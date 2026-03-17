import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from store.models import Product
from .utils import (
    LIVE_WINDOW_MINUTES,
    get_live_counts,
    is_valid_event_type,
    prune_live_views,
    record_event,
    touch_live_view,
)


def _is_superuser(user) -> bool:
    return user.is_authenticated and user.is_superuser

@csrf_exempt
@require_POST
def track_event(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    event_type = (data.get('event_type') or '').strip().lower()
    if not event_type:
        return JsonResponse({'status': 'error', 'message': 'event_type is required'}, status=400)
    if not is_valid_event_type(event_type):
        return JsonResponse({'status': 'error', 'message': 'Invalid event_type'}, status=400)

    product_id = data.get('product_id')
    details = data.get('details', {})

    product = None
    if product_id:
        product = Product.objects.filter(id=product_id).first()

    record_event(
        request,
        event_type,
        product=product,
        details=details,
    )

    return JsonResponse({'status': 'success'})


@csrf_exempt
@require_POST
def track_live(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    product_id = data.get('product_id')
    if not product_id:
        return JsonResponse({'status': 'error', 'message': 'product_id is required'}, status=400)

    product = Product.objects.filter(id=product_id).first()
    if not product:
        return JsonResponse({'status': 'error', 'message': 'Invalid product_id'}, status=400)

    touch_live_view(request, product)
    return JsonResponse({'status': 'success'})


@login_required
@user_passes_test(_is_superuser)
@require_GET
def live_counts(request):
    window_minutes = LIVE_WINDOW_MINUTES
    try:
        window_minutes = int(request.GET.get('window', LIVE_WINDOW_MINUTES))
    except (TypeError, ValueError):
        window_minutes = LIVE_WINDOW_MINUTES

    cutoff = timezone.now() - timedelta(minutes=window_minutes)
    prune_live_views()

    product_id = request.GET.get('product_id')
    product_ids = None
    if product_id:
        try:
            product_ids = [int(product_id)]
        except (TypeError, ValueError):
            product_ids = None

    counts = get_live_counts(product_ids, window_minutes=window_minutes)
    return JsonResponse({
        'status': 'success',
        'window_minutes': window_minutes,
        'cutoff': cutoff.isoformat(),
        'counts': counts,
    })
