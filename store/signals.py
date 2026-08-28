from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import SellerProfile, AdminNotification

@receiver(post_save, sender=User)
def auto_create_seller_for_superuser(sender, instance, created, **kwargs):
    """Auto-create a verified SellerProfile for superusers."""
    if instance.is_superuser and not SellerProfile.objects.filter(user=instance).exists():
        SellerProfile.objects.create(
            user=instance,
            store_name=f"{instance.username}'s Admin Store",
            description="Official ShopVibe Superadmin Store",
            phone="+233000000000",
            address="ShopVibe HQ, Accra, Ghana",
            is_verified=True
        )


@receiver(post_save, sender=SellerProfile)
def notify_admin_on_seller_application(sender, instance, created, **kwargs):
    if created and instance.status == 'pending':
        AdminNotification.objects.create(
            title="🆕 New Seller Application",
            message=f"{instance.user.username} applied with store: {instance.store_name}",
            link=f"/admin/seller/{instance.id}/application/"  # ✅ Links to detail page
        )