from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User
from supabase import create_client
from store.models import SellerProfile

class Command(BaseCommand):
    help = "Create or promote a superadmin with full seller & buyer capabilities"

    def handle(self, *args, **kwargs):
        email = getattr(settings, "ADMIN_EMAIL", None)
        username = getattr(settings, "ADMIN_USERNAME", "superadmin")
        password = getattr(settings, "ADMIN_PASSWORD", None)
        service_key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)

        if not all([email, password, service_key]):
            self.stdout.write(self.style.ERROR("❌ Missing ADMIN_EMAIL, ADMIN_PASSWORD, or SUPABASE_SERVICE_ROLE_KEY in .env"))
            return

        supabase = create_client(settings.SUPABASE_URL, service_key)
        self.stdout.write(self.style.SUCCESS(f"🔧 Initializing setup for: {email}"))

        # 1️⃣ SUPABASE AUTH SYNC
        try:
            supabase.auth.admin.create_user({
                "email": email, "password": password, "email_confirm": True,
                "user_metadata": {"username": username, "role": "superadmin"}
            })
            self.stdout.write(self.style.SUCCESS("✅ Supabase user created."))
        except Exception as e:
            if any(x in str(e).lower() for x in ["already exists", "duplicate", "constraint", "unique"]):
                self.stdout.write(self.style.WARNING("⚠️ Supabase user exists. Fetching & updating metadata..."))
                response = supabase.auth.admin.list_users()
                users = []
                if isinstance(response, dict): users = response.get("users") or response.get("data") or []
                elif hasattr(response, "users"): users = response.users
                elif isinstance(response, list): users = response
                
                target = next((u for u in users if getattr(u, "email", "").lower() == email.lower()), None)
                if target:
                    uid = getattr(target, "id", None) or target.get("id")
                    supabase.auth.admin.update_user_by_id(user_id=uid, attributes={"data": {"role": "superadmin", "username": username}})
                    self.stdout.write(self.style.SUCCESS("✅ Supabase metadata updated to superadmin."))
                else:
                    self.stdout.write(self.style.ERROR("❌ Could not locate user in Supabase."))
                    return
            else:
                self.stdout.write(self.style.ERROR(f"❌ Supabase error: {str(e)}"))
                return

        # 2️⃣ DJANGO USER SYNC
        django_user = User.objects.filter(email=email).first()
        if not django_user:
            django_user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
        
        if django_user.username != username:
            django_user.username = username
            django_user.save()

        if not django_user.is_superuser or not django_user.is_staff:
            django_user.is_superuser = True
            django_user.is_staff = True
            django_user.set_unusable_password()
            django_user.save()
            self.stdout.write(self.style.WARNING("⚠️ Promoted Django user to superuser & staff."))

        # 3️⃣ AUTO-CREATE SELLER PROFILE
        if not SellerProfile.objects.filter(user=django_user).exists():
            SellerProfile.objects.create(
                user=django_user,
                store_name=f"{django_user.username}'s Admin Store",
                description="Official ShopVibe Superadmin Store",
                phone="+233000000000",
                address="ShopVibe HQ, Accra, Ghana",
                is_verified=True
            )
            self.stdout.write(self.style.SUCCESS("✅ Auto-created SellerProfile for product uploads."))

        self.stdout.write(self.style.SUCCESS("\n🎉 SUPERADMIN READY!"))
        self.stdout.write(self.style.WARNING("🔐 Logout & login again to apply role/session changes."))