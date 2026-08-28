# store/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.text import slugify
from django.db.models import Avg
from django.conf import settings
from django.utils import timezone

from django.db.models.signals import post_delete
from django.dispatch import receiver

# ==================== USER PROFILES ====================

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=3, unique=True, help_text="ISO 3166-1 alpha-3 code")
    phone_code = models.CharField(max_length=5, help_text="e.g., +233 for Ghana")
    currency = models.CharField(max_length=3, default="GHS", help_text="ISO 4217 currency code")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.phone_code})"
    
    class Meta:
        ordering = ['name']

# store/models.py - Update UserProfile model

# store/models.py

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_profile")
    avatar = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, default="Shopper")
    whatsapp_number = models.CharField(max_length=20, blank=True)
    
    # ✅ Changed from ForeignKey to CharField
    country = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Country of residence"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self): return self.user.username
    
    def get_avatar_url(self):
        if not self.avatar:
            return "https://via.placeholder.com/150?text=No+Avatar"
        return str(self.avatar) if str(self.avatar).startswith("http") else f"{settings.MEDIA_URL}{self.avatar}"
    
    class Meta:
        verbose_name_plural = "User Profiles"

class SellerProfile(models.Model):
    """Seller-specific profile - also synced to Supabase 'prof' table"""
    
    # ✅ NEW: Verification status choices
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="seller_profile")
    store_name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, help_text="Store description")
    phone = models.CharField(max_length=20, help_text="Business phone number")
    address = models.TextField(help_text="Business address")
    is_verified = models.BooleanField(default=False, help_text="Admin-verified seller")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    region = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="State/Region/Province for delivery & tax calculations"
    )
    payment_number = models.CharField(
        max_length=20, 
        blank=True, 
        help_text="Mobile money or bank-linked number for receiving payments"
    )
    
    # ✅ NEW: Approval workflow fields
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        help_text="Current verification status"
    )
    verified_at = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="Timestamp when admin approved"
    )
    rejected_reason = models.TextField(
        blank=True, 
        default='', 
        help_text="Reason for rejection (visible to seller)"
    )
    admin_notes = models.TextField(
        blank=True, 
        default='', 
        help_text="Internal admin notes (not visible to seller)"
    )
    
    def __str__(self): 
        return self.store_name
    
    class Meta:
        verbose_name_plural = "Seller Profiles"
        ordering = ['-created_at']

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Auto-create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)
    instance.user_profile.save(update_fields=['updated_at'])


class AdminNotification(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.URLField(blank=True, default='#')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['is_read', '-created_at'])]

    def __str__(self):
        return f"{self.title} ({'Read' if self.is_read else 'Unread'})"

# ==================== PRODUCTS & CATEGORIES ====================

# store/models.py - Update Category model

class Category(models.Model):
    PREDEFINED_CATEGORIES = [
        # Electronics & Tech
        ("smartphones", "Smartphones", "📱"),
        ("laptops", "Laptops & Computers", "💻"),
        ("tablets", "Tablets", "📟"),
        ("audio", "Audio & Headphones", "🎧"),
        ("cameras", "Cameras & Photography", "📷"),
        ("accessories", "Tech Accessories", "🔌"),
        ("gaming", "Gaming", "🎮"),
        
        # Fashion & Beauty
        ("mens-fashion", "Men's Fashion", "👔"),
        ("womens-fashion", "Women's Fashion", "👗"),
        ("kids-fashion", "Kids' Fashion", "🧒"),
        ("shoes", "Shoes & Sneakers", "👟"),
        ("bags", "Bags & Luggage", "👜"),
        ("watches", "Watches", "⌚"),
        ("beauty", "Beauty & Cosmetics", "💄"),
        ("fragrance", "Fragrances", "🌸"),
        
        # Home & Living
        ("furniture", "Furniture", "🪑"),
        ("home-decor", "Home Decor", "🏠"),
        ("kitchen", "Kitchen & Dining", "🍳"),
        ("bedding", "Bedding & Bath", "🛏️"),
        ("appliances", "Home Appliances", "🔌"),
        ("gardening", "Gardening", "🌱"),
        
        # Health & Personal Care
        ("health", "Health & Wellness", "💊"),
        ("personal-care", "Personal Care", "🧴"),
        ("baby-care", "Baby & Toddler", "🍼"),
        
        # Sports & Outdoors
        ("sports", "Sports & Fitness", "⚽"),
        ("outdoor", "Outdoor & Camping", "🏕️"),
        ("cycling", "Cycling", "🚴"),
        
        # Automotive & Tools
        ("automotive", "Automotive", "🚗"),
        ("tools", "Tools & Hardware", "🔧"),
        ("electrical", "Electrical & Lighting", "⚡"),
        
        # Books & Media
        ("books", "Books & Literature", "📚"),
        ("music", "Music & Instruments", "🎵"),
        ("movies", "Movies & TV", "🎬"),
        
        # Food & Grocery
        ("food", "Food & Beverages", "🍎"),
        ("groceries", "Groceries", "🛒"),
        
        # Others
        ("toys", "Toys & Games", "🧸"),
        ("pet-supplies", "Pet Supplies", "🐾"),
        ("office", "Office Supplies", "🖊️"),
        ("crafts", "Arts & Crafts", "🎨"),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.CharField(max_length=10, default="📦", help_text="Emoji icon")
    is_active = models.BooleanField(default=True, help_text="Show category in storefront")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        # Auto-set icon from predefined list if slug matches
        for slug, name, icon in self.PREDEFINED_CATEGORIES:
            if slug == self.slug:
                self.icon = icon
                break
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.icon} {self.name}"
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

class Product(models.Model):
    # ✅ on_delete=CASCADE ensures products are deleted when seller is removed
    seller = models.ForeignKey(SellerProfile, null=True, blank=True, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(help_text="Product description, features, specifications")
    colors = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Comma-separated: Red, Blue, Black"
    )
    warranty = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="e.g., 1 Year Manufacturer Warranty"
    )
    warranty = models.CharField(max_length=100, blank=True)

    # ── VR / 3D fields (optional, set by seller) ──
    vr_type = models.CharField(
        max_length=20,
        choices=[('3d_model', '3D Model'), ('360_image', '360 Image')],
        blank=True, null=True
    )
    vr_supabase_path = models.CharField(max_length=500, blank=True, null=True,
        help_text="Supabase storage path for the VR file (GLB or 360 image)")

    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image_url = models.URLField(max_length=500, blank=True)
    supabase_image_path = models.CharField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug or self.slug.strip() == '':
            base = slugify(self.name) or f"product-{self.id}"
            slug, counter = base, 1
            while Product.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base}-{counter}"; counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    @property
    def avg_rating(self):
        return round(self.review_set.aggregate(rating_avg=Avg("rating"))["rating_avg"] or 0, 1)
    
    def get_image(self):
        if self.supabase_image_path: return f"{settings.SUPABASE_URL}/storage/v1/object/public/product-uploads/{self.supabase_image_path}"
        if self.image_url: return self.image_url if self.image_url.startswith("http") else f"https://{self.image_url}"
        return "https://via.placeholder.com/400?text=No+Image"

    @property
    def vr_model_url(self):
        """Public URL of the VR file stored in Supabase, or None."""
        if self.vr_supabase_path:
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/product-uploads/{self.vr_supabase_path}"
        return None
    
    def get_colors(self): return [c.strip() for c in self.colors.split(",") if c.strip()] if self.colors else []
    def get_features(self):
        lines = [f.strip() for f in self.description.splitlines() if f.strip() and len(f.strip()) > 5]
        if lines: return lines[:8]
        for sep in ['•', '–', '-', '*']:
            if sep in self.description:
                items = [f.strip() for f in self.description.split(sep) if f.strip()]
                if items: return items[:8]
        sentences = [s.strip() + '.' for s in self.description.split('.') if s.strip()]
        return [s for s in sentences if len(s) > 10][:5]
    
    def __str__(self): return self.name
    
    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['slug']), models.Index(fields=['seller', 'is_active'])]

# ==================== REVIEWS ====================

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True, max_length=500)
    is_approved = models.BooleanField(default=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'product'] 
    
    def __str__(self): return f"{self.user.username} → {self.product.name} ({self.rating}★)"

# ==================== CART (Supabase-backed placeholders) ====================

# store/models.py

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self): return f"Cart for {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['cart', 'product']  
    
    def __str__(self): return f"{self.quantity}x {self.product.name}"

# ==================== ORDERS & TRACKING ====================

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    reference = models.CharField(max_length=100, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    paystack_response = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default='pending', 
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('shipped', 'Shipped'),
            ('in_transit', 'In Transit'),          # ✅ Added
            ('out_for_delivery', 'Out for Delivery'), # ✅ Added
            ('delivered', 'Delivered'),
            ('cancelled', 'Cancelled'),
        ])
    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"
    
    class Meta:
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
    

# ==================== SIGNALS FOR SUPABASE SYNC & CLEANUP ====================

def _sync_to_supabase_prof(user_id, data):
    """Safe helper to sync profile data to Supabase 'prof' table"""
    if not getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', None): return
    try:
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        data["id"] = str(user_id)
        supabase.table("prof").upsert(data).execute()
    except: pass

@receiver(post_save, sender=UserProfile)
def sync_user_profile(sender, instance, created, **kwargs):
    """Sync UserProfile changes to Supabase (auth.users or custom table)"""
    # ✅ FIX: avatar is already a string URL, no .url needed
    avatar_url = instance.avatar if instance.avatar else None
    
    _sync_to_supabase_prof(instance.user.id, {
        "username": instance.user.username, 
        "email": instance.user.email,
        "whatsapp_number": instance.whatsapp_number, 
        "bio": instance.bio,
        "avatar_url": avatar_url,  # ✅ Pass string directly
        "updated_at": timezone.now().isoformat()
    })

@receiver(post_save, sender=SellerProfile)
def sync_seller_profile(sender, instance, created, **kwargs):
    _sync_to_supabase_prof(instance.user.id, {
        "is_seller": True, "store_name": instance.store_name,
        "seller_description": instance.description, "seller_phone": instance.phone,
        "seller_address": instance.address, "is_verified": instance.is_verified, "updated_at": timezone.now().isoformat()
    })

@receiver(post_delete, sender=Product)
def delete_product_image_from_supabase(sender, instance, **kwargs):
    if instance.supabase_image_path:
        try:
            from supabase import create_client
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            supabase.storage.from_("product-uploads").remove([instance.supabase_image_path])
        except: pass

@receiver(post_delete, sender=User)
def delete_user_from_supabase(sender, instance, **kwargs):
    """Automatically delete Supabase Auth user when Django User is deleted"""
    if not getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', None):
        return  # Skip if service key not configured
    
    try:
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        
        # Find & delete user by email (most reliable identifier)
        response = supabase.auth.admin.list_users()
        for auth_user in response.users:
            if auth_user.email == instance.email:
                supabase.auth.admin.delete_user(auth_user.id)
                break
    except Exception as e:
        print(f"⚠️ Failed to delete {instance.username} from Supabase: {e}")


class Region(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="regions")
    name = models.CharField(max_length=100, help_text="State/Province/Region name")
    code = models.CharField(max_length=10, blank=True, help_text="Short code (e.g., GA for Greater Accra)")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.country.name} - {self.name}"
    
    class Meta:
        unique_together = ['country', 'name']
        ordering = ['country', 'name']

class PageView(models.Model):
    """Track page views for analytics"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    path = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=40, blank=True)
    
    class Meta:
        indexes = [models.Index(fields=['-timestamp'])]

class AnalyticsCache(models.Model):
    """Cache heavy analytics queries for performance"""
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [models.Index(fields=['-updated_at'])]