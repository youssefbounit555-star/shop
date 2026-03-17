from django.db import models
from django.contrib.auth.models import User
from store.models import Product

class ClickEvent(models.Model):
    EVENT_TYPES = [
        ('page_view', 'Page View'),
        ('product_view', 'Product View'),
        ('add_to_cart', 'Add to Cart'),
        ('wishlist_add', 'Wishlist Add'),
        ('category_view', 'Category View'),
        ('search', 'Search'),
        ('purchase', 'Purchase'),
    ]

    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"

class Insight(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class ProductLiveView(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='live_views')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=40, db_index=True)
    last_seen = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('product', 'session_key')

    def __str__(self):
        return f"Live view for {self.product_id} ({self.session_key})"
