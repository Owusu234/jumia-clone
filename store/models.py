# store/models.py
import uuid
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


class UserNotification(models.Model):
    """Private notifications shown to the relevant buyer/seller."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='store_notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, default='#')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'is_read', '-created_at'])]

    def __str__(self):
        return f"{self.user.username}: {self.title}"

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

    # ── Size (wearable) / Dimensions (non-wearable) ──
    is_wearable = models.BooleanField(
        default=False,
        help_text="Check if this product is wearable (e.g., shirt, shoe) so buyers can pick a size"
    )
    available_sizes = models.CharField(
        max_length=200, blank=True,
        help_text="Comma-separated sizes for wearable items, e.g. S, M, L, XL or 39, 40, 41"
    )
    length = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True,
        help_text="Length in cm (for non-wearable items, e.g. a box)"
    )
    width = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True,
        help_text="Width in cm (for non-wearable items, e.g. a box)"
    )
    height = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True,
        help_text="Height in cm (for non-wearable items, e.g. a box)"
    )

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
    def size_list(self):
        """Available sizes as a clean list, e.g. ['S', 'M', 'L']."""
        if not self.available_sizes:
            return []
        return [s.strip() for s in self.available_sizes.split(",") if s.strip()]

    @property
    def dimensions_display(self):
        """Human-readable 'L x W x H cm' string, or '' if incomplete."""
        if self.length and self.width and self.height:
            return f"{self.length} x {self.width} x {self.height} cm"
        return ""

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
    image = models.ImageField(upload_to="reviews/", blank=True, null=True, help_text="Optional buyer photo. Stored at passport-photo dimensions (350×450 px).")
    # Public URL of the processed buyer photo stored in the Supabase Storage "review" bucket.
    review_image_url = models.URLField(blank=True, null=True, max_length=1000)
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
    color = models.CharField(max_length=50, blank=True, default='')
    size = models.CharField(max_length=50, blank=True, default='')
    # Who most recently added/updated this item — used to show "added by" in a
    # shared cart, never who bought it (purchases stay private).
    added_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="added_cart_items")
    added_at = models.DateTimeField(auto_now_add=True)
    # Opt-in visibility: a cart item is private by default and only appears in
    # the owner's shared cart (link view and linked-account view) once the
    # owner explicitly marks it as shared.
    is_shared = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['cart', 'product', 'color', 'size']
    
    def __str__(self): return f"{self.quantity}x {self.product.name}"


class SharedCartLink(models.Model):
    """A simple shareable link to a user's cart. Anyone with the link can
    see what's in the owner's cart (great for surprise gifts) — but never
    who purchased what: bought items simply disappear from the shared view."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shared_cart_links")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Shared cart link for {self.owner.username}"


class CartInvite(models.Model):
    """A live, bi-directional link between two accounts' carts — 'Linked
    Shared Carts'. Once accepted, both sides can see and add to each
    other's shared cart. Started as a pending invite carrying a
    relational tag (spouse, parent, friend, etc.) chosen by the sender."""
    RELATION_CHOICES = [
        ('spouse', 'Spouse'),
        ('parent', 'Parent'),
        ('business_partner', 'Business Partner'),
        ('friend', 'Friend'),
        ('sibling', 'Sibling'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_cart_invites')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_cart_invites', null=True, blank=True)
    invited_email = models.EmailField(blank=True, default='')
    relation = models.CharField(max_length=20, choices=RELATION_CHOICES, default='other')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def other_party(self, user):
        return self.invitee if user == self.inviter else self.inviter

    def get_relation_display_for(self, user):
        """The relation is defined from the inviter's point of view."""
        return self.get_relation_display()

    def __str__(self):
        who = self.invitee.username if self.invitee else self.invited_email
        return f"{self.inviter.username} → {who} ({self.get_status_display()})"


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
    # The account that actually paid for this order. For normal orders this is
    # the same as `user`; for a shared-cart gift it is the person paying.
    paid_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='paid_orders'
    )
    # Email of the anonymous/guest payer, when the order was paid for by
    # someone without an account (a guest shared-cart "gift" purchase).
    # Always blank for normal orders and for logged-in payers.
    guest_email = models.EmailField(blank=True, null=True)
    # Delivery/shipping charged on this order. Non-zero only for orders paid
    # against a seller invoice, where the fee comes from the buyer's shared
    # location. `total_amount` already includes it.
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
    color = models.CharField(max_length=50, blank=True, default='')
    size = models.CharField(max_length=50, blank=True, default='')
    
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

# ==================== COMMUNITY HIGHLIGHTS & ENGAGEMENT REWARDS ====================
#
# Proof-of-purchase social feed. A buyer who has a *paid + delivered* order can
# post an unboxing highlight for an item in it. Other shoppers engage with the
# post and every interaction earns the post points:
#
#       Like     +1        Comment  +2        Share  +3
#
# The seller sets a points goal (e.g. 15 pts) and a discount percentage on
# their store. When a highlight reaches that goal, a unique discount voucher
# is minted automatically and deposited into the buyer's wallet.
#
# Anti-gaming rules, enforced in HighlightEngagement.award():
#   • the author's own interactions never earn points
#   • one like per user per highlight (un-liking removes the point)
#   • one share point per user per highlight, however many times they share
#   • only a user's FIRST comment on a highlight earns points
# --------------------------------------------------------------------------

import secrets
import string
from decimal import Decimal
from datetime import timedelta


class SellerHighlightGoal(models.Model):
    """The engagement target a seller sets for unboxing highlights of their
    products, plus the reward a buyer unlocks by reaching it."""

    seller = models.OneToOneField(
        SellerProfile, on_delete=models.CASCADE, related_name="highlight_goal"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to pause rewards. Buyers can still post highlights."
    )
    points_goal = models.PositiveIntegerField(
        default=15,
        help_text="Engagement points a highlight must reach to unlock the reward (e.g. 15)."
    )
    discount_percent = models.PositiveSmallIntegerField(
        default=10,
        help_text="Percentage off the buyer receives as a voucher, 1–90."
    )
    voucher_validity_days = models.PositiveSmallIntegerField(
        default=30, help_text="How many days the unlocked voucher stays valid."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Seller Highlight Goal"
        verbose_name_plural = "Seller Highlight Goals"

    def __str__(self):
        return f"{self.seller.store_name}: {self.points_goal} pts → {self.discount_percent}% off"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.points_goal < 1:
            raise ValidationError({"points_goal": "The goal must be at least 1 point."})
        if not 1 <= self.discount_percent <= 90:
            raise ValidationError({"discount_percent": "Discount must be between 1% and 90%."})

    @classmethod
    def for_seller(cls, seller):
        """Always return a goal for a seller, creating the default if needed."""
        if seller is None:
            return None
        goal, _ = cls.objects.get_or_create(seller=seller)
        return goal


class CommunityHighlight(models.Model):
    """A buyer's unboxing post, permanently tied to a real delivered order."""

    MEDIA_IMAGE = "image"
    MEDIA_VIDEO = "video"
    MEDIA_CHOICES = [(MEDIA_IMAGE, "Photo"), (MEDIA_VIDEO, "Video")]

    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="community_highlights"
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="highlights"
    )
    order_item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE, related_name="highlights"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="highlights"
    )
    seller = models.ForeignKey(
        SellerProfile, on_delete=models.CASCADE, related_name="highlights",
        null=True, blank=True
    )

    title = models.CharField(max_length=160)
    body = models.TextField(max_length=2000, help_text="How was the unboxing?")
    media_url = models.URLField(max_length=1000, blank=True, default="")
    media_type = models.CharField(
        max_length=10, choices=MEDIA_CHOICES, default=MEDIA_IMAGE
    )
    media_storage_path = models.CharField(max_length=500, blank=True, default="")

    # Snapshot of the seller's goal at posting time, so a seller changing
    # their target later never moves the goalposts on a live highlight.
    points_goal = models.PositiveIntegerField(default=15)
    discount_percent = models.PositiveSmallIntegerField(default=10)

    total_points = models.PositiveIntegerField(default=0, db_index=True)
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)

    reward_unlocked = models.BooleanField(default=False, db_index=True)
    unlocked_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(
        default=True, help_text="Uncheck to hide from the public feed."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Community Highlight"
        constraints = [
            models.UniqueConstraint(
                fields=["buyer", "order_item"], name="uniq_highlight_per_order_item"
            )
        ]
        indexes = [
            models.Index(fields=["-created_at"], name="store_ch_created_idx"),
            models.Index(fields=["-total_points"], name="store_ch_points_idx"),
            models.Index(fields=["seller", "-created_at"], name="store_ch_seller_idx"),
        ]

    def __str__(self):
        return f"{self.buyer.username} → {self.product.name} ({self.total_points} pts)"

    # ── eligibility ───────────────────────────────────────────────────────
    @staticmethod
    def eligible_order_items(user):
        """OrderItems this user may still post about: paid, delivered, theirs,
        and not already used for a highlight."""
        return (
            OrderItem.objects
            .filter(
                order__user=user,
                order__payment_status="paid",
                order__status="delivered",
            )
            .exclude(highlights__buyer=user)
            .select_related("order", "product", "product__seller")
            .order_by("-order__created_at")
        )

    # ── progress helpers used by the templates ────────────────────────────
    @property
    def progress_percent(self):
        if not self.points_goal:
            return 100
        return min(100, int(round(self.total_points * 100 / self.points_goal)))

    @property
    def points_remaining(self):
        return max(0, self.points_goal - self.total_points)

    @property
    def is_video(self):
        return self.media_type == self.MEDIA_VIDEO

    def get_media_url(self):
        return self.media_url or (self.product.get_image() if self.product_id else "")

    # ── scoring ───────────────────────────────────────────────────────────
    def recalculate(self, commit=True):
        """Recount points and per-action tallies from the engagement rows."""
        rows = self.engagements.all()
        self.like_count = rows.filter(action=HighlightEngagement.LIKE).count()
        self.share_count = rows.filter(action=HighlightEngagement.SHARE).count()
        self.comment_count = self.comments.count()
        self.total_points = rows.aggregate(t=models.Sum("points"))["t"] or 0
        if commit:
            self.save(update_fields=[
                "like_count", "share_count", "comment_count",
                "total_points", "updated_at",
            ])
        return self.total_points

    def maybe_unlock_reward(self):
        """Mint the buyer's voucher the moment the goal is met. Returns the
        voucher if one was created on this call, else None."""
        if self.reward_unlocked or self.total_points < self.points_goal:
            return None
        goal = SellerHighlightGoal.for_seller(self.seller) if self.seller else None
        if goal and not goal.is_active:
            return None

        validity = goal.voucher_validity_days if goal else 30
        voucher = DiscountVoucher.objects.create(
            code=DiscountVoucher.generate_code(),
            buyer=self.buyer,
            seller=self.seller,
            highlight=self,
            discount_percent=self.discount_percent,
            expires_at=timezone.now() + timedelta(days=validity),
        )
        self.reward_unlocked = True
        self.unlocked_at = timezone.now()
        self.save(update_fields=["reward_unlocked", "unlocked_at", "updated_at"])
        return voucher


class HighlightEngagement(models.Model):
    """One scoring row per user per point-earning action on a highlight."""

    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    ACTION_CHOICES = [(LIKE, "Like"), (COMMENT, "Comment"), (SHARE, "Share")]

    # The published points table. Change here, changes everywhere.
    POINT_VALUES = {LIKE: 1, COMMENT: 2, SHARE: 3}

    highlight = models.ForeignKey(
        CommunityHighlight, on_delete=models.CASCADE, related_name="engagements"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="highlight_engagements"
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    points = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["highlight", "user", "action"],
                name="uniq_engagement_per_user_action",
            )
        ]
        indexes = [models.Index(fields=["highlight", "action"], name="store_he_hl_action_idx")]

    def __str__(self):
        return f"{self.user.username} {self.action} (+{self.points})"

    def save(self, *args, **kwargs):
        if not self.points:
            self.points = self.POINT_VALUES.get(self.action, 0)
        super().save(*args, **kwargs)


class HighlightComment(models.Model):
    """A comment on a highlight. Scoring lives in HighlightEngagement — only
    a user's first comment earns the +2, but every comment is kept."""

    highlight = models.ForeignKey(
        CommunityHighlight, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="highlight_comments"
    )
    body = models.TextField(max_length=600)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["highlight", "created_at"], name="store_hc_hl_created_idx")]

    def __str__(self):
        return f"{self.user.username} on #{self.highlight_id}"


class DiscountVoucher(models.Model):
    """A unique, single-use discount code minted when a highlight hits its
    goal. Deposited straight into the buyer's wallet."""

    code = models.CharField(max_length=32, unique=True, db_index=True)
    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="discount_vouchers"
    )
    seller = models.ForeignKey(
        SellerProfile, on_delete=models.CASCADE, related_name="issued_vouchers",
        null=True, blank=True
    )
    highlight = models.OneToOneField(
        CommunityHighlight, on_delete=models.CASCADE, related_name="voucher",
        null=True, blank=True
    )
    discount_percent = models.PositiveSmallIntegerField(default=10)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    used_on_order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="applied_vouchers"
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Discount Voucher"
        indexes = [models.Index(fields=["buyer", "is_used"], name="store_dv_buyer_used_idx")]

    def __str__(self):
        return f"{self.code} ({self.discount_percent}% off)"

    @staticmethod
    def generate_code():
        """Codes look like SV-POP-GOLD-8492 — readable and easy to retype."""
        words = [
            "GOLD", "KENTE", "VIBE", "WAVE", "STAR", "BOLD", "GLOW",
            "SHINE", "PEAK", "ROYAL", "SPARK", "FRESH",
        ]
        alphabet = string.digits
        while True:
            word = secrets.choice(words)
            tail = "".join(secrets.choice(alphabet) for _ in range(4))
            code = f"SV-POP-{word}-{tail}"
            if not DiscountVoucher.objects.filter(code=code).exists():
                return code

    @property
    def is_expired(self):
        return bool(self.expires_at and timezone.now() > self.expires_at)

    @property
    def is_redeemable(self):
        return not self.is_used and not self.is_expired

    @property
    def status_label(self):
        if self.is_used:
            return "Used"
        if self.is_expired:
            return "Expired"
        return "Ready to use"

    def discount_for(self, amount):
        """Cedi value this voucher takes off a given subtotal."""
        if not self.is_redeemable:
            return Decimal("0.00")
        return (Decimal(str(amount)) * Decimal(self.discount_percent) / Decimal(100)).quantize(Decimal("0.01"))

    def mark_used(self, order=None):
        self.is_used = True
        self.used_at = timezone.now()
        self.used_on_order = order
        self.save(update_fields=["is_used", "used_at", "used_on_order"])


# ==================== IN-SITE BUYER ↔ SELLER CHAT ====================

class Conversation(models.Model):
    """A private thread between one buyer and the seller of one product.

    Only the two participants can read it. The buyer's shared location lives
    here (not on each message) because it is the buyer's current delivery
    point for this negotiation, and the seller uses it to quote a delivery
    fee."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="conversations")
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="buyer_conversations")
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name="conversations")

    # Buyer-entered delivery area. No browser GPS or coordinates are stored.
    buyer_region = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Region/state/province entered by the buyer"
    )
    buyer_town = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Town/city entered by the buyer"
    )
    location_shared_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'buyer']
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.buyer.username} ↔ {self.seller.store_name} · {self.product.name}"

    @property
    def has_location(self):
        return bool(self.buyer_region.strip() and self.buyer_town.strip())

    @property
    def location_label(self):
        if not self.has_location:
            return ''
        return f"{self.buyer_region}, {self.buyer_town}"

    def is_participant(self, user):
        return bool(user and user.is_authenticated and
                    user.id in (self.buyer_id, self.seller.user_id))

    def other_party(self, user):
        """The display name of the person on the other side."""
        if user.id == self.buyer_id:
            return self.seller.store_name
        return self.buyer.username

    def unread_count_for(self, user):
        return self.messages.filter(is_read=False).exclude(sender_id=user.id).count()

    @property
    def latest_invoice(self):
        return self.invoices.order_by('-created_at').first()


class ChatMessage(models.Model):
    TEXT = 'text'
    LOCATION = 'location'
    INVOICE = 'invoice'
    SYSTEM = 'system'
    KIND_CHOICES = [
        (TEXT, 'Text'),
        (LOCATION, 'Location'),
        (INVOICE, 'Invoice'),
        (SYSTEM, 'System'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    # Null sender = written by the system (e.g. "location shared").
    sender = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="chat_messages")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=TEXT)
    body = models.TextField(blank=True, default='')
    invoice = models.ForeignKey('Invoice', null=True, blank=True, on_delete=models.CASCADE, related_name="messages")
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        who = self.sender.username if self.sender else 'system'
        return f"{who}: {self.body[:40]}"


class Invoice(models.Model):
    """The seller's offer at the end of a negotiation: the agreed unit price
    plus the delivery fee worked out from the buyer's shared location. The
    product's listed price still shows on the storefront — this is what the
    buyer actually pays."""
    PENDING = 'pending'
    PAID = 'paid'
    CANCELLED = 'cancelled'
    DECLINED = 'declined'
    STATUS_CHOICES = [
        (PENDING, 'Awaiting payment'),
        (PAID, 'Paid'),
        (CANCELLED, 'Cancelled'),
        (DECLINED, 'Declined'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="invoices")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="invoices")
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invoices")
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name="invoices")

    quantity = models.PositiveIntegerField(default=1)
    color = models.CharField(max_length=50, blank=True, default='')
    size = models.CharField(max_length=50, blank=True, default='')
    # The negotiated price per unit — may be above or below Product.price.
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    note = models.TextField(blank=True, default='')

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    order = models.ForeignKey('Order', null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice #{self.id} · {self.product.name} · GH₵{self.total}"

    @property
    def items_total(self):
        return (Decimal(self.unit_price) * Decimal(self.quantity)).quantize(Decimal('0.01'))

    @property
    def total(self):
        return (self.items_total + Decimal(self.delivery_fee)).quantize(Decimal('0.01'))

    @property
    def is_payable(self):
        return self.status == self.PENDING and self.product.is_active

    def mark_paid(self, order=None):
        self.status = self.PAID
        self.paid_at = timezone.now()
        self.order = order
        self.save(update_fields=['status', 'paid_at', 'order'])


class SellerFollow(models.Model):
    """A buyer following a seller's store."""
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seller_follows')
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('buyer', 'seller')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.buyer.username} → {self.seller.store_name}'
