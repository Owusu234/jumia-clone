
# store/views.py
import uuid
import json
import os
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.db.models.functions import TruncMonth
from django.utils.text import slugify
from django.contrib.auth import login as django_login, logout as django_logout
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse
from django.http import JsonResponse
from django.template.loader import render_to_string
from supabase import create_client
from paystackapi.paystack import Paystack
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import requests
from datetime import datetime, timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models.functions import TruncDay,TruncHour
from datetime import timezone as dt_timezone

from django.db import transaction
from django.contrib.auth import login

# Initialize Paystack
paystack = Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)

# ==================== AI CHATBOT (OpenRouter) ====================
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-4o-mini"  # any model id from https://openrouter.ai/models

from .models import Product, Category, Cart, CartItem, Order, OrderItem, SellerProfile, UserProfile, Review,Region, PageView
from .forms import CustomUserCreationForm, CustomAuthenticationForm, SellerSignupForm, ProductUploadForm, ReviewForm
from django.http import JsonResponse
import re
from django.core.paginator import Paginator

# ==================== SUPABASE CLIENT & HELPERS ====================

def get_supabase_client():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def fetch_whatsapp_from_supabase(supa_user_id):
    """Retrieve WhatsApp number from Supabase Auth metadata"""
    try:
        supabase = get_supabase_client()
        # Fetch user directly by ID (efficient & reliable)
        user = supabase.auth.admin.get_user_by_id(supa_user_id).user
        if user and user.user_metadata:
            return user.user_metadata.get("whatsapp_number")
    except Exception as e:
        print(f"⚠️ Supabase WhatsApp fetch failed: {e}")
    return None

# store/views.py - 

def upload_avatar_to_supabase(user_id, avatar_file):
    """Upload avatar to Supabase Storage and return public URL"""
    if not avatar_file:
        return None
    try:
        from supabase import create_client
        from django.conf import settings
        import uuid, os
        
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        
        # Generate unique filename
        ext = os.path.splitext(avatar_file.name)[1].lower()
        filename = f"avatars/{user_id}_{uuid.uuid4().hex}{ext}"
        
        # Upload to Supabase Storage bucket 'avatars'
        supabase.storage.from_("avatars").upload(
            filename, 
            avatar_file.read(), 
            {"content-type": avatar_file.content_type, "cache-control": "3600"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_("avatars").get_public_url(filename)
        return public_url
    except Exception as e:
        print(f"⚠️ Avatar upload failed: {e}")
        return None

def get_supabase_client():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY)

def get_or_create_django_user(supabase_user):
    username = supabase_user.user_metadata.get("username", supabase_user.email.split("@")[0])
    django_user, created = User.objects.get_or_create(
        username=username, defaults={"email": supabase_user.email, "first_name": supabase_user.user_metadata.get("first_name", "")}
    )
    if created:
        django_user.set_unusable_password()
        django_user.save()
    return django_user, created

def store_supabase_session(req, session):
    req.session["supabase_session"] = {"access_token": session.access_token, "refresh_token": session.refresh_token, "user_id": session.user.id, "email": session.user.email}
    req.session.modified = True

def clear_supabase_session(req):
    req.session.pop("supabase_session", None)
    req.session.modified = True

def convert_decimals_to_floats(obj):
    if isinstance(obj, Decimal): return float(obj)
    elif isinstance(obj, dict): return {k: convert_decimals_to_floats(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)): return [convert_decimals_to_floats(i) for i in obj]
    return obj

# 🔹 PROF TABLE HELPERS
def get_supabase_prof(user_id):
    supabase = get_supabase_client()
    try: return supabase.table("prof").select("*").eq("id", str(user_id)).single().execute().data
    except Exception: return None

def update_supabase_prof(user_id, data):
    supabase = get_supabase_client()
    try: supabase.table("prof").update(data).eq("id", str(user_id)).execute(); return True
    except Exception: return False

def get_cart_data(req):
    if not req.user.is_authenticated: return {"items": [], "total": 0, "count": 0, "cart_id": None}
    session_data = req.session.get("supabase_session")
    # ✅ FIXED: Added 'data' suffix and colon
    if not session_data: return {"items": [], "total": 0, "count": 0, "cart_id": None}
    
    auth_user_id = session_data.get("user_id")
    supabase = get_supabase_client()
    try:
        cart_resp = supabase.table("carts").select("id").eq("user_id", auth_user_id).execute()
        if not cart_resp.data or len(cart_resp.data) == 0:
            insert_resp = supabase.table("carts").insert({"user_id": auth_user_id}).execute()
            cart_id = insert_resp.data[0]["id"] if insert_resp.data else None
        else: cart_id = cart_resp.data[0]["id"]
        
        if not cart_id: return {"items": [], "total": 0, "count": 0, "cart_id": None}
        
        items_resp = supabase.table("cart_items").select("id, quantity, unit_price, product_id").eq("cart_id", cart_id).execute()
        items = items_resp.data or []
        if not items: return {"items": [], "total": 0, "count": 0, "cart_id": cart_id}
        
        product_ids = [i["product_id"] for i in items]
        products = Product.objects.filter(id__in=product_ids).values("id", "name", "price", "slug", "supabase_image_path", "image_url", "stock", "seller__store_name")
        products_map = {p["id"]: p for p in products}
        
        cart_items, total, count = [], 0, 0
        for item in items:
            prod = products_map.get(item["product_id"])
            if prod:
                subtotal = item["unit_price"] * item["quantity"]
                total += subtotal; count += item["quantity"]
                cart_items.append({
                    "id": item["id"], "product": prod, "quantity": item["quantity"], "unit_price": item["unit_price"], "subtotal": subtotal,
                    "get_image": (prod["supabase_image_path"] and f"{settings.SUPABASE_URL}/storage/v1/object/public/product-uploads/{prod['supabase_image_path']}") or prod["image_url"] or "https://via.placeholder.com/400?text=No+Image"
                })
        return {"items": cart_items, "total": total, "count": count, "cart_id": cart_id}
    except Exception as e:
        print(f"⚠️ Cart sync error: {e}")
        return {"items": [], "total": 0, "count": 0, "cart_id": None}

# ==================== DECORATORS ====================
def seller_required(view):
    def wrap(req, *a, **k):
        if not req.user.is_authenticated: return redirect("login")
        if req.user.is_superuser: return view(req, *a, **k)
        if not hasattr(req.user, "seller_profile"): return redirect("store:seller_signup")
        return view(req, *a, **k)
    return wrap

def superuser_required(view):
    def wrap(req, *a, **k):
        if not req.user.is_superuser:
            messages.error(req, "🚫 Admin access required.")
            return redirect("store:home")
        return view(req, *a, **k)
    return wrap

# ==================== AUTHENTICATION ====================
def register(req):
    if req.user.is_authenticated: return redirect("store:home")
    if req.method == "POST":
        form = CustomUserCreationForm(req.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            
            # Save country to UserProfile
            if hasattr(user, "user_profile"):
                user.user_profile.country = form.cleaned_data.get("country")
                user.user_profile.whatsapp_number = form.cleaned_data.get("whatsapp_number")
                user.user_profile.save()
                
                # Sync to Supabase prof table
                update_supabase_prof(user.id, {
                    "username": user.username,
                    "email": user.email,
                    "whatsapp_number": form.cleaned_data.get("whatsapp_number"),
                    "country_code": form.cleaned_data.get("country") if form.cleaned_data.get("country") else None
                })
            
            # Auto-login
            django_login(req, user)
            messages.success(req, "🎉 Account created! Welcome to ShopVibe.")
            return redirect("store:home")
    else:
        form = CustomUserCreationForm()
    return render(req, "store/register.html", {"form": form})

def login_view(req):
    if req.user.is_authenticated: return redirect("store:admin_dashboard" if req.user.is_superuser else "store:home")
    redirect_url = req.build_absolute_uri('/')
    if req.method == "POST":
        supabase = get_supabase_client()
        try:
            response = supabase.auth.sign_in_with_password({"email": req.POST.get("username"), "password": req.POST.get("password")})
            if response.user:
                django_user, created = get_or_create_django_user(response.user)
                django_login(req, django_user)
                if response.session: store_supabase_session(req, response.session)
                if created and hasattr(django_user, "user_profile"):
                    django_user.user_profile.bio = response.user.user_metadata.get("bio", "Shopper"); django_user.user_profile.save()
                if django_user.is_superuser:
                    messages.success(req, f"👋 Welcome back, Admin {django_user.username}!"); return redirect("store:admin_dashboard")
                messages.success(req, f"👋 Welcome back, {django_user.first_name or django_user.username}!"); return redirect("store:home")
            messages.error(req, "Invalid credentials.")
        except Exception as e:
            err = str(e).lower()
            if "invalid login" in err: messages.error(req, "Invalid email or password.")
            elif "email not confirmed" in err: messages.error(req, "Please confirm your email first.")
            else: messages.error(req, f"Login failed: {str(e)}")
    return render(req, "store/login.html", {"form": CustomAuthenticationForm(), "supabase_url": settings.SUPABASE_URL, "redirect_url": redirect_url})

def logout_view(req):
    clear_supabase_session(req); django_logout(req); messages.success(req, "👋 Logged out successfully."); return redirect("store:home")

def oauth_callback(req): return redirect("store:home")

# ==================== STOREFRONT ====================

def home(req):
    # 1️⃣ Get filter params
    q = req.GET.get("q", "").strip()
    cat_slug = req.GET.get("category")
    price_min = req.GET.get("price_min")
    price_max = req.GET.get("price_max")
    sort = req.GET.get("sort", "newest")  # Default to newest
    
    # 2️⃣ Base querysets
    categories = Category.objects.all().order_by('name')
    prods = Product.objects.filter(is_active=True, stock__gt=0)  # Only in-stock items
    
    # 3️⃣ Search Filter
    if q:
        prods = prods.filter(
            Q(name__icontains=q) | 
            Q(description__icontains=q) | 
            Q(category__name__icontains=q)
        )
    
    # 4️⃣ Category Filter
    if cat_slug:
        prods = prods.filter(category__slug=cat_slug)
    
    # 5️⃣ 💰 Price Filter (NEW)
    if price_min:
        try:
            prods = prods.filter(price__gte=float(price_min))
        except (ValueError, TypeError):
            pass  # Ignore invalid input
    if price_max:
        try:
            prods = prods.filter(price__lte=float(price_max))
        except (ValueError, TypeError):
            pass
    
    # 6️⃣ 📊 Sorting (NEW)
    if sort == "price_asc":
        prods = prods.order_by("price", "-created_at")
    elif sort == "price_desc":
        prods = prods.order_by("-price", "-created_at")
    elif sort == "name_asc":
        prods = prods.order_by("name", "-created_at")
    elif sort == "name_desc":
        prods = prods.order_by("-name", "-created_at")
    else:  # "newest" or default
        prods = prods.order_by("-created_at")
    
    # 7️⃣ Pagination
    paginator = Paginator(prods, 24)  # 24 products per page
    page_number = req.GET.get("page")
    products = paginator.get_page(page_number)
    
    # 8️⃣ Cart count (if using session)
    cart_count = len(req.session.get('cart', {})) if req.session else 0
    
    return render(req, "store/home.html", {
        "products": products,
        "categories": categories,
        "cart_count": cart_count,
        # Optional: Pass current filters for template display
        "current_filters": {
            "q": q,
            "category": cat_slug,
            "price_min": price_min,
            "price_max": price_max,
            "sort": sort,
        }
    })

@login_required
def product_detail(req, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    seller = product.seller
    seller_whatsapp = None

    if seller and seller.user:
        # 1️⃣ Fetch directly from Supabase Auth metadata
        raw_whatsapp = fetch_whatsapp_from_supabase(str(seller.user.id))
        
        # 2️⃣ Clean for wa.me link (remove +, spaces, dashes, leading 0)
        if raw_whatsapp:
            seller_whatsapp = re.sub(r'[^\d]', '', str(raw_whatsapp))
            if seller_whatsapp.startswith('0'):
                seller_whatsapp = seller_whatsapp[1:]

    # Handle Reviews
    if req.method == "POST":
        rating = req.POST.get("rating")
        comment = req.POST.get("comment", "").strip()
        if rating and rating.isdigit():
            Review.objects.update_or_create(
                user=req.user, product=product,
                defaults={"rating": int(rating), "comment": comment}
            )
            messages.success(req, "✅ Review submitted!")
            return redirect("store:product_detail", slug=slug)

    similar_products = Product.objects.filter(
        category=product.category, is_active=True, stock__gt=0
    ).exclude(id=product.id).order_by("-created_at")[:4]

    return render(req, "store/product_detail.html", {
        "product": product,
        "seller_whatsapp": seller_whatsapp,  # ✅ Clean number ready for wa.me
        "similar_products": similar_products
    })

@login_required
def submit_review(req, pid):
    prod = get_object_or_404(Product, id=pid)
    if req.method == "POST" and not Review.objects.filter(user=req.user, product=prod).exists():
        if OrderItem.objects.filter(order__user=req.user, product=prod).exists():
            form = ReviewForm(req.POST)
            if form.is_valid():
                rev = form.save(commit=False); rev.user = req.user; rev.product = prod; rev.save()
                messages.success(req, "✅ Review submitted successfully!")
        else: messages.error(req, "❌ Only verified buyers can review.")
    return redirect("store:product_detail", slug=prod.slug)

# ==================== CART & CHECKOUT ====================

def add_to_cart(req, product_id):
    if req.method == 'GET':
        try:
            product = Product.objects.get(id=product_id)
            cart = req.session.get('cart', {})
            if not isinstance(cart, dict):
                cart = {}
                
            pid_key = str(product_id)
            
            # Extract current qty safely
            current_qty = 1
            current_color = ''
            if pid_key in cart:
                item = cart[pid_key]
                if isinstance(item, dict):
                    current_qty = int(item.get('quantity', 1))
                    current_color = item.get('color', '')
                elif isinstance(item, (int, float)):
                    current_qty = int(item)
                    
            # Overwrite with clean structure
            cart[pid_key] = {
                'quantity': current_qty + 1,
                'color': req.GET.get('color', current_color)
            }
            
            req.session['cart'] = cart
            req.session.modified = True
            return redirect('store:cart')
        except Product.DoesNotExist:
            pass
    return redirect('store:home')

@login_required
def cart(req):
    """Display items in cart safely"""

    raw_cart = req.session.get('cart', {})

    # Ensure cart is always a dictionary
    if not isinstance(raw_cart, dict):
        raw_cart = {}

    cart_items = []
    cart_total = Decimal('0.00')
    cart_count = 0
    clean_cart = {}

    for pid, item_data in raw_cart.items():
        try:
            product = Product.objects.get(id=int(pid))

            # Default values
            quantity = 1
            color = ''

            # Handle dictionary structure
            if isinstance(item_data, dict):
                quantity = item_data.get('quantity', 1)
                color = item_data.get('color', '')

            # Handle old integer structure
            elif isinstance(item_data, (int, float)):
                quantity = item_data

            # Flatten corrupted nested dictionaries
            while isinstance(quantity, dict):
                quantity = quantity.get('quantity', 1)

            # Convert safely to integer
            try:
                quantity = int(quantity)
                if quantity < 1:
                    quantity = 1
            except:
                quantity = 1

            # Safe Decimal multiplication
            subtotal = product.price * Decimal(str(quantity))

            cart_items.append({
                'product': product,
                'quantity': quantity,
                'color_variant': color,
                'total_price': subtotal,
            })

            cart_total += subtotal
            cart_count += quantity

            # Save cleaned structure
            clean_cart[str(pid)] = {
                'quantity': quantity,
                'color': color
            }

        except Product.DoesNotExist:
            continue

        except Exception as e:
            print("Cart Error:", e)
            continue

    # Auto-fix corrupted session cart
    if clean_cart != raw_cart:
        req.session['cart'] = clean_cart
        req.session.modified = True

    return render(req, 'store/cart.html', {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_count': cart_count,
    })

@login_required
def remove_from_cart(req, product_id):
    """Remove product from cart"""
    cart = req.session.get('cart', {})
    pid = str(product_id)
    
    if pid in cart:
        del cart[pid]
        req.session['cart'] = cart
        req.session.modified = True
        
    return redirect('store:cart')


def cart_view(req):
    raw_cart = req.session.get('cart', {})

    if not isinstance(raw_cart, dict):
        raw_cart = {}

    cart_items = []
    total = Decimal("0.00")
    count = 0
    clean_cart = {}

    for pid, item_data in raw_cart.items():

        try:
            product = Product.objects.get(id=pid)

            qty = 1
            color = ''

            # Handle dictionary cart item
            if isinstance(item_data, dict):

                qty = item_data.get('quantity', 1)
                color = item_data.get('color', '')

            # Handle old integer-based carts
            elif isinstance(item_data, (int, float, str)):

                qty = item_data

            # Flatten nested quantity dictionaries safely
            max_depth = 5

            while isinstance(qty, dict) and max_depth > 0:

                qty = qty.get('quantity') or qty.get('qty') or 1

                max_depth -= 1

            # Final safety check
            if isinstance(qty, dict):
                qty = 1

            try:
                qty = int(float(qty))

                if qty < 1:
                    qty = 1

            except (ValueError, TypeError):
                qty = 1

            # Safe Decimal multiplication
            item_total = Decimal(product.price) * Decimal(qty)

            total += item_total
            count += qty

            cart_items.append({
                'product': product,
                'quantity': qty,
                'color_variant': color,
                'total_price': item_total,
            })

            # Save cleaned structure
            clean_cart[str(pid)] = {
                'quantity': qty,
                'color': color,
            }

        except Product.DoesNotExist:
            continue

        except Exception as e:
            print("Cart Error:", e)
            continue

    # Auto-clean malformed cart session
    if clean_cart != raw_cart:

        req.session['cart'] = clean_cart
        req.session.modified = True

    return render(req, 'store/cart.html', {
        'cart_items': cart_items,
        'cart_total': total,
        'cart_count': count,
    })

def update_cart(req):
    if req.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
        
    try:
        import json
        data = json.loads(req.body)
        pid = str(data.get('product_id'))
        color = data.get('color')
        change = data.get('change')
        
        cart = req.session.get('cart', {})
        if not isinstance(cart, dict):
            cart = {}
            
        if pid not in cart:
            return JsonResponse({'success': False, 'error': 'Item not in cart'})
            
        item = cart[pid]
        # Extract current qty safely
        if isinstance(item, int):
            current_qty = item
        elif isinstance(item, dict):
            current_qty = int(item.get('quantity', 1))
        else:
            current_qty = 1
            
        if change == 'remove':
            del cart[pid]
        else:
            new_qty = max(1, current_qty + int(change))
            cart[pid] = {
                'quantity': new_qty,
                'color': color if color is not None else item.get('color', '')
            }
            
        req.session['cart'] = cart
        req.session.modified = True
        
        new_count = sum(int(i.get('quantity', 1)) if isinstance(i, dict) else i for i in cart.values())
        return JsonResponse({'success': True, 'count': new_count})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
# store/views.py


from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings

@login_required
def checkout(req):
    """Display checkout page with Paystack integration"""

    cart_data = req.session.get('cart', {})

    if not isinstance(cart_data, dict):
        cart_data = {}

    if not cart_data:
        messages.warning(req, "🛒 Your cart is empty.")
        return redirect("store:cart")

    items = []
    total = Decimal('0.00')
    clean_cart = {}

    for pid, item_data in cart_data.items():

        try:
            product = Product.objects.get(id=int(pid))

            quantity = 1
            color = ''

            # Handle dictionary structure
            if isinstance(item_data, dict):
                quantity = item_data.get('quantity', 1)
                color = item_data.get('color', '')

            # Handle old integer structure
            elif isinstance(item_data, (int, float)):
                quantity = item_data

            # Flatten nested dictionaries
            while isinstance(quantity, dict):
                quantity = quantity.get('quantity', 1)

            # Safe integer conversion
            try:
                quantity = int(quantity)
                if quantity < 1:
                    quantity = 1
            except:
                quantity = 1

            # Safe subtotal calculation
            subtotal = product.price * Decimal(str(quantity))

            items.append({
                "product": product,
                "qty": quantity,
                "color": color,
                "subtotal": subtotal
            })

            total += subtotal

            # Save cleaned structure
            clean_cart[str(pid)] = {
                "quantity": quantity,
                "color": color
            }

        except Product.DoesNotExist:
            continue

        except Exception as e:
            print("Checkout Error:", e)
            continue

    # Auto-fix corrupted cart data
    if clean_cart != cart_data:
        req.session['cart'] = clean_cart
        req.session.modified = True

    # Convert to pesewas/kobo for Paystack
    total_kobo = int(total * 100)

    return render(req, "store/checkout.html", {
        "items": items,
        "total": total,
        "total_kobo": total_kobo,
        "paystack_public_key": settings.PAYSTACK_PUBLIC_KEY,
        "cart_count": len(items)
    })

@login_required
def initialize_paystack_payment(req):
    """Initialize Paystack transaction"""
    if req.method == "POST":
        cart_data = req.session.get('cart', {})
        total = sum(
            Product.objects.get(id=int(pid)).price * qty 
            for pid, qty in cart_data.items()
        )
        total_kobo = int(total * 100)
        
        # Generate unique reference
        import uuid
        ref = f"SHOPVIBE-{uuid.uuid4().hex[:10].upper()}"
        
        # Initialize Paystack transaction
        url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "email": req.user.email,
            "amount": total_kobo,
            "reference": ref,
            "metadata": {
                "user_id": req.user.id,
                "cart": cart_data,
                "custom_fields": [
                    {
                        "display_name": "User",
                        "variable_name": "user",
                        "value": req.user.username
                    }
                ]
            },
            "callback_url": req.build_absolute_uri('/checkout/verify/')
        }
        
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        if data.get('status'):
            # Save transaction reference to session
            req.session['paystack_ref'] = ref
            return JsonResponse({
                'status': True,
                'authorization_url': data['data']['authorization_url']
            })
        else:
            return JsonResponse({
                'status': False,
                'message': 'Failed to initialize payment'
            }, status=400)
    
    return JsonResponse({'status': False}, status=405)

@login_required
def verify_paystack_payment(req):
    """Verify Paystack transaction after payment"""
    reference = req.GET.get('reference') or req.session.get('paystack_ref')
    
    if not reference:
        messages.error(req, "❌ No payment reference found.")
        return redirect("store:cart")
    
    # Verify with Paystack
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if data.get('status') and data['data']['status'] == 'success':
        # Payment successful - Create order
        cart_data = req.session.get('cart', {})
        total = 0
        order = Order.objects.create(
            user=req.user,
            reference=reference,
            total_amount=data['data']['amount'] / 100,  # Convert back to GH₵
            payment_status='paid',
            payment_method='paystack',
            paystack_response=data['data']
        )
        
        # Create order items
        for pid, qty in cart_data.items():
            try:
                product = Product.objects.get(id=int(pid))
                subtotal = product.price * qty
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty,
                    price=product.price,
                    subtotal=subtotal
                )
                total += subtotal
                
                # Reduce stock
                product.stock -= qty
                product.save()
            except Product.DoesNotExist:
                continue
        
        # Clear cart
        req.session['cart'] = {}
        req.session.modified = True
        
        messages.success(req, f"✅ Payment successful! Order #{order.id} created.")
        return redirect("store:order_success", order_id=order.id)
    else:
        messages.error(req, "❌ Payment verification failed.")
        return redirect("store:checkout")

@login_required
def order_success(req, order_id):
    """Order success page"""
    try:
        order = Order.objects.get(id=order_id, user=req.user)
        return render(req, "store/order_success.html", {"order": order})
    except Order.DoesNotExist:
        return redirect("store:home")

@login_required
def order_receipt(req, order_id):
    """Display order receipt/invoice"""
    order = get_object_or_404(Order, id=order_id)
    
    # Security: Only allow user or staff to view receipt
    if order.user != req.user and not req.user.is_staff:
        # Sellers can view receipts for their orders
        if hasattr(req.user, 'seller_profile'):
            if not OrderItem.objects.filter(order=order, product__seller=req.user.seller_profile).exists():
                return redirect('store:home')
        else:
            return redirect('store:home')
    
    return render(req, "store/order_receipt.html", {"order": order})

# ==================== USER PROFILE ====================
# store/views.py

@login_required
def profile(req):
    profile = req.user.user_profile
    seller = getattr(req.user, "seller_profile", None)
    
    if req.method == "POST":
        avatar_file = req.FILES.get("avatar")
        if avatar_file:
            supa_url = upload_avatar_to_supabase(req.user.id, avatar_file)
            if supa_url:
                profile.avatar = supa_url  
                profile.save(update_fields=["avatar"])
                messages.success(req, "✅ Avatar updated!")
            else:
                messages.error(req, "❌ Avatar upload failed. Try again.")
        
        # Handle other fields...
        whatsapp = req.POST.get("whatsapp_number", "").strip()
        bio = req.POST.get("bio", "").strip()
        if whatsapp: profile.whatsapp_number = whatsapp
        if bio: profile.bio = bio
        country = req.POST.get("country", "").strip()
        if country: profile.country = country
        profile.save(update_fields=["whatsapp_number", "bio", "country", "avatar"])
        
        # ✅ Always redirect to force fresh context load
        return redirect("store:profile")
    
    return render(req, "store/profile.html", {
        "profile": profile,
        "seller": seller,
        "avatar_url": profile.get_avatar_url()  # ✅ Passes correct URL
    })
        

# ==================== SELLER PORTAL ====================
# In seller_signup view:
# store/views.py

@login_required
def seller_signup(req):

    if req.method == 'POST':
        form = SellerSignupForm(req.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1️⃣ Create User
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password']
                    )
                    
                    # 2️⃣ Create SellerProfile with WhatsApp
                    seller_profile = SellerProfile.objects.create(
                        user=user,
                        store_name=form.cleaned_data['store_name'],
                        phone=form.cleaned_data['phone'],
                        whatsapp=form.cleaned_data['whatsapp'],  # ✅ Saved here
                        address=form.cleaned_data['address'],
                        region=form.cleaned_data.get('region', '')
                    )
                    
                    # 3️⃣ Auto-login the seller
                    login(req, user)
                    
                    # 4️⃣ Success message
                    messages.success(
                        req, 
                        f"Welcome {user.username}! Your store '{seller_profile.store_name}' is ready. "
                        f"WhatsApp: {seller_profile.whatsapp or 'Not set'}"
                    )
                    
                    return redirect('store:seller_dashboard')
                    
            except Exception as e:
                messages.error(req, f"Registration failed: {str(e)}")
        else:
            messages.error(req, "Please correct the errors below.")
    else:
        form = SellerSignupForm()
    
    return render(req, 'store/seller_registration.html', {'form': form})

@login_required
@seller_required
def seller_dashboard(req):
    s = req.user.seller_profile
    prods = Product.objects.filter(seller=s)
    orders = Order.objects.filter(items__product__seller=s).distinct()
    stats = {
        "sales": orders.aggregate(t=Sum("total_amount"))["t"] or 0,
        "units": OrderItem.objects.filter(product__seller=s).aggregate(c=Count("id"))["c"] or 0,
        "count": orders.count()
    }
    

    statuses = ["Pending", "Processing", "Shipped", "In Transit", "Out for Delivery", "Delivered", "Cancelled"]
    
    return render(req, "store/seller_dashboard.html", {
        "profile": s,
        "products": prods,
        "orders": orders,
        "stats": stats,
        "statuses": statuses  
    })

# store/views.py


@login_required
def seller_analytics(req):
    """Seller analytics dashboard with revenue charts"""
    seller = get_object_or_404(SellerProfile, user=req.user)
    
    # Get seller's paid orders only
    orders = Order.objects.filter(
        items__product__seller=seller,
        payment_status='paid'
    ).distinct()
    
    # ✅ Total revenue - use total_amount (NOT total or total_)
    total_revenue = orders.aggregate(r=Sum("total_amount"))["r"] or 0
    
    # ✅ Order count
    order_count = orders.count()
    
    # ✅ Monthly revenue for Chart.js
    monthly = orders.annotate(
        mo=TruncMonth("created_at")
    ).values("mo").annotate(
        revenue=Sum("total_amount")  # ✅ FIXED: total_amount, not total_
    ).order_by("mo")
    
    # Format for frontend
    chart_labels = [item["mo"].strftime("%b %Y") for item in monthly]
    chart_data = [float(item["revenue"] or 0) for item in monthly]
    
    # ✅ Top selling products
    top_products = OrderItem.objects.filter(
        order__in=orders,
        product__seller=seller
    ).values(
        "product__name", "product__id"
    ).annotate(
        sold=Sum("quantity"),
        revenue=Sum("subtotal")
    ).order_by("-sold")[:5]
    
    context = {
        "seller": seller,
        "revenue": float(total_revenue),
        "order_count": order_count,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "top_products": list(top_products),
        "statuses": ["pending", "processing", "shipped", "delivered", "cancelled"],
    }
    
    return render(req, "store/seller_analytics.html", context)
# store/views.py


@login_required
@seller_required
def upload_product(req):
    """Handle product upload with single category selection"""
    if req.method == "POST":
        form = ProductUploadForm(req.POST, req.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = req.user.seller_profile
            
            # Handle image upload to Supabase Storage
            uploaded_file = req.FILES.get("image")
            if uploaded_file:
                ext = uploaded_file.name.split(".")[-1].lower()
                filename = f"products/{uuid.uuid4()}.{ext}"
                try:
                    supabase = get_supabase_client()
                    supabase.storage.from_("product-uploads").upload(
                        filename, 
                        uploaded_file.read(), 
                        {"content-type": uploaded_file.content_type}
                    )
                    product.supabase_image_path = filename
                except Exception as e:
                    messages.error(req, f"❌ Image upload failed: {str(e)}")
                    return render(req, "store/upload_product.html", {"form": form})
            
            # ✅ Category is already handled by the form's ModelChoiceField
            # No need for custom_category logic anymore
            product.save()
            
            messages.success(req, f'✅ "{product.name}" uploaded successfully!')
            return redirect("store:upload_product")
    else:
        form = ProductUploadForm()
    
    return render(req, "store/upload_product.html", {"form": form})

@login_required
@seller_required
def delete_product(req, product_id):
    if req.method != 'POST': return redirect("store:seller_dashboard")
    product = get_object_or_404(Product, id=product_id)
    if product.seller != req.user.seller_profile and not req.user.is_superuser: messages.error(req, "🚫 You can only delete your own products."); return redirect("store:seller_dashboard")
    product_name = product.name
    if product.supabase_image_path:
        try: supabase = get_supabase_client(); supabase.storage.from_("product-uploads").remove([product.supabase_image_path])
        except Exception: pass
    product.delete()
    messages.success(req, f"🗑️ '{product_name}' deleted."); return redirect("store:admin_dashboard" if req.user.is_superuser else "store:seller_dashboard")

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
@superuser_required
def admin_dashboard(req):
    users = User.objects.all().order_by("-date_joined")
    products = Product.objects.select_related("category", "seller").order_by("-created_at")
    stats = {
        "users": users.count(), 
        "sellers": users.filter(seller_profile__isnull=False).count(), 
        "products": products.count(), 
        "orders": Order.objects.count(), 
        "revenue": Order.objects.aggregate(total=Sum("total_amount"))["total"] or 0
    }
    return render(req, "store/admin_dashboard.html", {
        "users": users,
        "products": products,
        "stats": stats,
        "recent_orders": Order.objects.select_related("user").order_by("-created_at")[:5],  # ✅ Added
        "statuses": ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]           # ✅ Added
    })

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
    except Exception: pass
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
    """Admin analytics dashboard with charts and stats"""
    from django.db.models import Sum, Count, Avg
    from django.db.models.functions import TruncMonth
    import json
    
    # 🔹 Overall Stats
    total_users = User.objects.count()
    total_sellers = User.objects.filter(seller_profile__isnull=False).count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=Sum("total"))["total"] or 0
    
    # 🔹 Monthly Revenue Chart Data
    monthly_revenue = Order.objects.annotate(
        month=TruncMonth("created_at")
    ).values("month").annotate(
        revenue=Sum("total"),
        order_count=Count("id")
    ).order_by("month")
    
    months = [item["month"].strftime("%b %Y") for item in monthly_revenue]
    revenues = [float(item["revenue"] or 0) for item in monthly_revenue]
    order_counts = [item["order_count"] for item in monthly_revenue]
    
    # 🔹 Top Selling Products
    top_products = OrderItem.objects.values(
        "product__name", "product__id"
    ).annotate(
        total_sold=Sum("quantity"),
        revenue=Sum("price")
    ).order_by("-total_sold")[:10]
    
    # 🔹 Recent Orders
    recent_orders = Order.objects.select_related("user").order_by("-created_at")[:10]
    
    # 🔹 Seller Performance
    seller_stats = SellerProfile.objects.annotate(
        product_count=Count("products", distinct=True),
        order_count=Count("products__order_items__order", distinct=True),  
        total_sales=Sum("products__order_items__price")
    ).order_by("-total_sales")[:10]
    
    return render(req, "store/admin_analytics.html", {
        "stats": {
            "users": total_users, "sellers": total_sellers, "products": total_products,
            "orders": total_orders, "revenue": total_revenue
        },
        "chart_data": {
            "months": json.dumps(months),
            "revenues": json.dumps(revenues),
            "order_counts": json.dumps(order_counts)
        },
        "top_products": top_products,
        "recent_orders": recent_orders,
        "seller_stats": seller_stats
    })

@login_required
@superuser_required
def admin_orders(req):
    """Admin order management page"""
    # Filtering
    status_filter = req.GET.get("status", "")
    search_query = req.GET.get("q", "")
    
    orders = Order.objects.select_related("user").prefetch_related("items__product").order_by("-created_at")
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(items__product__name__icontains=search_query)
        ).distinct()
    
    # Pagination (optional)
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 20)  # 20 orders per page
    page_number = req.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(req, "store/admin_orders.html", {
        "orders": page_obj,
        "status_filter": status_filter,
        "search_query": search_query,
        "statuses": ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
    })

@login_required
@superuser_required
def admin_update_order_status(req, order_id):
    """Update order status (AJAX endpoint)"""
    if req.method != "POST":
        return redirect("store:admin_orders")
    
    order = get_object_or_404(Order, id=order_id)
    new_status = req.POST.get("status")
    
    if new_status in ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]:
        order.status = new_status
        order.save()
        messages.success(req, f"✅ Order #{order.id} status updated to {new_status}.")
    else:
        messages.error(req, "❌ Invalid status.")
    
    return redirect("store:admin_orders")

@login_required
def user_orders(req):
    """Display user's order & transaction history"""
    orders = Order.objects.filter(user=req.user).select_related('user').prefetch_related('items__product').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 8)
    page_number = req.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(req, 'store/user_orders.html', {
        'page_obj': page_obj,
        'orders': page_obj.object_list
    })

@login_required
def track_order(req, order_id):
    """Buyer-facing order tracking page with location timeline"""
    order = get_object_or_404(Order, id=order_id, user=req.user)
    
    # Build status timeline
    timeline = []
    status_order = ["Pending", "Processing", "Shipped", "In Transit", "Out for Delivery", "Delivered"]
    
    for i, status in enumerate(status_order):
        if order.status == status:
            # Current status
            timeline.append({
                "status": status,
                "active": True,
                "date": order.delivered_at if status == "Delivered" else order.created_at,
                "location": order.delivery_location if status in ["In Transit", "Out for Delivery", "Delivered"] else None
            })
        elif status_order.index(order.status) > i:
            # Completed status
            timeline.append({
                "status": status,
                "active": False,
                "date": order.created_at,  # Simplified: use order date for all past steps
                "location": None
            })
        else:
            # Future status
            break
    
    return render(req, "store/track_order.html", {
        "order": order,
        "timeline": timeline,
        "can_cancel": order.status in ["Pending", "Processing"]
    })

@login_required
def update_order_status(req, order_id):
    """Allow sellers/admin to update order status (including marking as delivered)"""
    if req.method != "POST":
        return redirect("store:order_history")
    
    order = get_object_or_404(Order, id=order_id)
    new_status = req.POST.get("status")
    
    # Permission check: seller can only update their own orders, admin can update any
    if not req.user.is_superuser:
        if not order.items.filter(product__seller=req.user.seller_profile).exists():
            messages.error(req, "🚫 You can only manage your own orders.")
            return redirect("store:order_history")
    
    valid_statuses = [s[0] for s in Order.STATUS]
    if new_status in valid_statuses:
        old_status = order.status
        order.status = new_status
        order.save()  # This triggers the auto-set delivered_at in model.save()
        messages.success(req, f"✅ Order #{order.id} updated: {old_status} → {new_status}")
    else:
        messages.error(req, "❌ Invalid status.")
    
    # Redirect based on user role
    if req.user.is_superuser:
        return redirect("store:admin_orders")
    return redirect("store:seller_dashboard")

# store/views.py

@login_required
def complete_profile(req):
    """Handle profile completion for new users"""
    profile, _ = UserProfile.objects.get_or_create(user=req.user)
    
    if req.method == "POST":
        # ✅ Handle text-based country field
        country = req.POST.get("country", "").strip()
        whatsapp = req.POST.get("whatsapp_number", "").strip()
        
        if country:
            profile.country = country
        if whatsapp:
            profile.whatsapp_number = whatsapp
            
        profile.save(update_fields=["country", "whatsapp_number"])
        
        # Sync to Supabase if needed
        update_supabase_prof(req.user.id, {
            "country": country,
            "whatsapp_number": whatsapp
        })
        
        messages.success(req, "✅ Profile completed!")
        
        # Redirect to intended page or home
        next_url = req.GET.get("next", "store:home")
        return redirect(next_url)
    
    return render(req, "store/complete_profile.html", {
        "profile": profile,
        "next": req.GET.get("next", "store:home")
    })


def get_regions_by_country(req):
    """API endpoint to fetch regions for a selected country"""
    country_id = req.GET.get('country_id')
    if country_id:
        regions = Region.objects.filter(country_id=country_id, is_active=True).values('id', 'name', 'code')
        return JsonResponse({'regions': list(regions)})
    return JsonResponse({'regions': []})

@require_POST
def chatbot_recommend(req):
    """
    AI shopping-assistant endpoint. Takes a free-text description of what
    the customer wants and returns a short reply + matching products,
    picked only from real catalog data (never invented by the model).
    """
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

    # Same base queryset convention as home() — active, in-stock products only
    prods = Product.objects.filter(is_active=True, stock__gt=0)[:200]

    catalog_lines = []
    id_to_product = {}
    for p in prods:
        id_to_product[p.id] = p
        catalog_lines.append(
            f"id={p.id} | {p.name} | category={p.category.name} "
            f"| price=GH₵{p.price} | stock={p.stock} | {p.description[:120]}"
        )
    catalog_text = "\n".join(catalog_lines)

    system_prompt = f"""You are a friendly shopping assistant for ShopVibe,
an online marketplace. A customer will describe what they're looking for.
Recommend ONLY items from the catalog below — never invent products or IDs.

CATALOG:
{catalog_text}

Respond with STRICT JSON only, no markdown, no extra text, in this exact shape:
{{
  "reply": "a short, friendly, 1-3 sentence response to the customer",
  "product_ids": [list of matching product ids from the catalog, empty if none fit]
}}
Pick at most 5 product_ids, ranked best match first."""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": user_message})

    try:
        ai_resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://shopvibe.up.railway.app/",
                "X-Title": "ShopVibe Chatbot",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 400,
            },
            timeout=20,
        )
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
    products_json = [
        {
            "id": p.id,
            "name": p.name,
            "price": str(p.price),
            "image_url": p.get_image(),
            "slug": p.slug,
        }
        for p in matched
    ]

    return JsonResponse({"reply": reply_text, "products": products_json})

@login_required
def product_detail(req, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # 1️⃣ Existing: Supabase profile fetch
    seller_prof = get_supabase_prof(product.seller.user_id) if product.seller else None
    
    # 2️ ✅ WhatsApp Retrieval & Formatting
    whatsapp_raw = None
    
    # Priority A: Supabase profile data
    if seller_prof:
        whatsapp_raw = seller_prof.get('whatsapp') or seller_prof.get('phone')
        
    # Priority B: Fallback to Django SellerProfile
    if not whatsapp_raw and product.seller:
        seller_obj = getattr(product.seller, 'seller_profile', None) or product.seller
        whatsapp_raw = getattr(seller_obj, 'whatsapp', None) or getattr(seller_obj, 'phone', None)
        
    # Format for WhatsApp API (wa.me/ requires digits + country code)
    whatsapp_api_id = None
    whatsapp_display = None
    
    if whatsapp_raw:
        # Strip everything except digits
        clean_digits = re.sub(r'[^\d]', '', str(whatsapp_raw))
        if clean_digits:
            # Ensure Ghana country code (233)
            if not clean_digits.startswith('233'):
                clean_digits = '233' + clean_digits.lstrip('0')
            whatsapp_api_id = clean_digits
            whatsapp_display = f"+{clean_digits}"
    
    # 3️⃣ Existing: Fetch similar products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True,
        stock__gt=0
    ).exclude(id=product.id).order_by('-created_at')[:4]
    
    # 4️⃣ Existing: Handle review submission
    if req.method == "POST" and req.user.is_authenticated:
        rating = req.POST.get("rating")
        comment = req.POST.get("comment", "")
        if rating:
            Review.objects.update_or_create(
                user=req.user, product=product,
                defaults={"rating": rating, "comment": comment}
            )
        return redirect("store:product_detail", slug=slug)
    
    # 5️⃣ Render with WhatsApp context
    return render(req, "store/product_detail.html", {
        "product": product,
        "seller_prof": seller_prof,
        "related_products": related_products,
        # ✅ WhatsApp variables for template
        "whatsapp_number": whatsapp_api_id,       # Digits only for wa.me/ link
        "whatsapp_display": whatsapp_display,     # Formatted for UI (e.g., +233...)
        "whatsapp_available": bool(whatsapp_api_id),
        "seller_name": seller_prof.get('store_name') if seller_prof else getattr(product.seller, 'store_name', 'Seller'),
    })


@login_required
def add_review(req, product_id):
    """Handle review submission via POST"""
    if req.method != "POST":
        return redirect("store:home")
    
    product = get_object_or_404(Product, id=product_id, is_active=True)
    rating = req.POST.get("rating")
    comment = req.POST.get("comment", "").strip()
    
    if rating and rating.isdigit():
        # Create or update review (one review per user per product)
        Review.objects.update_or_create(
            user=req.user,
            product=product,
            defaults={
                "rating": int(rating),
                "comment": comment
            }
        )
        messages.success(req, "✅ Review submitted successfully!")
    
    return redirect("store:product_detail", slug=product.slug)


@login_required
def remove_from_cart(req, product_id):
    """Remove product from cart"""
    cart = req.session.get('cart', {})
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        del cart[product_id_str]
        req.session['cart'] = cart
        req.session.modified = True
        messages.success(req, "✅ Item removed from cart")
    
    return redirect('store:cart')


def is_seller_or_staff(user):
    return user.is_staff or hasattr(user, 'seller_profile')

def is_seller_or_staff(user):
    return user.is_staff or hasattr(user, 'seller_profile')

@login_required
@user_passes_test(is_seller_or_staff)
def analytics_dashboard(req):
    """Analytics dashboard with accurate metrics and chart data"""
    
    is_staff = req.user.is_staff
    
    # ✅ Build base Q filters (no kwargs mixed in)
    if is_staff:
        order_q = Q(payment_status='paid')
        product_q = Q(is_active=True)
    else:
        seller = req.user.seller_profile
        order_q = Q(items__product__seller=seller, payment_status='paid')
        product_q = Q(seller=seller, is_active=True)
    
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    
    # 📊 Orders Today
    orders_q = order_q & Q(created_at__gte=today_start)
    orders_today = Order.objects.filter(orders_q).distinct().count()
    
    # 📊 Revenue Today
    revenue_today = Order.objects.filter(orders_q).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # 📊 New Users Today
    new_users_today = User.objects.filter(
        date_joined__gte=today_start,
        is_staff=False
    ).count()
    
    # 📊 Page Views
    try:
        from .models import PageView
        page_views_today = PageView.objects.filter(timestamp__gte=today_start).count()
    except ImportError:
        page_views_today = 0
    
    # 📈 Hourly Chart Data (last 24h)
    hourly_q = order_q & Q(created_at__gte=now - timedelta(hours=24))
    hourly_data = Order.objects.filter(hourly_q).annotate(
        hour=TruncHour('created_at')
    ).values('hour').annotate(
        revenue=Sum('total_amount'),
        orders=Count('id', distinct=True)
    ).order_by('hour')
    
    hourly_labels, hourly_revenue, hourly_orders = [], [], []
    for i in range(24):
        hour_dt = now - timedelta(hours=23-i)
        hourly_labels.append(hour_dt.strftime('%H:00'))
        match = next((h for h in hourly_data if h['hour'] == hour_dt.replace(minute=0, second=0, microsecond=0)), None)
        hourly_revenue.append(float(match['revenue'] or 0) if match else 0)
        hourly_orders.append(match['orders'] if match else 0)
    
    # 📈 Daily Chart Data (last 7 days)
    daily_q = order_q & Q(created_at__gte=week_start)
    daily_data = Order.objects.filter(daily_q).annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        revenue=Sum('total_amount'),
        orders=Count('id', distinct=True)
    ).order_by('day')
    
    daily_labels, daily_revenue = [], []
    for i in range(7):
        day_dt = week_start + timedelta(days=i)
        daily_labels.append(day_dt.strftime('%a %d'))
        match = next((d for d in daily_data if d['day'].date() == day_dt.date()), None)
        daily_revenue.append(float(match['revenue'] or 0) if match else 0)
    
    # 🏆 Top Products This Week

# ✅ Build product filters using relationship paths for OrderItem queries
    if is_staff:
        # Staff: filter by active products only
        order_item_filters = Q(
            order__payment_status='paid',
            product__is_active=True,
            order__created_at__gte=week_start
        )
    else:
        # Seller: filter by their active products only
        seller = req.user.seller_profile
        order_item_filters = Q(
            order__payment_status='paid',
            product__seller=seller,      # 🔑 Use product__seller
            product__is_active=True,     # 🔑 Use product__is_active
            order__created_at__gte=week_start
        )

    # ✅ Top Products query with correct field paths
    top_products = OrderItem.objects.filter(
        order_item_filters
    ).values(
        'product__name',
        'product__id'
    ).annotate(
        revenue=Sum('subtotal'),
        sold=Sum('quantity')
    ).order_by('-revenue')[:5]
    
    context = {
        'orders_today': orders_today,
        'revenue_today': float(revenue_today),
        'new_users_today': new_users_today,
        'page_views_today': page_views_today,
        'hourly_labels': hourly_labels,
        'hourly_revenue': hourly_revenue,
        'hourly_orders': hourly_orders,
        'daily_labels': daily_labels,
        'daily_revenue': daily_revenue,
        'top_products': list(top_products),
        'is_staff': is_staff,
        'last_updated': now.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    return render(req, 'store/analytics_dashboard.html', context)

@staff_member_required
def analytics_api(req):
    """API endpoint for real-time analytics data"""
    now = timezone.now()
    today = now.date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    
    # 📊 Revenue Metrics
    revenue_today = Order.objects.filter(
        created_at__date=today, payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    revenue_week = Order.objects.filter(
        created_at__date__gte=last_7_days, payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    revenue_month = Order.objects.filter(
        created_at__date__gte=last_30_days, payment_status='paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # 📦 Order Metrics
    orders_today = Order.objects.filter(created_at__date=today).count()
    orders_week = Order.objects.filter(created_at__date__gte=last_7_days).count()
    
    # 👥 User Metrics
    new_users_today = User.objects.filter(date_joined__date=today).count()
    total_users = User.objects.count()
    
    # 🛍️ Product Metrics
    top_products = OrderItem.objects.filter(
        order__created_at__date__gte=last_7_days
    ).values('product__name').annotate(
        total_sold=Sum('quantity'),
        revenue=Sum('subtotal')
    ).order_by('-total_sold')[:5]
    
    # 📈 Hourly Sales (last 24 hours)
    hourly_sales = []
    for hour in range(24):
        start = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
        sales = Order.objects.filter(
            created_at__gte=start, created_at__lt=end, payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        hourly_sales.append({
            'hour': f"{hour:02d}:00",
            'sales': float(sales)
        })
    
    # 🌍 Page Views (last hour)
    views_last_hour = PageView.objects.filter(
        timestamp__gte=now - timedelta(hours=1)
    ).count()
    
    return JsonResponse({
        'revenue': {
            'today': float(revenue_today),
            'week': float(revenue_week),
            'month': float(revenue_month)
        },
        'orders': {
            'today': orders_today,
            'week': orders_week
        },
        'users': {
            'new_today': new_users_today,
            'total': total_users
        },
        'top_products': list(top_products),
        'hourly_sales': hourly_sales,
        'page_views_last_hour': views_last_hour,
        'timestamp': now.isoformat()
    })

# Middleware to track page views (optional but recommended)
class AnalyticsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Track page views for analytics (skip static/media/admin)
        if not request.path.startswith(('/static/', '/media/', '/admin/', '/api/')):
            PageView.objects.create(
                user=request.user if request.user.is_authenticated else None,
                path=request.path,
                session_key=request.session.session_key or ''
            )
        return response
    
# store/views.py


# store/views.py

@login_required
def seller_daily_sales_api(req):
    """API: Returns last 7 days of daily sales broken down by product"""
    try:
        seller = req.user.seller_profile
    except SellerProfile.DoesNotExist:
        return JsonResponse({"labels": [], "datasets": []})

    start_date = timezone.now() - timedelta(days=7)
    
    # Get seller's active products for consistent color mapping
    products = Product.objects.filter(seller=seller, is_active=True).order_by('name')
    product_ids = {p.id: p.name for p in products}
    
    # Aggregate daily sales PER PRODUCT for paid orders
    daily_product_sales = OrderItem.objects.filter(
        product__seller=seller,
        product__in=products,
        order__payment_status='paid',
        order__created_at__gte=start_date
    ).annotate(
        day=TruncDay('order__created_at')
    ).values('day', 'product_id').annotate(
        total=Sum('subtotal'),
        quantity=Sum('quantity')
    ).order_by('day', 'product_id')

    # Structure data for Chart.js multi-dataset
    days = {}
    for item in daily_product_sales:
        day_key = item['day'].strftime('%a %d')  # e.g., "Mon 05"
        if day_key not in days:
            days[day_key] = {}
        days[day_key][item['product_id']] = {
            'total': float(item['total'] or 0),
            'quantity': item['quantity'] or 0
        }

    # Build datasets array (one per product)
    datasets = []
    for pid, pname in product_ids.items():
        data = []
        for day_key in sorted(days.keys()):
            val = days[day_key].get(pid, {}).get('total', 0)
            data.append(val)
        
        # Skip products with zero sales in the period
        if any(v > 0 for v in data):
            datasets.append({
                'label': pname,
                'data': data,
                'productId': pid,  # For legend toggle
                'backgroundColor': '',  # Will be set by JS theme handler
                'borderColor': '',
                'borderWidth': 1
            })

    return JsonResponse({
        'labels': sorted(days.keys()),
        'datasets': datasets,
        'products': [{'id': pid, 'name': name} for pid, name in product_ids.items()]
    })