import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('store', '0032_review_review_image_url')]
    operations = [
        migrations.CreateModel(
            name='SharedCartLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='shared_cart_links', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RemoveField(model_name='cart', name='members'),
        migrations.DeleteModel(name='CartInvite'),
    ]
