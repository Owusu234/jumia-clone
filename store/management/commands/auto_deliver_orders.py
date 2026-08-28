# store/management/commands/auto_deliver_orders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from store.models import Order

class Command(BaseCommand):
    help = "Auto-mark orders as Delivered if estimated delivery date has passed"

    def handle(self, *args, **options):
        today = timezone.now().date()
        # Find orders that are "Out for Delivery" and past estimated date
        orders = Order.objects.filter(
            status="Out for Delivery",
            estimated_delivery__lt=today,
            delivered_at__isnull=True
        )
        
        updated = 0
        for order in orders:
            order.status = "Delivered"
            order.save()  # This triggers delivered_at auto-set
            updated += 1
            self.stdout.write(f"✅ Marked Order #{order.id} as Delivered")
        
        self.stdout.write(self.style.SUCCESS(f"🎉 Auto-delivered {updated} orders"))