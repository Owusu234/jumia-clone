from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("store", "0044_chatmessage_soft_delete"),
    ]

    operations = [
        migrations.CreateModel(
            name="CartItemShare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("cart_item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recipient_shares", to="store.cartitem")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="received_cart_item_shares", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="cartitemshare",
            constraint=models.UniqueConstraint(fields=("cart_item", "recipient"), name="unique_cart_item_recipient_share"),
        ),
    ]
