# store/middleware.py

class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Skip static, media, auth, and completion pages
            skip_paths = ['/static/', '/media/', '/login/', '/logout/', '/register/', '/complete-profile/']
            if any(request.path.startswith(path) for path in skip_paths):
                return self.get_response(request)

            try:
                profile = getattr(request.user, 'user_profile', None)
                
                # ✅ FIXED: Check 'country' (text field) instead of 'country_id' (ForeignKey)
                country_ok = profile and getattr(profile, 'country', None)
                
                if not profile or not country_ok:
                    return self._redirect_to_completion(request)
                
                # Check seller fields if applicable
                if hasattr(request.user, 'seller_profile'):
                    seller = request.user.seller_profile
                    if not getattr(seller, 'region', None) or not getattr(seller, 'payment_number', None):
                        return self._redirect_to_completion(request)
                        
            except Exception:
                # If DB schema is out of sync, skip middleware check gracefully
                pass

        return self.get_response(request)

    def _redirect_to_completion(self, request):
        from django.shortcuts import redirect
        from django.urls import reverse
        next_url = request.path
        completion_url = reverse('store:complete_profile')
        return redirect(f"{completion_url}?next={next_url}")