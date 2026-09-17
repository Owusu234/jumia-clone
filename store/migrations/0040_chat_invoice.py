from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('store', '0039_cartitem_is_shared'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('buyer_latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('buyer_longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('buyer_location_label', models.CharField(blank=True, default='', max_length=255)),
                ('buyer_location_accuracy', models.FloatField(blank=True, help_text='Accuracy radius in metres reported by the browser', null=True)),
                ('location_shared_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buyer_conversations', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='store.product')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='store.sellerprofile')),
            ],
            options={
                'ordering': ['-updated_at'],
                'unique_together': {('product', 'buyer')},
            },
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('color', models.CharField(blank=True, default='', max_length=50)),
                ('size', models.CharField(blank=True, default='', max_length=50)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('delivery_fee', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('note', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('pending', 'Awaiting payment'), ('paid', 'Paid'), ('cancelled', 'Cancelled')], default='pending', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to=settings.AUTH_USER_MODEL)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='store.conversation')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoices', to='store.order')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='store.product')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='store.sellerprofile')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('text', 'Text'), ('location', 'Location'), ('invoice', 'Invoice'), ('system', 'System')], default='text', max_length=10)),
                ('body', models.TextField(blank=True, default='')),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='store.conversation')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='store.invoice')),
                ('sender', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chat_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
