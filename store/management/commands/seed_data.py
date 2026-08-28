from django.core.management.base import BaseCommand
from store.models import Category, Product, SellerProfile, Order, OrderItem, Review
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = "Seed data with expanded catalog"
    
    def handle(self, *args, **kwargs):
        # Expanded Categories
        cats = [
            ("Electronics", "💻"), ("Fashion", "👕"), ("Home", "🏠"), 
            ("Sports", "⚽"), ("Beauty", "💄"), ("Phones", "📱"),
            ("Computing", "⌨️"), ("Automotive", "🚗"), ("Groceries", "🛒")
        ]
        for name, icon in cats:
            Category.objects.get_or_create(name=name, defaults={"slug": name.lower(), "icon": icon})
        
        # Demo Seller
        if not User.objects.filter(username="demo_seller").exists():
            u = User.objects.create_user(username="demo_seller", email="s@d.com", password="seller123")
            SellerProfile.objects.create(user=u, store_name="VibeTech Official", description="Premium electronics & lifestyle", phone="+234 800 123 4567", address="Lagos, Nigeria")
        
        # Demo Buyer
        buyer, _ = User.objects.get_or_create(username="shopper1", defaults={"email": "b@d.com"})
        if _: buyer.set_password("shopper123"); buyer.save()
        
        seller = SellerProfile.objects.first()
        
        # Expanded Product Catalog (10+ items with real Unsplash images)
        prods = [
            ("Wireless ANC Headphones", 89.99, 40, "Electronics", "SoundMax", "Active Noise Cancel\n30h Battery\nBluetooth 5.3", "Black, Silver", "2Y", "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500"),
            ("Smart Fitness Watch", 149.99, 35, "Electronics", "FitGear", "Heart Rate Monitor\nGPS Tracking\nIP68 Waterproof", "Space Gray, Rose Gold", "1Y", "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500"),
            ("Premium Running Shoes", 119.99, 50, "Sports", "AeroStride", "Lightweight Mesh\nCloud Cushion\nAnti-Slip Grip", "White/Blue, Black", "6M", "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500"),
            ("Leather Crossbody Bag", 79.99, 25, "Fashion", "LuxeCraft", "Genuine Leather\nRFID Blocking\nAdjustable Strap", "Brown, Charcoal", "Lifetime", "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500"),
            ("Mechanical Keyboard", 69.99, 30, "Computing", "KeyMaster", "Blue Switches\nRGB Backlight\nHot-Swappable", "Black, White", "1Y", "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500"),
            ("Portable Bluetooth Speaker", 45.99, 45, "Electronics", "SoundWave", "360° Sound\nIPX7 Waterproof\n12h Playtime", "Black, Red, Blue", "1Y", "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=500"),
            ("Organic Face Moisturizer", 24.99, 60, "Beauty", "GlowLab", "Hyaluronic Acid\nVitamin C\nDermatologist Tested", "Clear", "N/A", "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=500"),
            ("Smart Home Speaker", 99.99, 20, "Electronics", "EchoTech", "Voice Assistant\nMulti-Room Audio\nSmart Hub Built-in", "Charcoal, Sand", "1Y", "https://images.unsplash.com/photo-1589003077984-894e133dabab?w=500"),
            ("Yoga Mat Premium", 29.99, 80, "Sports", "ZenFit", "6mm Thickness\nNon-Slip Surface\nEco-Friendly TPE", "Purple, Green, Black", "Lifetime", "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=500"),
            ("Stainless Water Bottle", 19.99, 100, "Sports", "HydraPure", "Vacuum Insulated\nKeeps Cold 24h\nBPA Free", "Matte Black, Silver, Teal", "N/A", "https://images.unsplash.com/photo-1602143407151-0111d256631a?w=500"),
        ]
        
        for name, price, stock, cat_name, brand, feats, col, war, img in prods:
            Product.objects.get_or_create(
                name=name,
                defaults={
                    "category": Category.objects.get(name=cat_name),
                    "seller": seller,
                    "price": price,
                    "stock": stock,
                    "brand": brand,
                    "description": f"Premium quality {name} designed for everyday performance.",
                    "features": feats,
                    "colors": col,
                    "warranty": war,
                    "image_url": img,
                    "is_active": True,
                }
            )
        
        # Sample Order & Review
        prod = Product.objects.first()
        if prod and not Order.objects.exists():
            o = Order.objects.create(user=buyer, total=prod.price * 2, address="123 Main St, Lagos")
            OrderItem.objects.create(order=o, product=prod, quantity=2, price=prod.price)
            Review.objects.create(user=buyer, product=prod, rating=5, comment="Excellent build quality and fast delivery!")
            for i in range(1, 4):
                o2 = Order.objects.create(user=buyer, total=prod.price * i, address="123 Main St", created_at=timezone.now() - timedelta(days=i*30))
                OrderItem.objects.create(order=o2, product=prod, quantity=i, price=prod.price)
        
        self.stdout.write(self.style.SUCCESS("✅ 10 Products & Categories Loaded"))
        self.stdout.write(self.style.SUCCESS("🔑 demo_seller / seller123"))