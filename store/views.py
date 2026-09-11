# store/views.py
import logging
import os 
import uuid
import json
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

logger = logging.getLogger(__name__)

# ==================== AI CHATBOT (OpenRouter) ====================
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-4o-mini"  # any model id from https://openrouter.ai/models

# Initialize Paystack
paystack = Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)

from .models import Product, Category, Cart, CartItem, CartInvite, Order, OrderItem, SellerProfile, UserProfile, Review, Region, PageView
from .forms import CustomUserCreationForm, CustomAuthenticationForm, SellerSignupForm, ProductUploadForm, ReviewForm, CartInviteForm
from django.core.mail import send_mail
import re
from django.core.paginator import Paginator
from .models import AdminNotification
from .decorators import seller_approved_required

# ==================== SUPABASE CLIENT & HELPERS ====================

def get_supabase_client():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY)

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
        
        supabase.storage.from_("profile_pictures").upload(
            filename, 
            avatar_file.read(), 
            {"content-type": avatar_file.content_type, "cache-control": "3600"}
        )
        
        public_url = supabase.storage.from_("profile_pictures").get_public_url(filename)
        return public_url
    except Exception as e:
        print(f"⚠️ Avatar upload failed: {e}")
        return None

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
    req.session["supabase_session"] = {
        "access_token": session.access_token, 
        "refresh_token": session.refresh_token, 
        "user_id": session.user.id, 
        "email": session.user.email
    }
    req.session.modified = True

def clear_supabase_session(req):
    req.session.pop("supabase_session", None)
    req.session.modified = True

def convert_decimals_to_floats(obj):
    if isinstance(obj, Decimal): 
        return float(obj)
    elif isinstance(obj, dict): 
        return {k: convert_decimals_to_floats(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)): 
        return [convert_decimals_to_floats(i) for i in obj]
    return obj

# 🔹 PROF TABLE HELPERS
def get_supabase_prof(user_id):
    supabase = get_supabase_client()
    try: 
        return supabase.table("prof").select("*").eq("id", str(user_id)).single().execute().data
    except Exception: 
        return None

def update_supabase_prof(user_id, data):
    supabase = get_supabase_client()
    try: 
        supabase.table("prof").update(data).eq("id", str(user_id)).execute()
        return True
    except Exception: 
        return False

@login_required
@seller_approved_required
def seller_dashboard(request):
    return render(request, 'store/seller_dashboard.html')

def get_cart_data(req):
    if not req.user.is_authenticated: 
        return {"items": [], "total": 0, "count": 0, "cart_id": None}
    session_data = req.session.get("supabase_session")
    if not session_data: 
        return {"items": [], "total": 0, "count": 0, "cart_id": None}
    
    auth_user_id = session_data.get("user_id")
    supabase = get_supabase_client()
    try:
        cart_resp = supabase.table("carts").select("id").eq("user_id", auth_user_id).execute()
        if not cart_resp.data or len(cart_resp.data) == 0:
            insert_resp = supabase.table("carts").insert({"user_id": auth_user_id}).execute()
            cart_id = insert_resp.data[0]["id"] if insert_resp.data else None
        else: 
            cart_id = cart_resp.data[0]["id"]
        
        if not cart_id: 
            return {"items": [], "total": 0, "count": 0, "cart_id": None}
        
        items_resp = supabase.table("cart_items").select("id, quantity, unit_price, product_id").eq("cart_id", cart_id).execute()
        items = items_resp.data or []
        if not items: 
            return {"items": [], "total": 0, "count": 0, "cart_id": cart_id}
        
        product_ids = [i["product_id"] for i in items]
        products = Product.objects.filter(id__in=product_ids).values("id", "name", "price", "slug", "supabase_image_path", "image_url", "stock", "seller__store_name")
        products_map = {p["id"]: p for p in products}
        
        cart_items, total, count = [], 0, 0
        for item in items:
            prod = products_map.get(item["product_id"])
            if prod:
                subtotal = item["unit_price"] * item["quantity"]
                total += subtotal
                count += item["quantity"]
                cart_items.append({
                    "id": item["id"], 
                    "product": prod, 
                    "quantity": item["quantity"], 
                    "unit_price": item["unit_price"], 
                    "subtotal": subtotal,
                    "get_image": (prod["supabase_image_path"] and f"{settings.SUPABASE_URL}/storage/v1/object/public/product-uploads/{prod['supabase_image_path']}") or prod["image_url"] or "https://via.placeholder.com/400?text=No+Image"
                })
        return {"items": cart_items, "total": total, "count": count, "cart_id": cart_id}
    except Exception as e:
        print(f"⚠️ Cart sync error: {e}")
        return {"items": [], "total": 0, "count": 0, "cart_id": None}

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
                # 1. CREATE USER IN SUPABASE AUTH
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
                    messages.error(
                        req,
                        "❌ Could not create Supabase account."
                    )
                    return render(
                        req,
                        "store/register.html",
                        {"form": form}
                    )

                # 2. CREATE / GET DJANGO USER
                django_user, _ = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                    }
                )

                # 3. LINK / UPDATE USERPROFILE IN DJANGO
                user_profile, _ = UserProfile.objects.get_or_create(user=django_user)
                user_profile.whatsapp_number = whatsapp
                user_profile.country = country
                user_profile.save()

                messages.success(
                    req,
                    "Account created successfully! Please log in."
                )
                return redirect("login")

            except Exception as e:
                logger.error(f"Registration failed: {e}")
                messages.error(req, f"Registration failed: {e}")

    else:
        form = CustomUserCreationForm()

    return render(req, "store/register.html", {"form": form})

# ==================== PAYSTACK PAYMENT HANDLERS ====================

@csrf_exempt
def paystack_callback(req):
    """
    Paystack Webhook / Callback Handler
    """
    reference = req.GET.get('reference') or req.POST.get('reference')
    if not reference:
        logger.error("Paystack callback invoked without a reference.")
        messages.error(req, 'Invalid transaction reference.')
        return redirect('store:checkout')

    try:
        # Verify transaction with Paystack API
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()

        paystack_status = data.get('data', {}).get('status', 'unknown')

        # ── FIX: cancelled / abandoned / failed is TERMINAL ──
        # Release the pending order, restore stock, give the cart back,
        # and send the user to checkout with a message — never leave a
        # stuck confirmation or a half-created order behind.
        if paystack_status in ('abandoned', 'cancelled', 'failed', 'reversed'):
            pending = Order.objects.filter(reference=reference).exclude(payment_status='paid')
            for order in pending:
                for item in order.orderitem_set.all():   # Default related_name for OrderItem
                    product = item.product
                    product.stock += item.quantity
                    product.save(update_fields=['stock'])
                order.delete()
            messages.error(req, 'Payment was cancelled. Your cart is intact — you can try again.')
            return redirect('store:checkout')

        if not (data.get('status') and paystack_status == 'success'):
            logger.warning(f"Payment not successful: {reference}")
            messages.info(req, 'Payment is not complete yet.')
            return redirect('store:checkout')

        # Handle successful payment logic
        order = Order.objects.filter(reference=reference).first()
        if order:
            order.payment_status = 'paid'
            order.status = 'processing'
            order.save()
            messages.success(req, 'Payment successful! Order is being processed.')
            return redirect('store:order_success')

    except Exception as e:
        logger.error(f"Error during Paystack verification: {e}")
        messages.error(req, 'Error confirming payment.')
    
    return redirect('store:checkout')

def verify_paystack_payment(req):
    """
    Endpoint polled by checkout.html frontend during payment verification
    """
    reference = req.GET.get('reference')
    if not reference:
        return JsonResponse({'success': False, 'error': 'Missing reference parameter.'}, status=400)

    try:
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()

        ps_status = data.get('data', {}).get('status')
        if ps_status in ('abandoned', 'cancelled', 'failed', 'reversed'):
            # Terminal failure — tell the frontend to STOP polling
            return JsonResponse({
                'success': False, 
                'status': 'cancelled',
                'error': 'Payment was cancelled. Please try again.'
            })

        if data.get('status') and ps_status == 'success':
            order = Order.objects.filter(reference=reference).first()
            if order:
                order.payment_status = 'paid'
                order.status = 'processing'
                order.save()
            return JsonResponse({
                'success': True,
                'status': 'success',
                'redirect_url': reverse('store:order_success')
            })

        return JsonResponse({
            'success': False,
            'status': ps_status or 'pending',
            'error': 'Payment verification pending...'
        })

    except Exception as e:
        logger.error(f"Error checking Paystack reference {reference}: {e}")
        return JsonResponse({'success': False, 'error': 'Server error during payment verification.'}, status=500)