# store/management/commands/seed_regions.py
from django.core.management.base import BaseCommand
from store.models import Country, Region

class Command(BaseCommand):
    help = 'Seed region/state data for countries'

    def handle(self, *args, **options):
        regions_data = {
            "GHA": [
                {"name": "Greater Accra", "code": "GA"},
                {"name": "Ashanti", "code": "AH"},
                {"name": "Western", "code": "WP"},
                {"name": "Eastern", "code": "EP"},
                {"name": "Central", "code": "CP"},
                {"name": "Volta", "code": "TV"},
                {"name": "Northern", "code": "NP"},
                {"name": "Upper East", "code": "UE"},
                {"name": "Upper West", "code": "UW"},
                {"name": "Brong-Ahafo", "code": "BA"},
            ],
            "NGA": [
                {"name": "Lagos", "code": "LA"},
                {"name": "Abuja (FCT)", "code": "FC"},
                {"name": "Rivers", "code": "RI"},
                {"name": "Kano", "code": "KN"},
                {"name": "Oyo", "code": "OY"},
                {"name": "Edo", "code": "ED"},
                {"name": "Delta", "code": "DE"},
                {"name": "Anambra", "code": "AN"},
            ],
            "KEN": [
                {"name": "Nairobi", "code": "NB"},
                {"name": "Mombasa", "code": "MB"},
                {"name": "Kisumu", "code": "KS"},
                {"name": "Nakuru", "code": "NK"},
                {"name": "Kiambu", "code": "KB"},
            ],
            "ZAF": [
                {"name": "Gauteng", "code": "GT"},
                {"name": "Western Cape", "code": "WC"},
                {"name": "KwaZulu-Natal", "code": "NL"},
                {"name": "Eastern Cape", "code": "EC"},
                {"name": "Limpopo", "code": "LP"},
            ],
            "USA": [
                {"name": "California", "code": "CA"},
                {"name": "New York", "code": "NY"},
                {"name": "Texas", "code": "TX"},
                {"name": "Florida", "code": "FL"},
                {"name": "Illinois", "code": "IL"},
            ],
            "GBR": [
                {"name": "England", "code": "ENG"},
                {"name": "Scotland", "code": "SCT"},
                {"name": "Wales", "code": "WLS"},
                {"name": "Northern Ireland", "code": "NIR"},
            ],
        }

        created_count = 0
        for country_code, regions in regions_data.items():
            try:
                country = Country.objects.get(code=country_code)
                for r in regions:
                    obj, created = Region.objects.get_or_create(
                        country=country,
                        name=r["name"],
                        defaults={"code": r["code"]}
                    )
                    if created:
                        created_count += 1
            except Country.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"⚠️  Country {country_code} not found. Skipping."))

        self.stdout.write(self.style.SUCCESS(f"✅ Successfully seeded {created_count} new regions."))