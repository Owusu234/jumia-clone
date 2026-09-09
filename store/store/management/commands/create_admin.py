import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from store.models import UserProfile
from store.views import get_supabase_client, update_supabase_prof

class Command(BaseCommand):
    help = 'Creates or updates the initial Superadmin account (syncs WhatsApp & Supabase)'

    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME")
        email = os.getenv("ADMIN_EMAIL")
        password = os.getenv("ADMIN_PASSWORD")
        whatsapp = os.getenv("ADMIN_WHATSAPP", "")

        if not all([username, email, password]):
            self.stdout.write(self.style.ERROR("❌ ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD must be set in .env"))
            return

        # Create or get Django admin
        admin, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_superuser": True, "is_staff": True}
        )
        
        admin.email = email
        admin.set_password(password)
        admin.is_superuser = True
        admin.is_staff = True
        admin.save()

        # Ensure UserProfile exists
        UserProfile.objects.get_or_create(user=admin)

        # Sync to Supabase Auth
        try:
            supabase = get_supabase_client()
            supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "username": username, 
                    "role": "admin", 
                    "whatsapp_number": whatsapp
                }
            })
        except Exception:
            pass  # Safe to ignore if already exists in Supabase

        # Sync to prof table
        update_supabase_prof(admin.id, {
            "username": username,
            "email": email,
            "whatsapp_number": whatsapp,
            "is_seller": False
        })
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Created admin: {username} | WhatsApp: {whatsapp}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Updated existing admin: {username} | WhatsApp: {whatsapp}"))