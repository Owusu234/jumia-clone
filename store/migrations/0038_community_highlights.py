from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("store", "0037_cartinvite"),
    ]

    operations = [
        migrations.CreateModel(
            name="SellerHighlightGoal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True, help_text="Uncheck to pause rewards. Buyers can still post highlights.")),
                ("points_goal", models.PositiveIntegerField(default=15, help_text="Engagement points a highlight must reach to unlock the reward (e.g. 15).")),
                ("discount_percent", models.PositiveSmallIntegerField(default=10, help_text="Percentage off the buyer receives as a voucher, 1\u201390.")),
                ("voucher_validity_days", models.PositiveSmallIntegerField(default=30, help_text="How many days the unlocked voucher stays valid.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("seller", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="highlight_goal", to="store.sellerprofile")),
            ],
            options={
                "verbose_name": "Seller Highlight Goal",
                "verbose_name_plural": "Seller Highlight Goals",
            },
        ),
        migrations.CreateModel(
            name="CommunityHighlight",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("body", models.TextField(help_text="How was the unboxing?", max_length=2000)),
                ("media_url", models.URLField(blank=True, default="", max_length=1000)),
                ("media_type", models.CharField(choices=[("image", "Photo"), ("video", "Video")], default="image", max_length=10)),
                ("media_storage_path", models.CharField(blank=True, default="", max_length=500)),
                ("points_goal", models.PositiveIntegerField(default=15)),
                ("discount_percent", models.PositiveSmallIntegerField(default=10)),
                ("total_points", models.PositiveIntegerField(db_index=True, default=0)),
                ("like_count", models.PositiveIntegerField(default=0)),
                ("comment_count", models.PositiveIntegerField(default=0)),
                ("share_count", models.PositiveIntegerField(default=0)),
                ("reward_unlocked", models.BooleanField(db_index=True, default=False)),
                ("unlocked_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("is_approved", models.BooleanField(default=True, help_text="Uncheck to hide from the public feed.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("buyer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="community_highlights", to=settings.AUTH_USER_MODEL)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="highlights", to="store.order")),
                ("order_item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="highlights", to="store.orderitem")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="highlights", to="store.product")),
                ("seller", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="highlights", to="store.sellerprofile")),
            ],
            options={
                "verbose_name": "Community Highlight",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="HighlightEngagement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("like", "Like"), ("comment", "Comment"), ("share", "Share")], max_length=10)),
                ("points", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("highlight", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="engagements", to="store.communityhighlight")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="highlight_engagements", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="HighlightComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(max_length=600)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("highlight", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="store.communityhighlight")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="highlight_comments", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="DiscountVoucher",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(db_index=True, max_length=32, unique=True)),
                ("discount_percent", models.PositiveSmallIntegerField(default=10)),
                ("is_used", models.BooleanField(default=False)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("buyer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="discount_vouchers", to=settings.AUTH_USER_MODEL)),
                ("highlight", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="voucher", to="store.communityhighlight")),
                ("seller", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="issued_vouchers", to="store.sellerprofile")),
                ("used_on_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="applied_vouchers", to="store.order")),
            ],
            options={
                "verbose_name": "Discount Voucher",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="communityhighlight",
            index=models.Index(fields=["-created_at"], name="store_ch_created_idx"),
        ),
        migrations.AddIndex(
            model_name="communityhighlight",
            index=models.Index(fields=["-total_points"], name="store_ch_points_idx"),
        ),
        migrations.AddIndex(
            model_name="communityhighlight",
            index=models.Index(fields=["seller", "-created_at"], name="store_ch_seller_idx"),
        ),
        migrations.AddConstraint(
            model_name="communityhighlight",
            constraint=models.UniqueConstraint(fields=("buyer", "order_item"), name="uniq_highlight_per_order_item"),
        ),
        migrations.AddIndex(
            model_name="highlightengagement",
            index=models.Index(fields=["highlight", "action"], name="store_he_hl_action_idx"),
        ),
        migrations.AddConstraint(
            model_name="highlightengagement",
            constraint=models.UniqueConstraint(fields=("highlight", "user", "action"), name="uniq_engagement_per_user_action"),
        ),
        migrations.AddIndex(
            model_name="highlightcomment",
            index=models.Index(fields=["highlight", "created_at"], name="store_hc_hl_created_idx"),
        ),
        migrations.AddIndex(
            model_name="discountvoucher",
            index=models.Index(fields=["buyer", "is_used"], name="store_dv_buyer_used_idx"),
        ),
    ]
