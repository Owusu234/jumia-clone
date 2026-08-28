from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

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