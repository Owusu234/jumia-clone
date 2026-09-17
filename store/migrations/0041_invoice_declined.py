from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0040_chat_invoice'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Awaiting payment'),
                    ('paid', 'Paid'),
                    ('cancelled', 'Cancelled'),
                    ('declined', 'Declined'),
                ],
                default='pending',
                max_length=10,
            ),
        ),
    ]
