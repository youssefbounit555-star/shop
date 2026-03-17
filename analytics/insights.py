from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from analytics.models import ClickEvent, Insight
from store.models import OrderItem, Product


ARCHIVE_AFTER_DAYS = 30
DEDUP_HOURS = 12


def _archive_old_insights() -> None:
    cutoff = timezone.now() - timedelta(days=ARCHIVE_AFTER_DAYS)
    Insight.objects.filter(is_archived=False, generated_at__lt=cutoff).update(is_archived=True)


def _create_insight(title: str, content: str) -> bool:
    recent_cutoff = timezone.now() - timedelta(hours=DEDUP_HOURS)
    if Insight.objects.filter(title=title, content=content, generated_at__gte=recent_cutoff).exists():
        return False
    Insight.objects.create(title=title, content=content)
    return True


def _top_viewed_product(since) -> bool:
    result = (
        ClickEvent.objects.filter(
            event_type='product_view',
            timestamp__gte=since,
            product__isnull=False,
        )
        .values('product')
        .annotate(views=Count('id'))
        .order_by('-views')
        .first()
    )
    if not result:
        return False

    product = Product.objects.filter(pk=result['product']).first()
    if not product:
        return False

    title = 'Most viewed product'
    content = (
        f'"{product.name}" got the highest attention with {result["views"]} product views '
        'in the selected period.'
    )
    return _create_insight(title, content)


def _top_selling_product(since) -> bool:
    result = (
        OrderItem.objects.filter(order__created_at__gte=since)
        .exclude(order__status__in=['cancelled', 'refunded'])
        .values('product')
        .annotate(units=Sum('quantity'))
        .order_by('-units')
        .first()
    )
    if not result:
        return False

    product = Product.objects.filter(pk=result['product']).first()
    if not product:
        return False

    title = 'Top selling product'
    content = (
        f'"{product.name}" is the top seller with {result["units"]} units sold in the selected period.'
    )
    return _create_insight(title, content)


def _top_category_interest(since) -> bool:
    result = (
        ClickEvent.objects.filter(
            event_type='product_view',
            timestamp__gte=since,
            product__isnull=False,
        )
        .values('product__category')
        .annotate(views=Count('id'))
        .order_by('-views')
        .first()
    )
    if not result or not result.get('product__category'):
        return False

    category_value = result['product__category']
    category_label = dict(Product.CATEGORY_CHOICES).get(category_value, category_value)
    title = 'Most interesting category'
    content = (
        f'Customers are showing the most interest in the "{category_label}" category '
        f'({result["views"]} product views).'
    )
    return _create_insight(title, content)


def _cart_dropoff_insight(since) -> bool:
    add_counts = (
        ClickEvent.objects.filter(
            event_type='add_to_cart',
            timestamp__gte=since,
            product__isnull=False,
        )
        .values('product')
        .annotate(adds=Count('id'))
    )

    if not add_counts:
        return False

    purchase_counts = (
        OrderItem.objects.filter(order__created_at__gte=since)
        .exclude(order__status__in=['cancelled', 'refunded'])
        .values('product')
        .annotate(units=Sum('quantity'))
    )
    purchase_map = {row['product']: row['units'] or 0 for row in purchase_counts}

    candidate = None
    for row in add_counts:
        adds = row['adds'] or 0
        if adds < 5:
            continue
        purchases = purchase_map.get(row['product'], 0)
        conversion = purchases / adds if adds else 0
        if conversion >= 0.25:
            continue
        if candidate is None or adds > candidate['adds']:
            candidate = {
                'product_id': row['product'],
                'adds': adds,
                'purchases': purchases,
            }

    if not candidate:
        return False

    product = Product.objects.filter(pk=candidate['product_id']).first()
    if not product:
        return False

    title = 'High interest, low conversion'
    content = (
        f'"{product.name}" is frequently added to carts ({candidate["adds"]} adds) but has '
        f'low purchases ({candidate["purchases"]} units). Consider improving pricing, '
        'photos, or the description.'
    )
    return _create_insight(title, content)


def _top_search_term(since) -> bool:
    events = ClickEvent.objects.filter(
        event_type='search',
        timestamp__gte=since,
    ).values_list('details', flat=True)

    term_counts = Counter()
    for details in events:
        if isinstance(details, dict):
            term = str(details.get('query', '')).strip().lower()
            if term:
                term_counts[term] += 1

    if not term_counts:
        return False

    term, count = term_counts.most_common(1)[0]
    title = 'Most searched term'
    content = (
        f'The most searched term is "{term}" ({count} searches). Consider featuring products '
        'related to this interest.'
    )
    return _create_insight(title, content)


def generate_insights(days: int = 7) -> int:
    _archive_old_insights()
    since = timezone.now() - timedelta(days=days)

    created = 0
    for fn in (
        _top_viewed_product,
        _top_category_interest,
        _top_selling_product,
        _cart_dropoff_insight,
        _top_search_term,
    ):
        if fn(since):
            created += 1

    return created


def ensure_recent_insights(days: int = 7, max_age_hours: int = 24) -> int:
    latest = Insight.objects.order_by('-generated_at').first()
    if not latest:
        return generate_insights(days=days)

    if latest.generated_at < timezone.now() - timedelta(hours=max_age_hours):
        return generate_insights(days=days)

    return 0
