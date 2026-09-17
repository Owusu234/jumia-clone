from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0038_community_highlights'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='is_shared',
            field=models.BooleanField(default=False),
        ),
    ]
