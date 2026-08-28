# store/management/commands/seed_countries.py
from django.core.management.base import BaseCommand
from store.models import Country

class Command(BaseCommand):
    help = 'Seed initial country data for phone formatting & currency'

    def handle(self, *args, **options):
        countries = [
            {"name": "Ghana", "code": "GHA", "phone_code": "+233", "currency": "GHS", "is_active": True},
            {"name": "Nigeria", "code": "NGA", "phone_code": "+234", "currency": "NGN", "is_active": True},
            {"name": "Kenya", "code": "KEN", "phone_code": "+254", "currency": "KES", "is_active": True},
            {"name": "South Africa", "code": "ZAF", "phone_code": "+27", "currency": "ZAR", "is_active": True},
            {"name": "United States", "code": "USA", "phone_code": "+1", "currency": "USD", "is_active": True},
            {"name": "United Kingdom", "code": "GBR", "phone_code": "+44", "currency": "GBP", "is_active": True},
            {"name": "India", "code": "IND", "phone_code": "+91", "currency": "INR", "is_active": True},
        ]

        created_count = 0
        for c in countries:
            obj, created = Country.objects.update_or_create(
                code=c["code"], defaults=c
            )
            if created: created_count += 1
            
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully seeded {created_count} new countries."))