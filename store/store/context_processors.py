from .models import AdminNotification

def global_context(req):
    """Provides cart_count, global variables, and admin notifications to all templates"""
    
    # ─────────────────────────────────────────────────────────────────────────────
    # 1️⃣ YOUR EXISTING CART & GLOBAL LOGIC (100% Preserved)
    # ─────────────────────────────────────────────────────────────────────────────
    cart = req.session.get('cart', {})
    
    # Safely calculate total items
    cart_count = 0
    for qty in cart.values():
        try:
            cart_count += int(qty)
        except (ValueError, TypeError):
            pass
            
    context = {
        'cart_count': cart_count,
        'SITE_NAME': 'ShopVibe',
        'SITE_URL': req.build_absolute_uri('/').rstrip('/')
    }

    # ─────────────────────────────────────────────────────────────────────────────
    # 2️⃣ NEW: ADMIN NOTIFICATION LOGIC (Only runs for Staff/Admins)
    # ─────────────────────────────────────────────────────────────────────────────
    if req.user.is_authenticated and (req.user.is_staff or req.user.is_superuser):
        # Unread count for bell badge
        context['admin_notification_count'] = AdminNotification.objects.filter(is_read=False).count()
        
        # 5 most recent unread alerts for dropdown
        context['admin_notifications'] = AdminNotification.objects.filter(is_read=False).order_by('-created_at')[:5]
    else:
        # Fallback for buyers/guests to prevent template errors
        context['admin_notification_count'] = 0
        context['admin_notifications'] = []

    return context