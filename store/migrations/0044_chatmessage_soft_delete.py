from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0043_conversation_buyer_area'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
