from .models import AdminNotification, UserNotification

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
        context['admin_notification_count'] = 0
        context['admin_notifications'] = []

    if req.user.is_authenticated:
        context['user_notification_count'] = UserNotification.objects.filter(
            user=req.user, is_read=False
        ).count()
        context['user_notifications'] = UserNotification.objects.filter(
            user=req.user, is_read=False
        ).order_by('-created_at')[:5]
    else:
        context['user_notification_count'] = 0
        context['user_notifications'] = []

    return context