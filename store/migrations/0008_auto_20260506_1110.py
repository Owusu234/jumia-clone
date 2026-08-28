# store/migrations/0008_auto_20260506_1110.py
from django.db import migrations

PREDEFINED_CATEGORIES = [
    ("smartphones", "Smartphones", "📱"),
    ("laptops", "Laptops & Computers", "💻"),
    ("tablets", "Tablets", "📟"),
    ("audio", "Audio & Headphones", "🎧"),
    ("cameras", "Cameras & Photography", "📷"),
    ("accessories", "Tech Accessories", "🔌"),
    ("gaming", "Gaming", "🎮"),
    ("mens-fashion", "Men's Fashion", "👔"),
    ("womens-fashion", "Women's Fashion", "👗"),
    ("kids-fashion", "Kids' Fashion", "🧒"),
    ("shoes", "Shoes & Sneakers", "👟"),
    ("bags", "Bags & Luggage", "👜"),
    ("watches", "Watches", "⌚"),
    ("beauty", "Beauty & Cosmetics", "💄"),
    ("fragrance", "Fragrances", "🌸"),
    ("furniture", "Furniture", "🪑"),
    ("home-decor", "Home Decor", "🏠"),
    ("kitchen", "Kitchen & Dining", "🍳"),
    ("bedding", "Bedding & Bath", "🛏️"),
    ("appliances", "Home Appliances", "🔌"),
    ("gardening", "Gardening", "🌱"),
    ("health", "Health & Wellness", "💊"),
    ("personal-care", "Personal Care", "🧴"),
    ("baby-care", "Baby & Toddler", "🍼"),
    ("sports", "Sports & Fitness", "⚽"),
    ("outdoor", "Outdoor & Camping", "🏕️"),
    ("cycling", "Cycling", "🚴"),
    ("automotive", "Automotive", "🚗"),
    ("tools", "Tools & Hardware", "🔧"),
    ("electrical", "Electrical & Lighting", "⚡"),
    ("books", "Books & Literature", "📚"),
    ("music", "Music & Instruments", "🎵"),
    ("movies", "Movies & TV", "🎬"),
    ("food", "Food & Beverages", "🍎"),
    ("groceries", "Groceries", "🛒"),
    ("toys", "Toys & Games", "🧸"),
    ("pet-supplies", "Pet Supplies", "🐾"),
    ("office", "Office Supplies", "🖊️"),
    ("crafts", "Arts & Crafts", "🎨"),
]

def populate_categories(apps, schema_editor):
    Category = apps.get_model('store', 'Category')
    for slug, name, icon in PREDEFINED_CATEGORIES:
        Category.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'icon': icon}
        )

def reverse_populate(apps, schema_editor):
    Category = apps.get_model('store', 'Category')
    slugs = [slug for slug, _, _ in PREDEFINED_CATEGORIES]
    Category.objects.filter(slug__in=slugs).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('store', '0007_remove_order_store_order_trackin_132e03_idx_and_more'),
    ]
    operations = [
        migrations.RunPython(populate_categories, reverse_populate),
    ]