# store/management/commands/wipe_all_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session

class Command(BaseCommand):
    help = "Permanently deletes all users and cascades related data (products, orders, sessions)."

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help="Required to confirm irreversible deletion")

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.ERROR("⚠️  Use --confirm to proceed. This will DELETE ALL users, products, and orders."))
            return

        count = User.objects.count()
        self.stdout.write(f"🗑️  Deleting {count} users and cascading related data...")
        
        User.objects.all().delete()
        Session.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully wiped {count} users and all related data."))