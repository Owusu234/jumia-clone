from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('store', '0030_alter_cartinvite_id')]
    operations = [
        migrations.AddField(model_name='review', name='image', field=models.ImageField(blank=True, help_text='Optional buyer photo. Stored at passport-photo dimensions (350×450 px).', null=True, upload_to='reviews/')),
        migrations.AddField(model_name='cartitem', name='size', field=models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField(model_name='orderitem', name='color', field=models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField(model_name='orderitem', name='size', field=models.CharField(blank=True, default='', max_length=50)),
        migrations.AlterUniqueTogether(name='cartitem', unique_together={('cart', 'product', 'color', 'size')}),
    ]
