from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from datetime import timedelta


# ==================== PRODUCT MANAGEMENT ====================

class Product(models.Model):
    """
    Comprehensive Product model with advanced e-commerce features.
    """
    PAYMENT_MODE_CHOICES = [
        ('cash_on_delivery', 'Cash on Delivery (COD)'),
        ('online', 'Pay Online'),
    ]

    CATEGORY_CHOICES = [
        ("Women's clothing", "Women's clothing"),
        ("Watch", "Watch"),
        ("Men's clothing", "Men's clothing"),
        ("Kids' clothing", "Kids' clothing"),
        ("Accessories", "Accessories"),
        ("Footwear", "Footwear"),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('draft', 'Draft'),
        ('archived', 'Archived'),
    ]

    # Basic Information
    name = models.CharField(max_length=255, unique=True, db_index=True)
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    description = models.TextField(blank=True, help_text="Rich HTML description")
    short_description = models.CharField(max_length=500, blank=True)
    
    # Pricing & Stock
    price = models.DecimalField(
        max_digits=10, decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Leave blank if no discount"
    )
    discount_note = models.CharField(
        max_length=140,
        blank=True,
        help_text="Short promotional text shown below discounted products."
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=100, unique=True, blank=True)
    
    # Classification
    category = models.CharField(
        max_length=50, 
        choices=CATEGORY_CHOICES,
        db_index=True
    )
    brand = models.CharField(max_length=100, blank=True, db_index=True)
    tags = models.CharField(
        max_length=300, 
        blank=True,
        help_text="Comma-separated tags for filtering"
    )
    
    # Attributes
    weight = models.DecimalField(
        max_digits=8, decimal_places=3, 
        null=True, blank=True,
        help_text="Weight in kg"
    )
    featured = models.BooleanField(default=False, db_index=True)
    featured_order = models.PositiveIntegerField(default=0, help_text="Lower number = higher priority")
    is_active = models.BooleanField(default=True, db_index=True)
    is_digital = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Digital products do not require shipping details from customers."
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODE_CHOICES,
        default='cash_on_delivery',
        db_index=True,
        help_text="Choose whether this product is paid on delivery or online."
    )
    accepts_stripe = models.BooleanField(default=False)
    accepts_paypal = models.BooleanField(default=False)
    
    # Images
    main_image = models.ImageField(upload_to='products/main/', blank=True)
    product_video = models.FileField(upload_to='products/videos/', blank=True)
    gallery_images = models.JSONField(default=list, blank=True, help_text="Store image URLs as JSON")
    
    # SEO
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['featured', '-featured_order']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.payment_mode == 'cash_on_delivery':
            self.accepts_stripe = False
            self.accepts_paypal = False
        super().save(*args, **kwargs)

    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.price and self.price > 0 and self.discount_price is not None:
            discount = ((self.price - self.discount_price) / self.price) * 100
            return round(discount, 1)
        return 0

    @property
    def current_price(self):
        """Get current price (considering discount)"""
        return self.discount_price if self.discount_price is not None else self.price

    @property
    def in_stock(self):
        """Check if product is in stock"""
        return self.stock_quantity > 0

    @property
    def low_stock(self):
        """Check if product is low in stock (less than 10)"""
        return self.stock_quantity < 10 and self.stock_quantity > 0

    @property
    def allowed_payment_methods(self):
        if self.payment_mode == 'cash_on_delivery':
            return [('cash_on_delivery', 'Cash on Delivery (COD)')]

        methods = []
        if self.accepts_stripe:
            methods.append(('stripe', 'Stripe'))
        if self.accepts_paypal:
            methods.append(('paypal', 'PayPal'))
        return methods

    @property
    def payment_methods_display(self):
        return ', '.join(label for _, label in self.allowed_payment_methods) or 'Not configured'

    @property
    def requires_online_payment(self):
        return self.payment_mode == 'online'


class ProductImage(models.Model):
    """
    Additional images for products (gallery)
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.product.name}"


# ==================== ORDER MANAGEMENT ====================

class Order(models.Model):
    """
    Comprehensive Order model with full e-commerce details.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending - Awaiting Processing'),
        ('processing', 'Processing - Preparing to Ship'),
        ('shipped', 'Shipped - In Transit'),
        ('completed', 'Completed - Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('stripe', 'Stripe'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('other', 'Other'),
    ]

    # Order Identification
    order_id = models.CharField(max_length=50, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='admin_orders')
    
    # Customer Information
    full_name = models.CharField(max_length=255, default='')
    email = models.EmailField(default='')
    phone = models.CharField(max_length=20, default='')
    
    # Shipping Information
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    country = models.CharField(max_length=100, blank=True, default='')
    postal_code = models.CharField(max_length=20, blank=True, default='')
    shipping_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    shipping_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Order Details
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Status & Payment
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        db_index=True
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(
        max_length=20, 
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='pending'
    )
    transaction_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    
    # Notes & Metadata
    notes = models.TextField(blank=True, help_text="Internal notes for staff")
    customer_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f"Order {self.order_id}"

    def save(self, *args, **kwargs):
        if not self.order_id:
            from datetime import datetime
            self.order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self.id or 0}"
        super().save(*args, **kwargs)

    @property
    def item_count(self):
        """Total number of items in order"""
        return sum(item.quantity for item in self.items.all())

    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def is_shipped(self):
        return self.status == 'shipped'


class OrderItem(models.Model):
    """
    Individual items in an order (line items).
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of order
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.product.name if self.product else 'Unknown'} x {self.quantity}"

    def save(self, *args, **kwargs):
        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)


# ==================== SITE SETTINGS ====================

class SiteSettings(models.Model):
    """
    Global site configuration and settings.
    """
    # Site Identity
    site_name = models.CharField(max_length=255, default='ElegantShop')
    site_description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='settings/', blank=True)
    favicon = models.ImageField(upload_to='settings/', blank=True)
    
    # Contact Information
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=20, blank=True)
    whatsapp_number = models.CharField(
        max_length=20, 
        blank=True,
        help_text="WhatsApp number with country code (e.g., +1234567890)"
    )
    
    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Business Settings
    currency = models.CharField(max_length=10, default='MAD')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Tax percentage")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Maintenance
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    
    # Homepage
    homepage_banner = models.ImageField(upload_to='settings/banners/', blank=True)
    homepage_title = models.CharField(max_length=255, blank=True)
    homepage_subtitle = models.CharField(max_length=500, blank=True)
    
    # Social Links (JSON format)
    social_links = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"facebook": "url", "instagram": "url", ...}'
    )
    
    # SEO
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return self.site_name

    @classmethod
    def get_settings(cls):
        """Get or create site settings"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

