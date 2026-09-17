from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0042_sellerfollow'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='buyer_region',
            field=models.CharField(blank=True, default='', help_text='Region/state/province entered by the buyer', max_length=100),
        ),
        migrations.AddField(
            model_name='conversation',
            name='buyer_town',
            field=models.CharField(blank=True, default='', help_text='Town/city entered by the buyer', max_length=100),
        ),
        migrations.RemoveField(
            model_name='conversation',
            name='buyer_latitude',
        ),
        migrations.RemoveField(
            model_name='conversation',
            name='buyer_longitude',
        ),
        migrations.RemoveField(
            model_name='conversation',
            name='buyer_location_accuracy',
        ),
        migrations.RemoveField(
            model_name='conversation',
            name='buyer_location_label',
        ),
    ]
