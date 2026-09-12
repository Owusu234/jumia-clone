from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0035_rename_store_userno_user_id_9e8e5b_idx_store_usern_user_id_90270f_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='guest_email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
    ]
