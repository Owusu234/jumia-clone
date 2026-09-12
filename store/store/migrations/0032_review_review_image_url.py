from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("store", "0031_product_variants_review_image_orderitem_variants")]

    operations = [
        migrations.AddField(
            model_name="review",
            name="review_image_url",
            field=models.URLField(blank=True, max_length=1000, null=True),
        ),
    ]
