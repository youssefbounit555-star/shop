from django.db.models.signals import post_save
from django.dispatch import receiver
from store.models import Order
from .models import ClickEvent

@receiver(post_save, sender=Order)
def track_order_creation(sender, instance, created, **kwargs):
    if created:
        for item in instance.items.select_related('product').all():
            ClickEvent.objects.create(
                event_type='purchase',
                product=item.product,
                user=instance.user,
                session_key=None,  # Not available here, but user is more important
                details={
                    'order_id': instance.order_id,
                    'quantity': item.quantity,
                    'price': float(item.price),
                    'status': instance.status,
                    'payment_status': instance.payment_status,
                }
            )
