from django.contrib import admin
from .models import Product, Order, OrderItem, SiteSettings, ProductImage


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin interface for Product model.
    """
    list_display = (
        'name', 'category', 'price', 'payment_mode',
        'is_digital', 'stock_quantity', 'featured', 'is_active', 'created_at'
    )
    list_filter = ('category', 'payment_mode', 'is_digital', 'featured', 'is_active', 'created_at')
    search_fields = ('name', 'sku', 'brand')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'slug', 'category', 'brand', 'description', 'short_description')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'discount_price', 'discount_note', 'stock_quantity', 'sku')
        }),
        ('Payment', {
            'fields': ('payment_mode', 'accepts_stripe', 'accepts_paypal')
        }),
        ('Media', {
            'fields': ('main_image', 'product_video', 'gallery_images')
        }),
        ('Classification', {
            'fields': ('tags', 'weight', 'featured', 'featured_order', 'is_active', 'is_digital', 'status')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Admin interface for Order model.
    """
    list_display = ('order_id', 'full_name', 'total_price', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at', 'payment_method')
    search_fields = ('order_id', 'full_name', 'email', 'phone')
    readonly_fields = ('order_id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'user', 'status', 'payment_status')
        }),
        ('Customer Information', {
            'fields': ('full_name', 'email', 'phone', 'customer_notes')
        }),
        ('Shipping Address', {
            'fields': ('address', 'city', 'country', 'postal_code', 'shipping_latitude', 'shipping_longitude')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'transaction_id', 'total_price', 'subtotal', 'tax_amount', 'shipping_cost', 'discount_amount')
        }),
        ('Internal Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'shipped_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Admin interface for OrderItem model.
    """
    list_display = ('get_product_name', 'quantity', 'price', 'subtotal', 'get_order')
    list_filter = ('order__created_at',)
    search_fields = ('product__name', 'order__order_id')
    readonly_fields = ('subtotal',)

    def get_product_name(self, obj):
        return obj.product.name if obj.product else 'Deleted Product'
    get_product_name.short_description = 'Product'
    
    def get_order(self, obj):
        return obj.order.order_id
    get_order.short_description = 'Order'


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for SiteSettings model.
    """
    fieldsets = (
        ('Site Identity', {
            'fields': ('site_name', 'site_description', 'logo', 'favicon')
        }),
        ('Contact Information', {
            'fields': ('support_email', 'support_phone', 'whatsapp_number')
        }),
        ('Business Settings', {
            'fields': ('currency', 'tax_rate', 'shipping_cost', 'free_shipping_threshold')
        }),
        ('Address', {
            'fields': ('address', 'city', 'country')
        }),
        ('Homepage', {
            'fields': ('homepage_banner', 'homepage_title', 'homepage_subtitle')
        }),
        ('Social Links', {
            'fields': ('social_links',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Maintenance', {
            'fields': ('maintenance_mode', 'maintenance_message'),
            'classes': ('collapse',)
        }),
    )

