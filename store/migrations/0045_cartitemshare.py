from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0044_chatmessage_soft_delete'),
    ]

    operations = [
        migrations.CreateModel(
            name='CartItemShare',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipient_shares', to='store.cartitem')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_cart_item_shares', to='auth.user')),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(fields=('item', 'recipient'), name='unique_cart_item_recipient_share'),
                ],
            },
        ),
    ]
