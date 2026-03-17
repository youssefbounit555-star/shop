from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Count
from django.utils import timezone

from .models import ClickEvent, ProductLiveView


ALLOWED_EVENT_TYPES = {choice[0] for choice in ClickEvent.EVENT_TYPES}
LIVE_WINDOW_MINUTES = 5
LIVE_RETENTION_HOURS = 24


def is_valid_event_type(event_type: str) -> bool:
    return event_type in ALLOWED_EVENT_TYPES


def _ensure_session_key(request) -> str | None:
    if request is None:
        return None
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _normalize_details(details: Any) -> dict:
    if isinstance(details, dict):
        return details
    return {}


def record_event(
    request,
    event_type: str,
    *,
    product=None,
    user=None,
    details: dict | None = None,
) -> ClickEvent | None:
    if not is_valid_event_type(event_type):
        return None

    payload = _normalize_details(details)
    session_key = _ensure_session_key(request)

    if request is not None:
        payload.setdefault('path', getattr(request, 'path', '') or '')
        payload.setdefault('referrer', request.META.get('HTTP_REFERER', ''))
        payload.setdefault('user_agent', request.META.get('HTTP_USER_AGENT', ''))

        if user is None and getattr(request, 'user', None) and request.user.is_authenticated:
            user = request.user

    return ClickEvent.objects.create(
        event_type=event_type,
        product=product,
        user=user,
        session_key=session_key,
        details=payload,
    )


def touch_live_view(request, product) -> ProductLiveView | None:
    if request is None or product is None:
        return None

    session_key = _ensure_session_key(request)
    if not session_key:
        return None

    user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

    live_view, _ = ProductLiveView.objects.update_or_create(
        product=product,
        session_key=session_key,
        defaults={
            'user': user,
            'last_seen': timezone.now(),
        },
    )
    return live_view


def prune_live_views(retention_hours: int = LIVE_RETENTION_HOURS) -> int:
    cutoff = timezone.now() - timedelta(hours=retention_hours)
    deleted, _ = ProductLiveView.objects.filter(last_seen__lt=cutoff).delete()
    return deleted


def get_live_counts(
    product_ids: list[int] | None = None,
    *,
    window_minutes: int = LIVE_WINDOW_MINUTES,
) -> dict[int, int]:
    cutoff = timezone.now() - timedelta(minutes=window_minutes)
    queryset = ProductLiveView.objects.filter(last_seen__gte=cutoff)
    if product_ids:
        queryset = queryset.filter(product_id__in=product_ids)

    counts = queryset.values('product').annotate(count=Count('id'))
    return {row['product']: row['count'] for row in counts}
