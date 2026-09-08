import logging
import uuid
import json
import os
import requests
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.db.models.functions import TruncMonth
from django.utils.text import slugify
from django.contrib.auth import login as django_login, logout as django_logout
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from supabase import create_client
from paystackapi.paystack import Paystack
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models.functions import TruncDay, TruncHour
from datetime import timezone as dt_timezone
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib.auth import login
from django.core.paginator import Paginator
import re

# Initialize Paystack
paystack = Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)

# ==================== AI CHATBOT (OpenRouter) ====================
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-4o-mini"

from .models import Product, Category, Cart, CartItem, Order, OrderItem, SellerProfile, UserProfile, Review, Region, PageView, AdminNotification
from .forms import CustomUserCreationForm, CustomAuthenticationForm, SellerSignupForm, ProductUploadForm, ReviewForm
from .decorators import seller_approved_required

# ==================== SUPABASE CLIENT & HELPERS ====================
def get_supabase_client():
    """Initialize Supabase client"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY)

def fetch_whatsapp_from_supabase(supa_user_id):
    """Retrieve WhatsApp number from Supabase Auth metadata"""
    try:
        supabase = get_supabase_client()
        user = supabase.auth.admin.get_user_by_id(supa_user_id).user
        if user and user.user_metadata:
            return user.user_metadata.get("whatsapp_number")
    except Exception as e:
        print(f"⚠️ Supabase WhatsApp fetch failed: {e}")
    return None

def upload_avatar_to_supabase(user_id, avatar_file):
    """Upload avatar to Supabase Storage and return public URL"""
    if not avatar_file:
        return None
    try:
        ext = os.path.splitext(avatar_file.name)[1].lower()
        filename = f"avatars/{user_id}_{uuid.uuid4().hex}{ext}"
        supabase = get_supabase_client()
        supabase.storage.from_("profile_pictures").upload(
            filename, 
            avatar_file.read(), 
            {"content-type": avatar_file.content_type, "cache-control": "3600"}
        )
        return supabase.storage.from_("profile_pictures").get_public_url(filename)
    except Exception as e:
        print(f"⚠️ Avatar upload failed: {e}")
        return None

def get_or_create_django_user(supabase_user):
    """Create or retrieve Django User from Supabase user"""
    username = supabase_user.user_metadata.get("username", supabase_user.email.split("@")[0])
    django_user, created = User.objects.get_or_create(
        username=username, 
        defaults={"email": supabase_user.email, "first_name": supabase_user.user_metadata.get("first_name", "")}
    )
    if created:
        django_user.set_unusable_password()
        django_user.save()
    return django_user, created

def store_supabase_session(req, session):
    """Store Supabase session tokens in Django session"""
    req.session["supabase_session"] = {
        "access_token": session.access_token, 
        "refresh_token": session.refresh_token, 
        "user_id": session.user.id, 
        "email": session.user.email
    }
    req.session.modified = True

def clear_supabase_session(req):
    """Clear Supabase session from Django session"""
    req.session.pop("supabase_session", None)
    req.session.modified = True

def convert_decimals_to_floats(obj):
    """Recursively convert Decimal objects to floats for JSON serialization"""
    if isinstance(obj, Decimal): 
        return float(obj)
    elif isinstance(obj, dict): 
        return {k: convert_decimals_to_floats(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)): 
        return [convert_decimals_to_floats(i) for i in obj]
    return obj

def get_supabase_prof(user_id):
    """Fetch user profile from Supabase 'prof' table"""
    supabase = get_supabase_client()
    try: 
        return supabase.table("prof").select("*").eq("id", str(user_id)).single().execute().data
    except Exception: 
        return None

def update_supabase_prof(user_id, data):
    """Update user profile in Supabase 'prof' table"""
    supabase = get_supabase_client()
    try: 
        supabase.table("prof").update(data).eq("id", str(user_id)).execute()
        return True
    except Exception: 
        return False

def fix_glb_diffuse_factors(glb_bytes):
    """Fix GLB files where diffuseFactor is white [1,1,1,1], washing out texture colours."""
    import struct, json, io
    try:
        from PIL import Image
    except ImportError:
        return glb_bytes
    try:
        data = bytearray(glb_bytes)
        if data[:4] != b"glTF": 
            return glb_bytes
        chunk0_len = struct.unpack_from("<I", data, 12)[0]
        gltf = json.loads(data[20:20 + chunk0_len])
        bin_start = 20 + chunk0_len
        chunk1_len = struct.unpack_from("<I", data, bin_start)[0]
        bin_data = bytes(data[bin_start + 8 : bin_start + 8 + chunk1_len])
        bv_list = gltf.get("bufferViews", [])
        img_list = gltf.get("images", [])
        tex_list = gltf.get("textures", [])
        
        def sample_color(tex_idx):
            src = tex_list[tex_idx]["source"]
            bv = bv_list[img_list[src]["bufferView"]]
            chunk = bin_data[bv["byteOffset"]: bv["byteOffset"] + bv["byteLength"]]
            img = Image.open(io.BytesIO(chunk)).convert("RGB")
            w, h = img.size
            pts = [(int(fx*w), int(fy*h)) for fx in (.2,.4,.5,.6,.8) for fy in (.2,.4,.5,.6,.8)]
            avg = tuple(sum(img.getpixel(p)[i] for p in pts)//len(pts) for i in range(3))
            return [round(c/255, 4) for c in avg] + [1.0]
        
        changed = False
        for mat in gltf.get("materials", []):
            ext = mat.get("extensions", {}).get("KHR_materials_pbrSpecularGlossiness", {})
            df = ext.get("diffuseFactor", [0,0,0,1])
            if df[0] > 0.95 and df[1] > 0.95 and df[2] > 0.95:
                dt = ext.get("diffuseTexture")
                if dt:
                    try: 
                        ext["diffuseFactor"] = sample_color(dt["index"])
                        changed = True
                    except Exception: 
                        pass
            pbr = mat.get("pbrMetallicRoughness", {})
            bf = pbr.get("baseColorFactor", [0,0,0,1])
            if bf[0] > 0.95 and bf[1] > 0.95 and bf[2] > 0.95:
                bt = pbr.get("baseColorTexture")
                if bt:
                    try: 
                        pbr["baseColorFactor"] = sample_color(bt["index"])
                        changed = True
                    except Exception: 
                        pass
        if not changed: 
            return glb_bytes
        new_json = json.dumps(gltf, separators=(",",":")).encode("utf-8")
        while len(new_json) % 4: 
            new_json += b" "
        size_diff = len(new_json) - chunk0_len
        new_total = struct.unpack_from("<I", data, 8)[0] + size_diff
        struct.pack_into("<I", data, 8, new_total)
        struct.pack_into("<I", data, 12, len(new_json))
        return bytes(data[:20]) + new_json + bytes(data[20 + chunk0_len:])
    except Exception:
        return glb_bytes

# ==================== DECORATORS ====================
def seller_required(view):
    def wrap(req, *a, **k):
        if not req.user.is_authenticated: 
            return redirect("login")
        if req.user.is_superuser: 
            return view(req, *a, **k)
        if not hasattr(req.user, "seller_profile"): 
            return redirect("store:seller_signup")
        return view(req, *a, **k)
    return wrap

def superuser_required(view):
    def wrap(req, *a, **k):
        if not req.user.is_superuser:
            messages.error(req, "🚫 Admin access required.")
            return redirect("store:home")
        return view(req, *a, **k)
    return wrap

def is_seller_or_staff(user):
    return user.is_staff or hasattr(user, 'seller_profile')

def is_admin(user): 
    return user.is_staff or user.is_superuser

# ==================== AUTHENTICATION ====================
def register(req):
    if req.user.is_authenticated:
        return redirect("store:home")
    if req.method == "POST":
        form = CustomUserCreationForm(req.POST)
        if form.is_valid():
            supabase = get_supabase_client()
            email = form.cleaned_data["email"].strip().lower()
            password = form.cleaned_data["password1"]
            username = form.cleaned_data["username"]
            first_name = form.cleaned_data.get("first_name", "")
            last_name = form.cleaned_data.get("last_name", "")
            whatsapp = form.cleaned_data.get("whatsapp_number", "")
            country = form.cleaned_data.get("country")
            try:
                supabase_response = supabase.auth.sign_up({
                    "email": email,
                    "password": password,
                    "options": {
                        "data": {
                            "username": username,
                            "first_name": first_name,
                            "last_name": last_name,
                            "whatsapp_number": whatsapp,
                            "country": country,
                        }
                    }
                })
                supabase_user = supabase_response.user
                if not supabase_user:
                    messages.error(req, "❌ Could not create Supabase account.")
                    return render(req, "store/register.html", {"form": form})
                user = form.save(commit=False)
                user.save()
                if hasattr(user, "user_profile"):
                    user.user_profile.country = country
                    user.user_profile.whatsapp_number = whatsapp
                    user.user_profile.save()
                try:
                    supabase.table("prof").upsert({
                        "id": str(supabase_user.id),
                        "username": username,
                        "email": email,
                        "whatsapp_number": whatsapp,
                        "country_code": country if country else None,
                    }).execute()
                except Exception as profile_error:
                    print(f"⚠️ Supabase profile sync failed: {profile_error}")
                django_login(req, user)
                if supabase_response.session:
                    store_supabase_session(req, supabase_response.session)
                messages.success(req, "🎉 Account created! Welcome to ShopVibe.")
                return redirect("store:home")
            except Exception as e:
                print(f"🔴 REGISTRATION ERROR: {type(e).__name__}: {str(e)}")
                messages.error(req, f"❌ Registration failed: {str(e)}")
    else:
        form = CustomUserCreationForm()
    return render(req, "store/register.html", {"form": form})

def login_view(req):
    """Login view with Supabase Auth"""
    logger = logging.getLogger(__name__)
    if req.user.is_authenticated:
        return redirect("store:admin_dashboard" if req.user.is_superuser else "store:home")
    if req.method == "POST":
        email = req.POST.get("email", "").strip().lower()
        password = req.POST.get("password", "")
        if not email or not password:
            messages.error(req, "❌ Please enter both email and password.")
            return render(req, "store/login.html", {"email_value": email})
        try:
            supabase = get_supabase_client()
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if response.user:
                django_user, created = get_or_create_django_user(response.user)
                django_login(req, django_user)
                if response.session:
                    store_supabase_session(req, response.session)
                if django_user.is_superuser:
                    messages.success(req, f"👋 Welcome back, Admin {django_user.username}!")
                    return redirect("store:admin_dashboard")
                messages.success(req, f"👋 Welcome back, {django_user.first_name or django_user.username}!")
                return redirect("store:home")
            else:
                messages.error(req, "❌ Invalid email or password.")
        except Exception as e:
            logger.exception(f"Login error: {type(e).__name__} - {str(e)}")
            err_msg = str(e).lower()
            if "invalid login" in err_msg or "invalid credentials" in err_msg:
                messages.error(req, "❌ Invalid email or password.")
            elif "email not confirmed" in err_msg:
                messages.error(req, "⚠️ Please confirm your email address first.")
            elif "user not found" in err_msg:
                messages.error(req, "❌ No account found with this email.")
            else:
                messages.error(req, "❌ Login failed. Please try again.")
        return render(req, "store/login.html", {"email_value": email})
    return render(req, "store/login.html")

def logout_view(req):
    clear_supabase_session(req)
    django_logout(req)
    messages.success(req, "👋 Logged out successfully.")
    return redirect("store:home")

def oauth_callback(req): 
    return redirect("store:home")

# ==================== STOREFRONT ====================
def home(req):
    q = req.GET.get("q", "").strip()
    cat_slug = req.GET.get("category")
    price_min = req.GET.get("price_min")
    price_max = req.GET.get("price_max")
    sort = req.GET.get("sort", "newest")
    categories = Category.objects.all().order_by('name')
    prods = Product.objects.filter(is_active=True, stock__gt=0)
    if q:
        prods = prods.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(category__name__icontains=q))
    if cat_slug:
        prods = prods.filter(category__slug=cat_slug)
    if price_min:
        try: prods = prods.filter(price__gte=float(price_min))
        except: pass
    if price_max:
        try: prods = prods.filter(price__lte=float(price_max))
        except: pass
    if sort == "price_asc": prods = prods.order_by("price", "-created_at")
    elif sort == "price_desc": prods = prods.order_by("-price", "-created_at")
    elif sort == "name_asc": prods = prods.order_by("name", "-created_at")
    elif sort == "name_desc": prods = prods.order_by("-name", "-created_at")
    else: prods = prods.order_by("-created_at")
    paginator = Paginator(prods, 24)
    products = paginator.get_page(req.GET.get("page"))
    cart_count = len(req.session.get('cart', {})) if req.session else 0
    return render(req, "store/home.html", {
        "products": products, "categories": categories, "cart_count": cart_count,
        "current_filters": {"q": q, "category": cat_slug, "price_min": price_min, "price_max": price_max, "sort": sort}
    })

@require_POST
def chatbot_recommend(req):
    """AI shopping-assistant endpoint"""
    try:
        body = json.loads(req.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request body"}, status=400)
    user_message = (body.get("message") or "").strip()
    history = body.get("history") or []
    if not user_message:
        return JsonResponse({"error": "message is required"}, status=400)
    if not OPENROUTER_API_KEY:
        return JsonResponse({"error": "Server not configured (missing OPENROUTER_API_KEY)"}, status=500)
    prods = Product.objects.filter(is_active=True, stock__gt=0)[:200]
    catalog_lines = []
    id_to_product = {}
    for p in prods:
        id_to_product[p.id] = p
        catalog_lines.append(f"id={p.id} | {p.name} | category={p.category.name} | price=GH₵{p.price} | stock={p.stock} | {p.description[:120]}")
    catalog_text = "\n".join(catalog_lines)
    system_prompt = f"""You are a friendly shopping assistant for ShopVibe. Recommend ONLY items from the catalog below.
CATALOG:
{catalog_text}
Respond with STRICT JSON only: {{"reply": "short friendly response", "product_ids": [list of ids]}}"""
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": user_message})
    try:
        ai_resp = requests.post(OPENROUTER_URL, headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://shopvibe.up.railway.app/",
            "X-Title": "ShopVibe Chatbot",
        }, json={
            "model": OPENROUTER_MODEL, "messages": messages, "temperature": 0.4, "max_tokens": 400,
        }, timeout=20)
        ai_resp.raise_for_status()
        raw_content = ai_resp.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        return JsonResponse({"error": f"AI service error: {e}"}, status=502)
    cleaned = raw_content.strip().strip("`").replace("json\n", "", 1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return JsonResponse({"reply": raw_content, "products": []})
    reply_text = parsed.get("reply", "")
    product_ids = parsed.get("product_ids", []) or []
    matched = [id_to_product[pid] for pid in product_ids if pid in id_to_product]
    products_json = [{"id": p.id, "name": p.name, "price": str(p.price), "image_url": p.get_image(), "slug": p.slug} for p in matched]
    return JsonResponse({"reply": reply_text, "products": products_json})

@login_required
def product_detail(req, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    seller = product.seller
    seller_whatsapp = None
    if seller and seller.user:
        raw_whatsapp = fetch_whatsapp_from_supabase(str(seller.user.id))
        if raw_whatsapp:
            seller_whatsapp = re.sub(r'[^\d]', '', str(raw_whatsapp))
            if seller_whatsapp.startswith('0'): seller_whatsapp = seller_whatsapp[1:]
    if req.method == "POST" and req.user.is_authenticated:
        rating = req.POST.get("rating")
        comment = req.POST.get("comment", "").strip()
        if rating and rating.isdigit():
            Review.objects.update_or_create(user=req.user, product=product, defaults={"rating": int(rating), "comment": comment})
            messages.success(req, "✅ Review submitted!")
            return redirect("store:product_detail", slug=slug)
    similar_products = Product.objects.filter(category=product.category, is_active=True, stock__gt=0).exclude(id=product.id).order_by("-created_at")[:4]
    reviews = Review.objects.filter(product=product, is_approved=True).order_by('-created_at')
    return render(req, "store/product_detail.html", {
        "product": product, "seller_whatsapp": seller_whatsapp, "similar_products": similar_products, "reviews": reviews
    })

@login_required
def submit_review(req, product_id):
    """Handle review submission"""
    product = get_object_or_404(Product, id=product_id)
    if req.method == "POST":
        rating = req.POST.get("rating")
        comment = req.POST.get("comment", "").strip()
        if rating and comment:
            Review.objects.create(user=req.user, product=product, rating=int(rating), comment=comment)
            messages.success(req, "✅ Review submitted! Thank you.")
            return redirect("store:product_detail", slug=product.slug)
    return redirect("store:product_detail", slug=product.slug)

# ==================== CART & CHECKOUT ====================
def add_to_cart(req, product_id):
    if req.method == 'GET':
        try:
            product = Product.objects.get(id=product_id)
            cart = req.session.get('cart', {})
            if not isinstance(cart, dict): cart = {}
            pid_key = str(product_id)
            current_qty = 1
            current_color = ''
            if pid_key in cart:
                item = cart[pid_key]
                if isinstance(item, dict):
                    current_qty = int(item.get('quantity', 1))
                    current_color = item.get('color', '')
                elif isinstance(item, (int, float)):
                    current_qty = int(item)
            cart[pid_key] = {'quantity': current_qty + 1, 'size': '', 'color': req.GET.get('color', current_color)}
            req.session['cart'] = cart
            req.session.modified = True
            return redirect('store:cart')
        except Product.DoesNotExist:
            pass
        return redirect('store:home')

@login_required
@require_POST
def add_to_cart_post(req, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    qty = int(req.POST.get('quantity', 1))
    size = req.POST.get('size', '').strip().upper()
    color = req.POST.get('color', '').strip()
    if product.requires_size:
        if not size:
            messages.error(req, "❌ Please select a size before adding to cart.")
            return redirect('store:product_detail', slug=product.slug)
        size_stock = product.size_stock or {}
        if size not in size_stock or size_stock[size] < qty:
            messages.error(req, f"❌ Size {size} is out of stock or insufficient.")
            return redirect('store:product_detail', slug=product.slug)
    else:
        if product.stock < qty:
            messages.error(req, "❌ Insufficient stock.")
            return redirect('store:product_detail', slug=product.slug)
    cart = req.session.get('cart', {})
    cart[str(product_id)] = {'quantity': qty, 'size': size, 'color': color, 'name': product.name, 'price': float(product.price), 'image': product.get_image()}
    req.session['cart'] = cart
    req.session.modified = True
    messages.success(req, f"✅ {product.name} added to cart!")
    return redirect('store:cart')

# Keep original name mapping for backward compatibility
add_to_cart = add_to_cart_post if True else add_to_cart

@login_required
def cart(req):
    raw_cart = req.session.get('cart', {})
    if not isinstance(raw_cart, dict): raw_cart = {}
    cart_items = []
    cart_total = Decimal('0.00')
    cart_count = 0
    clean_cart = {}
    for pid, item_data in raw_cart.items():
        try:
            product = Product.objects.get(id=int(pid))
            quantity = 1; color = ''; size = ''
            if isinstance(item_data, dict):
                quantity = item_data.get('quantity', 1); color = item_data.get('color', ''); size = item_data.get('size', '')
            elif isinstance(item_data, (int, float)): quantity = item_data
            while isinstance(quantity, dict): quantity = quantity.get('quantity', 1)
            try:
                quantity = int(quantity)
                if quantity < 1: quantity = 1
            except: quantity = 1
            subtotal = product.price * Decimal(str(quantity))
            cart_items.append({'product': product, 'quantity': quantity, 'color_variant': color, 'size': size, 'total_price': subtotal})
            cart_total += subtotal; cart_count += quantity
            clean_cart[str(pid)] = {'quantity': quantity, 'color': color, 'size': size}
        except Product.DoesNotExist: continue
        except Exception as e: print("Cart Error:", e)
    if clean_cart != raw_cart:
        req.session['cart'] = clean_cart
        req.session.modified = True
    return render(req, 'store/cart.html', {'cart_items': cart_items, 'cart_total': cart_total, 'cart_count': cart_count})

@login_required
def remove_from_cart(req, product_id):
    cart = req.session.get('cart', {})
    pid = str(product_id)
    if pid in cart:
        del cart[pid]
        req.session['cart'] = cart
        req.session.modified = True
    return redirect('store:cart')

def update_cart(req):
    if req.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    try:
        data = json.loads(req.body)
        pid = str(data.get('product_id'))
        color = data.get('color')
        change = data.get('change')
        cart = req.session.get('cart', {})
        if not isinstance(cart, dict): cart = {}
        if pid not in cart:
            return JsonResponse({'success': False, 'error': 'Item not in cart'})
        item = cart[pid]
        if isinstance(item, int): current_qty = item
        elif isinstance(item, dict): current_qty = int(item.get('quantity', 1))
        else: current_qty = 1
        if change == 'remove':
            del cart[pid]
        else:
            new_qty = max(1, current_qty + int(change))
            cart[pid] = {'quantity': new_qty, 'color': color if color is not None else item.get('color', '')}
        req.session['cart'] = cart
        req.session.modified = True
        new_count = sum(int(i.get('quantity', 1)) if isinstance(i, dict) else i for i in cart.values())
        return JsonResponse({'success': True, 'count': new_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def checkout(req):
    cart_data = req.session.get('cart', {})
    if not isinstance(cart_data, dict): cart_data = {}
    if not cart_data:
        messages.warning(req, "🛒 Your cart is empty.")
        return redirect("store:cart")
    items = []; total = Decimal('0.00'); clean_cart = {}
    for pid, item_data in cart_data.items():
        try:
            product = Product.objects.get(id=int(pid))
            quantity = 1; color = ''; size = ''
            if isinstance(item_data, dict):
                quantity = item_data.get('quantity', 1); color = item_data.get('color', ''); size = item_data.get('size', '')
            elif isinstance(item_data, (int, float)): quantity = item_data
            while isinstance(quantity, dict): quantity = quantity.get('quantity', 1)
            try:
                quantity = int(quantity)
                if quantity < 1: quantity = 1
            except (ValueError, TypeError): quantity = 1
            subtotal = product.price * Decimal(str(quantity))
            items.append({"product": product, "qty": quantity, "color": color, "size": size, "subtotal": subtotal})
            total += subtotal
            clean_cart[str(pid)] = {"quantity": quantity, "color": color, "size": size}
        except Product.DoesNotExist: continue
        except Exception as e: print("Checkout Error:", e)
    if clean_cart != cart_data:
        req.session['cart'] = clean_cart
        req.session.modified = True
    total_kobo = int(total * 100)
    cart_json = json.dumps(clean_cart, default=str)
    return render(req, "store/checkout.html", {
        "items": items, "total": total, "total_kobo": total_kobo,
        "paystack_public_key": settings.PAYSTACK_PUBLIC_KEY, "cart_count": len(items),
        "cart_json": cart_json, "site_url": settings.SITE_URL
    })

@login_required
@require_POST
def initialize_paystack_payment(req):
    logger = logging.getLogger(__name__)
    try:
        cart_data = req.session.get('cart', {})
        if not cart_data or not isinstance(cart_data, dict):
            return JsonResponse({'error': 'Cart is empty or invalid'}, status=400)
        total = Decimal('0'); valid_items = 0
        for pid, item in cart_data.items():
            try:
                qty = item.get('quantity', 1) if isinstance(item, dict) else item
                while isinstance(qty, dict): qty = qty.get('quantity', 1)
                qty = max(1, int(float(qty)))
                product = Product.objects.get(id=int(pid), is_active=True)
                total += product.price * Decimal(qty); valid_items += 1
            except: continue
        if valid_items == 0 or total <= 0:
            return JsonResponse({'error': 'No valid items in cart'}, status=400)
        reference = f"SV-{req.user.id}-{int(timezone.now().timestamp())}-{valid_items}"
        payload = {
            'email': req.user.email or 'customer@shopvibe.com', 'amount': int(total * 100),
            'reference': reference, 'callback_url': f"{settings.SITE_URL.rstrip('/')}/checkout/callback/",
            'metadata': {'user_id': req.user.id, 'username': req.user.username, 'items_count': valid_items},
            'currency': 'GHS'
        }
        headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}', 'Content-Type': 'application/json'}
        resp = requests.post('https://api.paystack.co/transaction/initialize', json=payload, headers=headers, timeout=15)
        if resp.status_code == 400:
            try:
                error_data = resp.json()
                return JsonResponse({'error': error_data.get('message', 'Invalid request'), 'details': error_data.get('errors', [])}, status=400)
            except: pass
        resp.raise_for_status()
        data = resp.json()
        if data.get('status') and data.get('data', {}).get('authorization_url'):
            req.session['paystack_ref'] = reference; req.session['paystack_amount'] = str(total); req.session.modified = True
            return JsonResponse({'success': True, 'authorization_url': data['data']['authorization_url'], 'reference': reference})
        else:
            return JsonResponse({'error': data.get('message', 'Payment initialization failed')}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def paystack_callback(req):
    logger = logging.getLogger(__name__)
    reference = req.GET.get('reference')
    if not reference:
        return JsonResponse({'success': False, 'error': 'No payment reference'}, status=400)
    try:
        verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
        response = requests.get(verify_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not (data.get('status') and data.get('data', {}).get('status') == 'success'):
            return JsonResponse({'success': False, 'error': 'Payment not completed'}, status=400)
        paystack_data = data['data']; paid_amount_ghs = Decimal(paystack_data['amount']) / Decimal('100')
        cart_data = req.session.get('cart', {})
        order = Order.objects.create(user=req.user, reference=reference, total_amount=paid_amount_ghs, payment_status='paid', payment_method='paystack', paystack_response=paystack_data, customer_email=paystack_data.get('customer', {}).get('email', req.user.email))
        total_calculated = Decimal('0')
        for pid, item in cart_data.items():
            try:
                if isinstance(item, dict):
                    qty = item.get('quantity', 1); size = item.get('size', '')
                    while isinstance(qty, dict): qty = qty.get('quantity', 1)
                    qty = max(1, int(float(qty)))
                else: qty = max(1, int(float(item))); size = ''
                product = Product.objects.get(id=int(pid), is_active=True)
                if product.requires_size and size:
                    size_stock = product.size_stock or {}
                    if size in size_stock:
                        size_stock[size] = max(0, size_stock[size] - qty)
                        product.size_stock = size_stock
                        product.save(update_fields=['size_stock'])
                else:
                    product.stock = max(0, product.stock - qty); product.save(update_fields=['stock'])
                OrderItem.objects.create(order=order, product=product, quantity=qty, price=product.price, subtotal=product.price * qty, size=size)
                total_calculated += product.price * qty
            except Exception as e: logger.error(f"Error processing item {pid}: {e}"); continue
        req.session['cart'] = {}; req.session.pop('paystack_ref', None); req.session.pop('paystack_amount', None); req.session.modified = True
        return JsonResponse({'success': True, 'order_id': order.id, 'message': 'Payment successful'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def verify_paystack_payment(req):
    logger = logging.getLogger(__name__)
    reference = req.GET.get('reference') or req.session.get('paystack_ref')
    if not reference:
        messages.error(req, "❌ No payment reference found."); return redirect("store:cart")
    if not reference.startswith("SV-"):
        messages.error(req, "❌ Invalid payment reference."); return redirect("store:cart")
    try:
        verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
        response = requests.get(verify_url, headers=headers, timeout=30)
        if response.status_code in [400, 404]:
            messages.error(req, "❌ Invalid payment reference."); return redirect("store:checkout")
        response.raise_for_status()
        data = response.json()
        if not (data.get('status') and data.get('data', {}).get('status') == 'success'):
            messages.error(req, f"❌ Payment status: {data.get('data', {}).get('status', 'unknown')}."); return redirect("store:checkout")
        paystack_data = data['data']; paid_amount_ghs = Decimal(paystack_data['amount']) / Decimal('100')
        cart_data = req.session.get('cart', {})
        order = Order.objects.create(user=req.user, reference=reference, total_amount=paid_amount_ghs, payment_status='paid', payment_method='paystack', paystack_response=paystack_data)
        for pid, item in cart_data.items():
            try:
                if isinstance(item, dict):
                    qty = item.get('quantity', 1); color = item.get('color', ''); size = item.get('size', '')
                    while isinstance(qty, dict): qty = qty.get('quantity', 1)
                    qty = max(1, int(float(qty)))
                else: qty = max(1, int(float(item))); color = ''; size = ''
                product = Product.objects.select_for_update().get(id=int(pid), is_active=True)
                if product.requires_size and size:
                    size_stock = product.size_stock or {}
                    if size in size_stock:
                        size_stock[size] = max(0, size_stock[size] - qty)
                        product.size_stock = size_stock
                        product.save(update_fields=['size_stock'])
                else:
                    product.stock = max(0, product.stock - qty); product.save(update_fields=['stock'])
                OrderItem.objects.create(order=order, product=product, quantity=qty, price=product.price, subtotal=product.price * qty, color=color, size=size)
            except: continue
        req.session['cart'] = {}; req.session.pop('paystack_ref', None); req.session.pop('paystack_amount', None); req.session.modified = True
        messages.success(req, f"✅ Payment successful! Order #{order.id} confirmed."); return redirect("store:order_success", order_id=order.id)
    except Exception as e:
        messages.error(req, "❌ An unexpected error occurred."); return redirect("store:checkout")

@login_required
def order_success(req, order_id):
    try:
        order = Order.objects.get(id=order_id, user=req.user)
        return render(req, "store/order_success.html", {"order": order})
    except Order.DoesNotExist:
        return redirect("store:home")

@login_required
def order_receipt(req, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.user != req.user and not req.user.is_staff:
        if hasattr(req.user, 'seller_profile'):
            if not OrderItem.objects.filter(order=order, product__seller=req.user.seller_profile).exists():
                return redirect('store:home')
        else:
            return redirect('store:home')
    return render(req, "store/order_receipt.html", {"order": order})

# ==================== USER PROFILE ====================
@login_required
def profile(req):
    profile = req.user.user_profile
    seller = getattr(req.user, "seller_profile", None)
    if req.method == "POST":
        avatar_file = req.FILES.get("avatar")
        if avatar_file:
            supa_url = upload_avatar_to_supabase(req.user.id, avatar_file)
            if supa_url:
                profile.avatar = supa_url; profile.save(update_fields=["avatar"]); messages.success(req, "✅ Avatar updated!")
            else: messages.error(req, "❌ Avatar upload failed. Try again.")
        whatsapp = req.POST.get("whatsapp_number", "").strip()
        bio = req.POST.get("bio", "").strip()
        if whatsapp: profile.whatsapp_number = whatsapp
        if bio: profile.bio = bio
        country = req.POST.get("country", "").strip()
        if country: profile.country = country
        profile.save(update_fields=["whatsapp_number", "bio", "country", "avatar"])
        return redirect("store:profile")
    return render(req, "store/profile.html", {"profile": profile, "seller": seller, "avatar_url": profile.get_avatar_url()})

# ==================== SELLER PORTAL ====================
@login_required
def seller_signup(req):
    if hasattr(req.user, 'seller_profile'):
        status = req.user.seller_profile.status
        if status == 'approved':
            messages.info(req, "✅ You already have an approved seller account."); return redirect('store:seller_dashboard')
        elif status == 'pending':
            messages.warning(req, "⏳ Your application is pending admin review."); return redirect('store:profile')
    if req.method == 'POST':
        form = SellerSignupForm(req.POST, user=req.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = req.user; user.email = form.cleaned_data['email']
                    if form.cleaned_data['password']: user.set_password(form.cleaned_data['password']); user.save()
                    seller_profile = SellerProfile.objects.create(user=user, store_name=form.cleaned_data['store_name'], phone=form.cleaned_data['phone'], address=form.cleaned_data['address'], payment_number=form.cleaned_data.get('payment_number', ''), status='pending', is_verified=False)
                    messages.success(req, f"✅ Application submitted! '{seller_profile.store_name}' pending review."); return redirect('store:home')
            except Exception as e:
                import logging; logging.error(f"Seller signup failed: {e}"); messages.error(req, "Registration failed. Please try again.")
        else:
            messages.error(req, "Please correct the errors below.")
    else:
        initial_data = {'username': req.user.username, 'email': req.user.email}
        form = SellerSignupForm(initial=initial_data, user=req.user)
    return render(req, 'store/seller_signup.html', {'form': form})

@login_required
@seller_required
def seller_dashboard(req):
    s = req.user.seller_profile
    prods = Product.objects.filter(seller=s)
    orders = Order.objects.filter(items__product__seller=s).distinct()
    stats = {"sales": orders.aggregate(t=Sum("total_amount"))["t"] or 0, "units": OrderItem.objects.filter(product__seller=s).aggregate(c=Count("id"))["c"] or 0, "count": orders.count()}
    statuses = ["Pending", "Processing", "Shipped", "In Transit", "Out for Delivery", "Delivered", "Cancelled"]
    return render(req, "store/seller_dashboard.html", {"profile": s, "products": prods, "orders": orders, "stats": stats, "statuses": statuses})

@login_required
def seller_analytics(req):
    seller = get_object_or_404(SellerProfile, user=req.user)
    orders = Order.objects.filter(items__product__seller=seller, payment_status='paid').distinct()
    total_revenue = orders.aggregate(r=Sum("total_amount"))["r"] or 0; order_count = orders.count()
    monthly = orders.annotate(mo=TruncMonth("created_at")).values("mo").annotate(revenue=Sum("total_amount")).order_by("mo")
    chart_labels = [item["mo"].strftime("%b %Y") for item in monthly]; chart_data = [float(item["revenue"] or 0) for item in monthly]
    top_products = OrderItem.objects.filter(order__in=orders, product__seller=seller).values("product__name", "product__id").annotate(sold=Sum("quantity"), revenue=Sum("subtotal")).order_by("-sold")[:5]
    context = {"seller": seller, "revenue": float(total_revenue), "order_count": order_count, "chart_labels": chart_labels, "chart_data": chart_data, "top_products": list(top_products), "statuses": ["pending", "processing", "shipped", "delivered", "cancelled"]}
    return render(req, "store/seller_analytics.html", context)

@login_required
@seller_approved_required
def upload_product(req):
    if req.method == "POST":
        form = ProductUploadForm(req.POST, req.FILES)
        if form.is_valid():
            product = form.save(commit=False); product.seller = req.user.seller_profile
            if product.requires_size:
                size_input = form.cleaned_data.get('size_stock_input', ''); size_dict = {}
                if size_input:
                    for pair in size_input.split(','):
                        if ':' in pair:
                            s, q = pair.split(':', 1)
                            try: size_dict[s.strip().upper()] = max(0, int(q.strip()))
                            except: pass
                product.size_stock = size_dict; product.stock = 0
            else:
                product.size_stock = {}
            product.length = form.cleaned_data.get('length'); product.width = form.cleaned_data.get('width'); product.height = form.cleaned_data.get('height')
            uploaded_file = req.FILES.get("image")
            if uploaded_file:
                ext = uploaded_file.name.split(".")[-1].lower(); filename = f"products/{uuid.uuid4()}.{ext}"
                try:
                    supabase = get_supabase_client()
                    supabase.storage.from_("product-uploads").upload(filename, uploaded_file.read(), {"content-type": uploaded_file.content_type})
                    product.supabase_image_path = filename
                except Exception as e: messages.error(req, f"❌ Image upload failed: {str(e)}"); return render(req, "store/upload_product.html", {"form": form})
            vr_enabled = req.POST.get("vr_enabled"); vr_file = req.FILES.get("vr_model") or req.FILES.get("vr_image")
            if vr_enabled and vr_file:
                vr_type = req.POST.get("vr_type", "3d_model"); ext = vr_file.name.split(".")[-1].lower(); vr_filename = f"products/vr/{uuid.uuid4()}.{ext}"
                content_type_map = {"glb": "model/gltf-binary", "gltf": "model/gltf+json", "jpg": "image/jpeg", "jpeg": "image/jpeg", "jfif": "image/jpeg", "png": "image/png", "webp": "image/webp"}
                vr_content_type = content_type_map.get(ext, vr_file.content_type)
                try:
                    vr_bytes = vr_file.read()
                    if ext == "glb": vr_bytes = fix_glb_diffuse_factors(vr_bytes)
                    supabase = get_supabase_client()
                    supabase.storage.from_("product-uploads").upload(vr_filename, vr_bytes, {"content-type": vr_content_type, "upsert": "true"})
                    product.vr_supabase_path = vr_filename; product.vr_type = vr_type
                except Exception as e: messages.warning(req, f"⚠️ VR upload failed: {str(e)}")
            else: product.vr_supabase_path = None; product.vr_type = None
            product.save(); messages.success(req, f'✅ "{product.name}" uploaded successfully!'); return redirect("store:upload_product")
    else: form = ProductUploadForm()
    return render(req, "store/upload_product.html", {"form": form})

@login_required
@seller_required
def delete_product(req, product_id):
    if req.method != 'POST': return redirect("store:seller_dashboard")
    product = get_object_or_404(Product, id=product_id)
    if product.seller != req.user.seller_profile and not req.user.is_superuser: 
        messages.error(req, "🚫 You can only delete your own products."); return redirect("store:seller_dashboard")
    product_name = product.name
    if product.supabase_image_path:
        try: supabase = get_supabase_client(); supabase.storage.from_("product-uploads").remove([product.supabase_image_path])
        except: pass
    product.delete(); messages.success(req, f"🗑️ '{product_name}' deleted."); return redirect("store:admin_dashboard" if req.user.is_superuser else "store:seller_dashboard")

# ==================== USER ORDERS ====================
@login_required
def order_history(req):
    orders = Order.objects.filter(user=req.user).order_by("-created_at")
    orders_with_details = []
    for order in orders:
        items = order.items.select_related("product").all()
        orders_with_details.append({"order": order, "item_count": items.count(), "items": items[:3]})
    return render(req, "store/order_history.html", {"orders": orders_with_details, "total_orders": len(orders)})

# ==================== ADMIN DASHBOARD ====================
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(req):
    users = User.objects.all().order_by("-date_joined")
    products = Product.objects.select_related("category", "seller").order_by("-created_at")
    stats = {"users": users.count(), "sellers": users.filter(seller_profile__isnull=False).count(), "products": products.count(), "orders": Order.objects.count(), "revenue": Order.objects.aggregate(total=Sum("total_amount"))["total"] or 0}
    pending_sellers = SellerProfile.objects.filter(status='pending').select_related('user').order_by('-created_at')
    return render(req, "store/admin_dashboard.html", {"users": users, "products": products, "stats": stats, "recent_orders": Order.objects.select_related("user").order_by("-created_at")[:5], "statuses": ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"], "pending_sellers": pending_sellers})

@login_required
@superuser_required
def admin_add_user(req):
    if req.method == "POST":
        email, username, password, role = req.POST.get("email"), req.POST.get("username"), req.POST.get("password"), req.POST.get("role", "buyer")
        if not all([email, username, password]): messages.error(req, "❌ All fields required."); return redirect("store:admin_dashboard")
        supabase = get_supabase_client()
        try:
            supabase.auth.admin.create_user({"email": email, "password": password, "email_confirm": True, "user_metadata": {"username": username, "role": role}})
            User.objects.get_or_create(username=username, defaults={"email": email, "is_superuser": role == "admin"})
            messages.success(req, f"✅ User '{username}' created.")
        except Exception as e: messages.error(req, f"❌ Failed: {str(e)}")
        return redirect("store:admin_dashboard")

@login_required
@superuser_required
def admin_remove_user(req, user_id):
    if req.method != "POST": return redirect("store:admin_dashboard")
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser: messages.error(req, "❌ Cannot delete superadmin."); return redirect("store:admin_dashboard")
    supabase = get_supabase_client()
    try:
        for u in supabase.auth.admin.list_users().users:
            if getattr(u, "email", "") == user.email: supabase.auth.admin.delete_user(u.id); break
    except: pass
    user.delete(); messages.success(req, f"✅ User '{user.username}' removed."); return redirect("store:admin_dashboard")

@login_required
@superuser_required
def admin_update_price(req, product_id):
    if req.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        try: product.price = float(req.POST.get("price")); product.save(); messages.success(req, f"✅ Price updated.")
        except ValueError: messages.error(req, "❌ Invalid price format.")
        return redirect("store:admin_dashboard")

@login_required
@superuser_required
def admin_analytics(req):
    total_users = User.objects.count(); total_sellers = User.objects.filter(seller_profile__isnull=False).count()
    total_products = Product.objects.count(); total_orders = Order.objects.count(); total_revenue = Order.objects.aggregate(total=Sum("total"))["total"] or 0
    monthly_revenue = Order.objects.annotate(month=TruncMonth("created_at")).values("month").annotate(revenue=Sum("total"), order_count=Count("id")).order_by("month")
    months = [item["month"].strftime("%b %Y") for item in monthly_revenue]; revenues = [float(item["revenue"] or 0) for item in monthly_revenue]; order_counts = [item["order_count"] for item in monthly_revenue]
    top_products = OrderItem.objects.values("product__name", "product__id").annotate(total_sold=Sum("quantity"), revenue=Sum("price")).order_by("-total_sold")[:10]
    recent_orders = Order.objects.select_related("user").order_by("-created_at")[:10]
    seller_stats = SellerProfile.objects.annotate(product_count=Count("products", distinct=True), order_count=Count("products__order_items__order", distinct=True), total_sales=Sum("products__order_items__price")).order_by("-total_sales")[:10]
    pending_sellers = SellerProfile.objects.filter(status='pending').select_related('user').order_by('-created_at')[:10]
    return render(req, "store/admin_analytics.html", {"stats": {"users": total_users, "sellers": total_sellers, "products": total_products, "orders": total_orders, "revenue": total_revenue}, "chart_data": {"months": json.dumps(months), "revenues": json.dumps(revenues), "order_counts": json.dumps(order_counts)}, "top_products": top_products, "recent_orders": recent_orders, "seller_stats": seller_stats, "pending_sellers": pending_sellers})

@login_required
@superuser_required
def admin_orders(req):
    status_filter = req.GET.get("status", ""); search_query = req.GET.get("q", "")
    orders = Order.objects.select_related("user").prefetch_related("items__product").order_by("-created_at")
    if status_filter: orders = orders.filter(status=status_filter)
    if search_query: orders = orders.filter(Q(id__icontains=search_query) | Q(user__username__icontains=search_query) | Q(user__email__icontains=search_query) | Q(items__product__name__icontains=search_query)).distinct()
    paginator = Paginator(orders, 20); page_number = req.GET.get("page"); page_obj = paginator.get_page(page_number)
    return render(req, "store/admin_orders.html", {"orders": page_obj, "status_filter": status_filter, "search_query": search_query, "statuses": ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]})

@login_required
@superuser_required
def admin_update_order_status(req, order_id):
    if req.method != "POST": return redirect("store:admin_orders")
    order = get_object_or_404(Order, id=order_id); new_status = req.POST.get("status")
    if new_status in ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]:
        order.status = new_status; order.save(); messages.success(req, f"✅ Order #{order.id} status updated to {new_status}.")
    else: messages.error(req, "❌ Invalid status.")
    return redirect("store:admin_orders")

@login_required
def user_orders(req):
    orders = Order.objects.filter(user=req.user).select_related('user').prefetch_related('items__product').order_by('-created_at')
    paginator = Paginator(orders, 8); page_number = req.GET.get('page'); page_obj = paginator.get_page(page_number)
    return render(req, 'store/user_orders.html', {'page_obj': page_obj, 'orders': page_obj.object_list})

@login_required
def track_order(req, order_id):
    order = get_object_or_404(Order, id=order_id, user=req.user)
    status_map = {'pending': 'Pending', 'processing': 'Processing', 'shipped': 'Shipped', 'in_transit': 'In Transit', 'in transit': 'In Transit', 'out_for_delivery': 'Out for Delivery', 'out for delivery': 'Out for Delivery', 'delivered': 'Delivered', 'cancelled': 'Cancelled'}
    raw = (order.status or 'pending').lower(); current_status = status_map.get(raw, 'Pending')
    status_order = ["Pending", "Processing", "Shipped", "In Transit", "Out for Delivery", "Delivered"]
    location = getattr(order, 'shipping_address', getattr(order, 'delivery_address', None))
    if not location: location = getattr(order, 'shipping_city', getattr(order, 'city', None))
    timeline = []
    try: current_index = status_order.index(current_status)
    except ValueError: current_index = 0
    for i, status in enumerate(status_order):
        if i == current_index:
            timeline.append({"status": status, "active": True, "date": order.delivered_at if status == "Delivered" else order.created_at, "location": location if status in ["In Transit", "Out for Delivery", "Delivered"] else None})
        elif i < current_index:
            timeline.append({"status": status, "active": False, "date": order.created_at, "location": None})
        else: break
    return render(req, "store/track_order.html", {"order": order, "timeline": timeline, "can_cancel": current_status in ["Pending", "Processing"]})

@login_required
def cancel_order(req, order_id):
    order = get_object_or_404(Order, id=order_id, user=req.user)
    if order.status in ['Pending', 'Processing', 'pending', 'processing']:
        order.status = 'Cancelled'; order.save(); messages.success(req, "Order cancelled successfully.")
    else: messages.error(req, "This order cannot be cancelled at this stage.")
    return redirect('store:track_order', order_id=order_id)

@login_required
def update_order_status(req, order_id):
    if req.method != "POST": return redirect("store:order_history")
    order = get_object_or_404(Order, id=order_id); new_status = req.POST.get("status", "").strip()
    if not req.user.is_superuser:
        seller = getattr(req.user, 'seller_profile', None)
        if not seller or not order.items.filter(product__seller=seller).exists():
            messages.error(req, "🚫 You can only manage your own orders."); return redirect("store:order_history")
    status_field = Order._meta.get_field('status'); valid_statuses = [choice[0] for choice in status_field.choices]
    normalized = new_status.lower(); valid_lower = [s.lower() for s in valid_statuses]
    if normalized in valid_lower:
        order.status = next(s for s in valid_statuses if s.lower() == normalized); order.save()
        messages.success(req, f"✅ Order #{order.id} updated to {order.status.title()}")
    else: messages.error(req, f"❌ Invalid status. Choose from: {', '.join(valid_statuses)}")
    if req.user.is_superuser: return redirect("store:admin_orders")
    return redirect("store:seller_dashboard")

# ==================== PROFILE & REGIONS ====================
@login_required
def complete_profile(req):
    profile, _ = UserProfile.objects.get_or_create(user=req.user)
    if req.method == "POST":
        country = req.POST.get("country", "").strip(); whatsapp = req.POST.get("whatsapp_number", "").strip()
        if country: profile.country = country
        if whatsapp: profile.whatsapp_number = whatsapp
        profile.save(update_fields=["country", "whatsapp_number"])
        update_supabase_prof(req.user.id, {"country": country, "whatsapp_number": whatsapp})
        messages.success(req, "✅ Profile completed!"); next_url = req.GET.get("next", "store:home"); return redirect(next_url)
    return render(req, "store/complete_profile.html", {"profile": profile, "next": req.GET.get("next", "store:home")})

# ✅ THIS WAS MISSING - ADD THIS FUNCTION
def get_regions_by_country(req):
    """API endpoint to fetch regions for a selected country"""
    country_id = req.GET.get('country_id')
    if country_id:
        regions = Region.objects.filter(country_id=country_id, is_active=True).values('id', 'name', 'code')
        return JsonResponse({'regions': list(regions)})
    return JsonResponse({'regions': []})

# ==================== ANALYTICS & API ====================
@login_required
@user_passes_test(is_seller_or_staff)
def analytics_dashboard(req):
    is_staff = req.user.is_staff
    pending_sellers = SellerProfile.objects.filter(status='pending').select_related('user').order_by('-created_at') if is_staff else []
    if is_staff:
        order_q = Q(payment_status='paid'); product_q = Q(is_active=True)
    else:
        seller = req.user.seller_profile
        order_q = Q(items__product__seller=seller, payment_status='paid'); product_q = Q(seller=seller, is_active=True)
    now = timezone.now(); today_start = now.replace(hour=0, minute=0, second=0, microsecond=0); week_start = now - timedelta(days=7)
    orders_q = order_q & Q(created_at__gte=today_start); orders_today = Order.objects.filter(orders_q).distinct().count()
    revenue_today = Order.objects.filter(orders_q).aggregate(total=Sum('total_amount'))['total'] or 0
    new_users_today = User.objects.filter(date_joined__gte=today_start, is_staff=False).count()
    try:
        from .models import PageView
        page_views_today = PageView.objects.filter(timestamp__gte=today_start).count()
    except ImportError: page_views_today = 0
    hourly_q = order_q & Q(created_at__gte=now - timedelta(hours=24))
    hourly_data = Order.objects.filter(hourly_q).annotate(hour=TruncHour('created_at')).values('hour').annotate(revenue=Sum('total_amount'), orders=Count('id', distinct=True)).order_by('hour')
    hourly_labels, hourly_revenue, hourly_orders = [], [], []
    for i in range(24):
        hour_dt = now - timedelta(hours=23-i); hourly_labels.append(hour_dt.strftime('%H:00'))
        match = next((h for h in hourly_data if h['hour'] == hour_dt.replace(minute=0, second=0, microsecond=0)), None)
        hourly_revenue.append(float(match['revenue'] or 0) if match else 0); hourly_orders.append(match['orders'] if match else 0)
    daily_q = order_q & Q(created_at__gte=week_start)
    daily_data = Order.objects.filter(daily_q).annotate(day=TruncDay('created_at')).values('day').annotate(revenue=Sum('total_amount'), orders=Count('id', distinct=True)).order_by('day')
    daily_labels, daily_revenue = [], []
    for i in range(7):
        day_dt = week_start + timedelta(days=i); daily_labels.append(day_dt.strftime('%a %d'))
        match = next((d for d in daily_data if d['day'].date() == day_dt.date()), None)
        daily_revenue.append(float(match['revenue'] or 0) if match else 0)
    if is_staff:
        order_item_filters = Q(order__payment_status='paid', product__is_active=True, order__created_at__gte=week_start)
    else:
        seller = req.user.seller_profile
        order_item_filters = Q(order__payment_status='paid', product__seller=seller, product__is_active=True, order__created_at__gte=week_start)
    top_products = OrderItem.objects.filter(order_item_filters).values('product__name', 'product__id').annotate(revenue=Sum('subtotal'), sold=Sum('quantity')).order_by('-revenue')[:5]
    context = {'orders_today': orders_today, 'revenue_today': float(revenue_today), 'new_users_today': new_users_today, 'page_views_today': page_views_today, 'hourly_labels': hourly_labels, 'hourly_revenue': hourly_revenue, 'hourly_orders': hourly_orders, 'daily_labels': daily_labels, 'daily_revenue': daily_revenue, 'top_products': list(top_products), 'is_staff': is_staff, 'last_updated': now.strftime('%Y-%m-%d %H:%M:%S'), 'pending_sellers': pending_sellers}
    return render(req, 'store/analytics_dashboard.html', context)

@staff_member_required
def analytics_api(req):
    now = timezone.now(); today = now.date(); last_7_days = today - timedelta(days=7); last_30_days = today - timedelta(days=30)
    revenue_today = Order.objects.filter(created_at__date=today, payment_status='paid').aggregate(total=Sum('total_amount'))['total'] or 0
    revenue_week = Order.objects.filter(created_at__date__gte=last_7_days, payment_status='paid').aggregate(total=Sum('total_amount'))['total'] or 0
    revenue_month = Order.objects.filter(created_at__date__gte=last_30_days, payment_status='paid').aggregate(total=Sum('total_amount'))['total'] or 0
    orders_today = Order.objects.filter(created_at__date=today).count(); orders_week = Order.objects.filter(created_at__date__gte=last_7_days).count()
    new_users_today = User.objects.filter(date_joined__date=today).count(); total_users = User.objects.count()
    top_products = OrderItem.objects.filter(order__created_at__date__gte=last_7_days).values('product__name').annotate(total_sold=Sum('quantity'), revenue=Sum('subtotal')).order_by('-total_sold')[:5]
    hourly_sales = []
    for hour in range(24):
        start = now.replace(hour=hour, minute=0, second=0, microsecond=0); end = start + timedelta(hours=1)
        sales = Order.objects.filter(created_at__gte=start, created_at__lt=end, payment_status='paid').aggregate(total=Sum('total_amount'))['total'] or 0
        hourly_sales.append({'hour': f"{hour:02d}:00", 'sales': float(sales)})
    views_last_hour = PageView.objects.filter(timestamp__gte=now - timedelta(hours=1)).count()
    return JsonResponse({'revenue': {'today': float(revenue_today), 'week': float(revenue_week), 'month': float(revenue_month)}, 'orders': {'today': orders_today, 'week': orders_week}, 'users': {'new_today': new_users_today, 'total': total_users}, 'top_products': list(top_products), 'hourly_sales': hourly_sales, 'page_views_last_hour': views_last_hour, 'timestamp': now.isoformat()})

@login_required
def seller_daily_sales_api(req):
    try: seller = req.user.seller_profile
    except SellerProfile.DoesNotExist: return JsonResponse({"labels": [], "datasets": []})
    start_date = timezone.now() - timedelta(days=7)
    products = Product.objects.filter(seller=seller, is_active=True).order_by('name'); product_ids = {p.id: p.name for p in products}
    daily_product_sales = OrderItem.objects.filter(product__seller=seller, product__in=products, order__payment_status='paid', order__created_at__gte=start_date).annotate(day=TruncDay('order__created_at')).values('day', 'product_id').annotate(total=Sum('subtotal'), quantity=Sum('quantity')).order_by('day', 'product_id')
    days = {}
    for item in daily_product_sales:
        day_key = item['day'].strftime('%a %d')
        if day_key not in days: days[day_key] = {}
        days[day_key][item['product_id']] = {'total': float(item['total'] or 0), 'quantity': item['quantity'] or 0}
    datasets = []
    for pid, pname in product_ids.items():
        data = []
        for day_key in sorted(days.keys()): val = days[day_key].get(pid, {}).get('total', 0); data.append(val)
        if any(v > 0 for v in data): datasets.append({'label': pname, 'data': data, 'productId': pid, 'backgroundColor': '', 'borderColor': '', 'borderWidth': 1})
    return JsonResponse({'labels': sorted(days.keys()), 'datasets': datasets, 'products': [{'id': pid, 'name': name} for pid, name in product_ids.items()]})

# ==================== PASSWORD RESET ====================
def forgot_password(req):
    if req.user.is_authenticated: return redirect('store:home')
    if req.method == 'POST':
        email = req.POST.get('email', '').strip()
        if not email: messages.error(req, "Please enter your email address.")
        else:
            try:
                supabase = get_supabase_client()
                redirect_url = req.build_absolute_uri(reverse('store:password_reset')).rstrip('/')
                supabase.auth.reset_password_for_email(email, options={"redirectTo": redirect_url})
                messages.success(req, f"✅ Reset link sent to {email}. Check your inbox (and spam folder).")
                return redirect('store:login')
            except Exception as e:
                print(f"🔴 SUPABASE RESET ERROR: {type(e).__name__} - {str(e)}")
                messages.error(req, "❌ Failed to send reset email. Please try again.")
    return render(req, 'store/forgot_password.html')

def password_reset(req):
    return render(req, 'store/reset_password.html')

@require_POST
def api_reset_password(req):
    try:
        data = json.loads(req.body); token = data.get('token'); new_password = data.get('password')
        if not token or not new_password: return JsonResponse({'error': 'Missing token or password'}, status=400)
        if len(new_password) < 8: return JsonResponse({'error': 'Password must be at least 8 characters'}, status=400)
        headers = {"Authorization": f"Bearer {token}", "apikey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"}
        resp = requests.put(f"{settings.SUPABASE_URL}/auth/v1/user", json={"password": new_password}, headers=headers, timeout=10)
        resp.raise_for_status()
        return JsonResponse({'success': True, 'message': 'Password updated successfully'})
    except requests.exceptions.HTTPError as e:
        error_msg = "Invalid or expired reset link. Please request a new one."
        try:
            error_data = e.response.json()
            if "Token is expired" in error_data.get("message", ""): error_msg = "Reset link has expired. Please request a new one."
        except: pass
        return JsonResponse({'error': error_msg}, status=401)
    except Exception as e:
        return JsonResponse({'error': 'An unexpected error occurred. Please try again.'}, status=500)

# ==================== SELLER APPROVAL & NOTIFICATIONS ====================
@login_required
@user_passes_test(is_admin)
@require_POST
def approve_seller(request, seller_id):
    seller = get_object_or_404(SellerProfile, id=seller_id, status='pending')
    seller.status = 'approved'; seller.is_verified = True; seller.verified_at = timezone.now(); seller.save()
    AdminNotification.objects.filter(link__contains=str(seller_id)).update(is_read=True)
    messages.success(request, f"✅ '{seller.store_name}' has been approved.")
    return redirect(request.META.get('HTTP_REFERER', 'store:admin_dashboard'))

@login_required
@user_passes_test(is_admin)
@require_POST
def reject_seller(request, seller_id):
    seller = get_object_or_404(SellerProfile, id=seller_id, status='pending')
    reason = request.POST.get('reason', 'No reason provided').strip()
    seller.status = 'rejected'; seller.is_verified = False; seller.rejected_reason = reason; seller.save()
    AdminNotification.objects.filter(link__contains=str(seller_id)).update(is_read=True)
    messages.warning(request, f"❌ '{seller.store_name}' has been rejected.")
    return redirect(request.META.get('HTTP_REFERER', 'store:admin_dashboard'))

@login_required
@user_passes_test(is_admin)
def mark_notifications_read(request):
    AdminNotification.objects.filter(is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'store:home'))

@login_required
@user_passes_test(is_admin)
def seller_application_detail(request, seller_id):
    seller = get_object_or_404(SellerProfile, id=seller_id)
    AdminNotification.objects.filter(link__contains=f'seller/{seller_id}').update(is_read=True)
    if request.method == 'POST':
        action = request.POST.get('action'); reason = request.POST.get('reason', '').strip()
        if action == 'approve':
            seller.status = 'approved'; seller.is_verified = True; seller.verified_at = timezone.now(); seller.save()
            messages.success(request, f"✅ '{seller.store_name}' has been APPROVED. User is now a seller.")
        elif action == 'reject':
            seller.status = 'rejected'; seller.is_verified = False; seller.rejected_reason = reason; seller.save()
            messages.warning(request, f"❌ '{seller.store_name}' has been REJECTED.")
        return redirect('store:admin_dashboard')
    return render(request, 'store/seller_application_detail.html', {'seller': seller})

# ==================== MIDDLEWARE ====================
class AnalyticsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith(('/static/', '/media/', '/admin/', '/api/')):
            PageView.objects.create(user=request.user if request.user.is_authenticated else None, path=request.path, session_key=request.session.session_key or '')
        return response