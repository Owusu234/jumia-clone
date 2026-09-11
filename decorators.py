from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def guest_or_login_required(view_func):
    """Like @login_required, but also lets an anonymous visitor through when
    they're paying for someone else's shared cart (a 'gift' purchase started
    via start_shared_cart_purchase). Guests can never check out their own
    regular cart or a 'self' shared-cart purchase — only a shared-cart gift.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        shared_purchase = request.session.get('shared_purchase')
        is_guest_gift = (
            isinstance(shared_purchase, dict)
            and shared_purchase.get('action') == 'gift'
        )
        if request.user.is_authenticated or is_guest_gift:
            return view_func(request, *args, **kwargs)
        messages.info(request, "🔐 Please log in to check out.")
        return redirect('store:login')
    return _wrapped_view


def seller_approved_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'seller_profile'):
            messages.warning(request, "📝 Please register as a seller first.")
            return redirect('store:seller_signup')
        
        if request.user.seller_profile.status != 'approved':
            status = request.user.seller_profile.status
            if status == 'pending':
                messages.info(request, "⏳ Your application is pending admin approval.")
            elif status == 'rejected':
                messages.error(request, f"❌ Application rejected: {request.user.seller_profile.rejected_reason}")
            return redirect('store:profile')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view