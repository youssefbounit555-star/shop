from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from django.utils.html import format_html
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode
import csv
import json
import logging
import re
import requests
try:
    import stripe
except ImportError:  # pragma: no cover - optional dependency at runtime
    stripe = None
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods, require_GET

from user.models import UserProfile
from dashboard.models import Message, Goal
from .models import Product, Order, OrderItem, SiteSettings, ProductImage
from .ai_agents import get_agent_catalog, generate_agent_reply
from .forms import (
    ProductForm, OrderForm, SiteSettingsForm, BulkProductActionForm,
    ProductFilterForm, OrderFilterForm, MessageReplyForm, CustomerOrderForm
)
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from admin_panel.views import AdminOnlyMixin
from .request_context import get_current_request
from analytics.utils import record_event


# ==================== FRONTEND VIEWS ====================
AGENT_SESSION_KEY = 'ai_agent_history_by_agent'
MAX_SESSION_HISTORY_ITEMS = 12
MAX_SESSION_MESSAGE_CHARS = 500
PAYPAL_API_BASE = {
    'sandbox': 'https://api-m.sandbox.paypal.com',
    'live': 'https://api-m.paypal.com',
}
ONLINE_PAYMENT_METHODS = {'stripe', 'paypal'}
SUPPORT_WHATSAPP_DISPLAY = '+212 667-853182'
SUPPORT_WHATSAPP_WA_LINK = 'https://wa.me/212667853182'
CART_SESSION_KEY = 'store_cart'
WISHLIST_SESSION_KEY = 'store_wishlist'
logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    pass


def _get_currency_codes():
    settings_obj = SiteSettings.get_settings()
    currency = (settings_obj.currency or 'USD').strip() or 'USD'
    request = get_current_request()
    if request and hasattr(request, "geo_profile"):
        geo_currency = getattr(request.geo_profile, "currency", None)
        if geo_currency:
            currency = str(geo_currency).strip() or currency
    return currency.lower(), currency.upper()


def _get_currency_label():
    request = get_current_request()
    if request and hasattr(request, "geo_profile"):
        currency_label = getattr(request.geo_profile, "currency_label", None)
        if currency_label:
            return str(currency_label)
    _, currency_upper = _get_currency_codes()
    return currency_upper


def _get_session_cart(request):
    raw_cart = request.session.get(CART_SESSION_KEY, {})
    if not isinstance(raw_cart, dict):
        raw_cart = {}

    cleaned_cart = {}
    for raw_product_id, raw_entry in raw_cart.items():
        try:
            product_id = int(raw_product_id)
        except (TypeError, ValueError):
            continue

        quantity = 1
        if isinstance(raw_entry, dict):
            quantity = raw_entry.get('quantity', 1)
        else:
            quantity = raw_entry

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 1

        cleaned_cart[str(product_id)] = {'quantity': max(1, quantity)}

    if cleaned_cart != raw_cart:
        request.session[CART_SESSION_KEY] = cleaned_cart
        request.session.modified = True
    return cleaned_cart


def _save_session_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def _cart_item_count(cart):
    return sum(int(item.get('quantity', 0) or 0) for item in cart.values())


def _add_product_to_cart(request, product, quantity):
    cart = _get_session_cart(request)
    product_key = str(product.pk)
    current_quantity = int(cart.get(product_key, {}).get('quantity', 0) or 0)
    max_quantity = max(product.stock_quantity, 1)
    next_quantity = min(current_quantity + max(1, quantity), max_quantity)
    cart[product_key] = {'quantity': next_quantity}
    _save_session_cart(request, cart)
    return next_quantity, max(next_quantity - current_quantity, 0)


def _get_session_wishlist(request):
    raw_wishlist = request.session.get(WISHLIST_SESSION_KEY, [])
    if not isinstance(raw_wishlist, list):
        raw_wishlist = []

    cleaned_wishlist = []
    seen = set()
    for raw_product_id in raw_wishlist:
        try:
            product_id = int(raw_product_id)
        except (TypeError, ValueError):
            continue
        if product_id in seen:
            continue
        seen.add(product_id)
        cleaned_wishlist.append(product_id)

    if cleaned_wishlist != raw_wishlist:
        request.session[WISHLIST_SESSION_KEY] = cleaned_wishlist
        request.session.modified = True
    return cleaned_wishlist


def _save_session_wishlist(request, wishlist):
    request.session[WISHLIST_SESSION_KEY] = wishlist
    request.session.modified = True


def _get_paypal_charge_details(amount):
    _, store_currency = _get_currency_codes()
    paypal_currency = (getattr(settings, 'PAYPAL_CURRENCY', '') or store_currency).upper()
    store_amount = Decimal(str(amount)).quantize(Decimal('0.01'))

    conversion_rate = Decimal(str(getattr(settings, 'PAYPAL_CONVERSION_RATE', '1')))
    paypal_amount = store_amount
    converted = False

    if paypal_currency != store_currency:
        if conversion_rate <= 0:
            raise PaymentGatewayError('PAYPAL_CONVERSION_RATE must be greater than 0.')
        paypal_amount = (store_amount * conversion_rate).quantize(Decimal('0.01'))
        converted = True

    return {
        'store_currency': store_currency,
        'store_amount': store_amount,
        'paypal_currency': paypal_currency,
        'paypal_amount': paypal_amount,
        'conversion_rate': conversion_rate,
        'converted': converted,
    }


def _create_online_order(user, product, quantity, payment_method, shipping_data=None):
    shipping_data = shipping_data or {}
    price = product.current_price
    line_subtotal = price * quantity
    order = Order.objects.create(
        user=user,
        full_name=user.get_full_name() or user.username,
        email=user.email or '',
        phone=shipping_data.get('phone', ''),
        address=shipping_data.get('address', ''),
        city=shipping_data.get('city', ''),
        country=shipping_data.get('country', ''),
        postal_code=shipping_data.get('postal_code', ''),
        shipping_latitude=shipping_data.get('shipping_latitude'),
        shipping_longitude=shipping_data.get('shipping_longitude'),
        total_price=line_subtotal,
        subtotal=line_subtotal,
        tax_amount=0,
        shipping_cost=0,
        discount_amount=0,
        payment_method=payment_method,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=quantity,
        price=price,
        subtotal=line_subtotal,
    )
    return order


def _create_stripe_checkout_session(request, order):
    if stripe is None:
        raise PaymentGatewayError('Stripe SDK is not installed on the server environment.')
    if not settings.STRIPE_SECRET_KEY:
        raise PaymentGatewayError('Stripe is not configured yet. Add STRIPE_SECRET_KEY in the server environment.')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    item = order.items.select_related('product').first()
    if not item or not item.product:
        raise PaymentGatewayError('The selected order does not contain a valid product for Stripe checkout.')

    currency_lower, _ = _get_currency_codes()
    success_url = (
        request.build_absolute_uri(reverse('store:payment_success'))
        + f'?provider=stripe&order_id={order.order_id}&session_id={{CHECKOUT_SESSION_ID}}'
    )
    cancel_url = (
        request.build_absolute_uri(reverse('store:payment_cancel'))
        + f'?provider=stripe&order_id={order.order_id}'
    )
    unit_amount = int((item.price * Decimal('100')).quantize(Decimal('1')))

    try:
        session = stripe.checkout.Session.create(
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=order.order_id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency_lower,
                    'product_data': {
                        'name': item.product.name,
                        'description': item.product.short_description or item.product.name,
                    },
                    'unit_amount': unit_amount,
                },
                'quantity': item.quantity,
            }],
            metadata={
                'order_id': order.order_id,
                'payment_method': 'stripe',
            },
            customer_email=order.email or None,
        )
    except Exception as exc:
        logger.exception('Stripe checkout session creation failed for order %s', order.order_id)
        error_detail = str(exc).strip()
        if error_detail:
            raise PaymentGatewayError(
                f'Stripe checkout session could not be created. Details: {error_detail}'
            )
        raise PaymentGatewayError('Stripe checkout session could not be created. Verify your Stripe key and account settings.')

    checkout_url = getattr(session, 'url', '')
    session_id = getattr(session, 'id', '')
    if not checkout_url or not session_id:
        raise PaymentGatewayError('Stripe did not return a valid checkout URL.')

    order.transaction_id = session_id
    order.save(update_fields=['transaction_id', 'updated_at'])
    return checkout_url


def _get_paypal_access_token():
    if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
        raise PaymentGatewayError('PayPal is not configured yet. Add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in the server environment.')

    paypal_base = PAYPAL_API_BASE['live' if settings.PAYPAL_MODE == 'live' else 'sandbox']
    response = requests.post(
        f'{paypal_base}/v1/oauth2/token',
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={'grant_type': 'client_credentials'},
        headers={'Accept': 'application/json'},
        timeout=30,
    )

    if response.status_code >= 400:
        raise PaymentGatewayError(
            f"PayPal authentication failed for mode '{settings.PAYPAL_MODE}'. "
            "Verify that PAYPAL_MODE matches your app credentials (sandbox or live)."
        )

    access_token = response.json().get('access_token')
    if not access_token:
        raise PaymentGatewayError('PayPal did not return an access token.')
    return access_token


def _create_paypal_checkout_order(request, order):
    access_token = _get_paypal_access_token()
    paypal_base = PAYPAL_API_BASE['live' if settings.PAYPAL_MODE == 'live' else 'sandbox']
    item = order.items.select_related('product').first()
    charge = _get_paypal_charge_details(order.total_price)
    site_settings = SiteSettings.get_settings()

    response = requests.post(
        f'{paypal_base}/v2/checkout/orders',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        json={
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': order.order_id,
                'invoice_id': order.order_id,
                'description': item.product.name if item and item.product else f'Order {order.order_id}',
                'amount': {
                    'currency_code': charge['paypal_currency'],
                    'value': f"{charge['paypal_amount']:.2f}",
                },
            }],
            'application_context': {
                'brand_name': site_settings.site_name,
                'user_action': 'PAY_NOW',
                'return_url': (
                    request.build_absolute_uri(reverse('store:payment_success'))
                    + f'?provider=paypal&order_id={order.order_id}&popup=1'
                ),
                'cancel_url': (
                    request.build_absolute_uri(reverse('store:payment_cancel'))
                    + f'?provider=paypal&order_id={order.order_id}&popup=1'
                ),
            },
        },
        timeout=30,
    )

    if response.status_code >= 400:
        error_payload = {}
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = {}
        details = error_payload.get('details', []) if isinstance(error_payload, dict) else []
        issue = details[0].get('issue') if details and isinstance(details[0], dict) else ''
        if issue == 'CURRENCY_NOT_SUPPORTED':
            raise PaymentGatewayError(
                f"PayPal currency '{charge['paypal_currency']}' is not supported for this account. "
                "Change PAYPAL_CURRENCY or your account settings."
            )
        raise PaymentGatewayError('PayPal checkout order could not be created. Verify your PayPal account settings.')

    payload = response.json()
    paypal_order_id = payload.get('id')
    approval_url = next((link.get('href') for link in payload.get('links', []) if link.get('rel') == 'approve'), '')
    if not paypal_order_id or not approval_url:
        raise PaymentGatewayError('PayPal did not return a valid approval URL.')

    order.transaction_id = paypal_order_id
    order.save(update_fields=['transaction_id', 'updated_at'])
    return approval_url


def _confirm_stripe_payment(session_id):
    if stripe is None:
        raise PaymentGatewayError('Stripe SDK is not installed on the server environment.')
    if not settings.STRIPE_SECRET_KEY:
        raise PaymentGatewayError('Stripe is not configured yet. Add STRIPE_SECRET_KEY in the server environment.')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        raise PaymentGatewayError('Unable to verify the Stripe payment result.')

    payment_status = getattr(session, 'payment_status', '')
    if payment_status != 'paid':
        raise PaymentGatewayError('The Stripe payment is not marked as paid yet.')
    return {
        'payment_intent': getattr(session, 'payment_intent', ''),
        'id': getattr(session, 'id', ''),
    }


def _capture_paypal_payment(paypal_order_id):
    access_token = _get_paypal_access_token()
    paypal_base = PAYPAL_API_BASE['live' if settings.PAYPAL_MODE == 'live' else 'sandbox']
    response = requests.post(
        f'{paypal_base}/v2/checkout/orders/{paypal_order_id}/capture',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        json={},
        timeout=30,
    )

    if response.status_code >= 400:
        raise PaymentGatewayError('Unable to capture the PayPal payment.')

    payload = response.json()
    if payload.get('status') != 'COMPLETED':
        raise PaymentGatewayError('The PayPal payment is not completed.')
    return payload


def _popup_aware_redirect(request, target_url_name=None, target_url=None):
    """
    Redirect normally, but if payment was completed inside a popup window
    send lightweight JS that redirects opener to target and closes popup.
    """
    if target_url is None:
        if not target_url_name:
            raise ValueError('Either target_url_name or target_url must be provided.')
        target_url = reverse(target_url_name)
    if request.GET.get('popup') != '1':
        return redirect(target_url)

    target_json = json.dumps(target_url)
    return HttpResponse(
        f"""
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Redirecting...</title></head>
<body>
<script>
(function () {{
  var target = {target_json};
  if (window.opener && !window.opener.closed) {{
    window.opener.location.href = target;
    window.close();
  }} else {{
    window.location.href = target;
  }}
}})();
</script>
</body>
</html>
"""
    )


def get_profile(request):
    """Helper function to get profile from session."""
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if request.session.get('user_id') != request.user.id:
            request.session['user_id'] = request.user.id
        if request.session.get('username') != request.user.username:
            request.session['username'] = request.user.username
        return profile

    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            return profile
        except User.DoesNotExist:
            request.session.pop('user_id', None)
            request.session.pop('username', None)
            return None
    return None


@require_GET
def services_summary(request):
    active_products = Product.objects.filter(is_active=True, status='active')
    category_labels = dict(Product.CATEGORY_CHOICES)
    category_counts = (
        active_products.values('category')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    categories = [
        {
            'value': entry['category'],
            'label': category_labels.get(entry['category'], entry['category']),
            'count': entry['total'],
        }
        for entry in category_counts
        if entry['category']
    ]
    products = active_products.order_by('-featured', '-created_at')[:8]
    product_list = [{'id': product.id, 'name': product.name} for product in products]
    return JsonResponse({
        'categories': categories,
        'products': product_list,
    })


def home(request):
    profile = get_profile(request)
    active_products = Product.objects.filter(is_active=True, status='active')
    featured_products = active_products.filter(featured=True).order_by('-featured_order', '-created_at')[:6]
    all_products = active_products.order_by('-created_at')[:12]

    category_counts = active_products.values('category').annotate(total=Count('id')).order_by('-total')[:6]
    category_labels = dict(Product.CATEGORY_CHOICES)
    category_highlights = [
        {
            'value': entry['category'],
            'label': category_labels.get(entry['category'], entry['category']),
            'total': entry['total'],
        }
        for entry in category_counts
    ]

    return render(request, 'store/home.html', {
        'profile': profile,
        'featured_products': featured_products,
        'all_products': all_products,
        'category_highlights': category_highlights,
        'total_active_products': active_products.count(),
    })

def about(request):
    profile = get_profile(request)
    return render(request, 'store/about.html', {'profile': profile})

def contact(request):
    profile = get_profile(request)
    return render(request, 'store/contact.html', {'profile': profile})

def faq(request):
    profile = get_profile(request)
    return render(request, 'store/faq.html', {'profile': profile})


class AgentsHubView(TemplateView):
    template_name = 'store/ai_agents.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agents = list(get_agent_catalog().values())
        context['profile'] = get_profile(self.request)
        context['agents'] = agents
        context['default_agent_id'] = agents[0]['id']
        context['agent_prompts'] = {agent['id']: agent['quick_prompts'] for agent in agents}
        context['featured_products'] = Product.objects.filter(
            is_active=True,
            status='active'
        ).order_by('-featured', '-created_at')[:6]
        return context


def _extract_query_tokens(message: str) -> list[str]:
    raw_tokens = re.findall(r"[\w']+", message.lower(), flags=re.UNICODE)
    unique_tokens = []
    seen = set()
    for token in raw_tokens:
        if len(token) < 3:
            continue
        if token in seen:
            continue
        unique_tokens.append(token)
        seen.add(token)
    return unique_tokens[:10]


def _find_relevant_products(message: str, limit: int = 6):
    queryset = Product.objects.filter(is_active=True, status='active')
    tokens = _extract_query_tokens(message)
    if not tokens:
        return queryset.order_by('-featured', '-created_at')[:limit]

    token_query = Q()
    for token in tokens:
        token_query |= (
            Q(name__icontains=token) |
            Q(short_description__icontains=token) |
            Q(description__icontains=token) |
            Q(category__icontains=token) |
            Q(brand__icontains=token) |
            Q(tags__icontains=token)
        )

    matched = queryset.filter(token_query).distinct().order_by('-featured', '-created_at')
    if matched.exists():
        return matched[:limit]
    return queryset.order_by('-featured', '-created_at')[:limit]


def _sanitize_agent_history(raw_history) -> list[dict[str, str]]:
    if not isinstance(raw_history, list):
        return []

    cleaned: list[dict[str, str]] = []
    for item in raw_history[-MAX_SESSION_HISTORY_ITEMS:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get('role', '')).strip().lower()
        if role not in {'user', 'assistant'}:
            continue
        content = str(item.get('content', '')).strip()
        if not content:
            continue
        cleaned.append({
            'role': role,
            'content': content[:MAX_SESSION_MESSAGE_CHARS],
        })
    return cleaned


def _get_agent_history(request, agent_id: str) -> list[dict[str, str]]:
    history_map = request.session.get(AGENT_SESSION_KEY, {})
    if not isinstance(history_map, dict):
        history_map = {}
    return _sanitize_agent_history(history_map.get(agent_id, []))


def _save_agent_history(request, agent_id: str, history: list[dict[str, str]]) -> None:
    history_map = request.session.get(AGENT_SESSION_KEY, {})
    if not isinstance(history_map, dict):
        history_map = {}
    history_map[agent_id] = _sanitize_agent_history(history)
    request.session[AGENT_SESSION_KEY] = history_map
    request.session.modified = True


def _serialize_product(product: Product) -> dict:
    image_url = product.main_image.url if product.main_image else ''
    currency_label = _get_currency_label()
    return {
        'id': product.id,
        'name': product.name,
        'category': product.get_category_display(),
        'price_label': f"{product.current_price} {currency_label}",
        'in_stock': product.in_stock,
        'url': reverse('store:product_detail', args=[product.id]),
        'image_url': image_url,
    }


@require_http_methods(["POST"])
def ai_agent_chat(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = request.POST

    catalog = get_agent_catalog()
    requested_agent_id = str(payload.get('agent_id', 'shop_strategist')).strip()
    agent = catalog.get(requested_agent_id, catalog['shop_strategist'])
    message = str(payload.get('message', '')).strip()

    if not message:
        return JsonResponse({
            'ok': False,
            'error': 'Please enter a message.'
        }, status=400)

    message = message[:1200]
    product_matches = _find_relevant_products(message, limit=6)
    recommendations = [_serialize_product(product) for product in product_matches]
    history = _get_agent_history(request, agent['id'])
    reply = generate_agent_reply(agent['id'], message, recommendations, history=history)
    updated_history = history + [
        {'role': 'user', 'content': message},
        {'role': 'assistant', 'content': reply},
    ]
    _save_agent_history(request, agent['id'], updated_history)

    return JsonResponse({
        'ok': True,
        'agent': {
            'id': agent['id'],
            'name': agent['name'],
            'tagline': agent['tagline'],
        },
        'reply': reply,
        'recommendations': recommendations[:4],
        'timestamp': timezone.now().isoformat(),
    })


# ==================== FRONTEND PRODUCT VIEWS ====================

class StoreProductListView(ListView):
    """
    Display all products with filtering and search for customers.
    """
    model = Product
    template_name = 'store/store.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True, status='active').order_by('-created_at')
        
        # Search
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(short_description__icontains=search) |
                Q(brand__icontains=search)
            )
        
        # Filter by category
        category = self.request.GET.get('category')
        if category and category != 'all':
            queryset = queryset.filter(category=category)
        
        # Filter by price
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass
        
        # Filter in stock only
        in_stock_only = self.request.GET.get('in_stock')
        if in_stock_only == 'true':
            queryset = queryset.filter(stock_quantity__gt=0)
        
        # Filter by featured
        featured_only = self.request.GET.get('featured')
        if featured_only == 'true':
            queryset = queryset.filter(featured=True)
        
        # Sorting
        sort_by = self.request.GET.get('sort', 'newest')
        if sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'featured':
            queryset = queryset.order_by('-featured_order', '-created_at')
        else:  # newest
            queryset = queryset.order_by('-created_at')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_profile(self.request)
        context['categories'] = Product.CATEGORY_CHOICES
        context['total_products'] = Product.objects.filter(is_active=True).count()
        context['currency_label'] = _get_currency_label()
        
        # Pass search/filter parameters to template
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', 'all')
        context['min_price'] = self.request.GET.get('min_price', '')
        context['max_price'] = self.request.GET.get('max_price', '')
        context['sort_by'] = self.request.GET.get('sort', 'newest')
        context['in_stock_only'] = self.request.GET.get('in_stock', '')
        context['featured_only'] = self.request.GET.get('featured', '')

        search_query = context['search_query']
        if search_query:
            record_event(
                self.request,
                'search',
                details={
                    'query': search_query,
                    'category': context['selected_category'],
                },
            )

        selected_category = context['selected_category']
        if selected_category and selected_category != 'all':
            category_label = dict(Product.CATEGORY_CHOICES).get(selected_category, selected_category)
            record_event(
                self.request,
                'category_view',
                details={
                    'category': selected_category,
                    'label': category_label,
                },
            )
        
        return context


class DiscountedProductsView(ListView):
    """
    Show products that currently have discount pricing or promo discount text.
    """
    model = Product
    template_name = 'store/discounts.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        return Product.objects.filter(
            is_active=True,
            status='active'
        ).filter(
            Q(discount_price__isnull=False) | ~Q(discount_note='')
        ).order_by('-featured', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_profile(self.request)
        context['currency_label'] = _get_currency_label()
        context['total_discounted_products'] = self.get_queryset().count()
        return context


class StoreQuickActionView(View):
    def post(self, request):
        action = (request.POST.get('action') or '').strip().lower()
        next_url = (request.POST.get('next') or '').strip()
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()
        ):
            next_url = reverse('store:store')

        if not request.user.is_authenticated:
            return redirect_to_login(next_url, login_url=reverse('user:login'))

        product_id_raw = request.POST.get('product_id', '').strip()
        try:
            product_id = int(product_id_raw)
        except (TypeError, ValueError):
            messages.error(request, 'المنتج غير صالح.')
            return redirect(next_url)

        product = Product.objects.filter(pk=product_id, is_active=True, status='active').first()
        if not product:
            messages.error(request, 'هذا المنتج غير متوفر حالياً.')
            return redirect(next_url)

        if action == 'add_to_wishlist':
            wishlist = _get_session_wishlist(request)
            if product.pk in wishlist:
                messages.info(request, 'هذا المنتج موجود بالفعل في قائمة الأحلام.')
            else:
                wishlist.append(product.pk)
                _save_session_wishlist(request, wishlist)
                messages.success(request, 'تمت إضافة المنتج إلى قائمة الأحلام.')
                record_event(
                    request,
                    'wishlist_add',
                    product=product,
                    details={'source': 'store_quick_action'},
                )
            return redirect(next_url)

        if action == 'add_to_cart':
            if not product.in_stock:
                messages.error(request, 'هذا المنتج غير متوفر حالياً ولا يمكن إضافته للعربة.')
                return redirect(next_url)

            try:
                quantity = int(request.POST.get('quantity', 1))
            except (TypeError, ValueError):
                quantity = 1
            quantity = max(1, quantity)

            if quantity > product.stock_quantity:
                quantity = product.stock_quantity
                messages.warning(request, f'تم تعديل الكمية إلى {quantity} حسب المتوفر.')

            _, added_quantity = _add_product_to_cart(request, product, quantity)
            record_event(
                request,
                'add_to_cart',
                product=product,
                details={
                    'requested_quantity': quantity,
                    'added_quantity': added_quantity,
                    'source': 'store_quick_action',
                },
            )
            if added_quantity <= 0:
                messages.info(request, 'المنتج موجود في العربة بالفعل بأقصى كمية متاحة.')
            else:
                messages.success(request, f'تمت إضافة {added_quantity} من "{product.name}" إلى العربة.')
            return redirect(next_url)

        messages.error(request, 'طلب غير صالح.')
        return redirect(next_url)


class ProductDetailView(DetailView):
    model = Product
    template_name = 'store/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings_obj = SiteSettings.get_settings()
        whatsapp_number = re.sub(r'\D', '', settings_obj.whatsapp_number or '')

        if self.object.stock_quantity <= 0:
            stock_meter = 0
        elif self.object.stock_quantity <= 10:
            stock_meter = 32
        elif self.object.stock_quantity <= 30:
            stock_meter = 66
        else:
            stock_meter = 100

        context['profile'] = get_profile(self.request)
        context['product_images'] = ProductImage.objects.filter(product=self.object)
        context['currency_label'] = _get_currency_label()
        context['stock_meter'] = stock_meter
        context['support_email'] = settings_obj.support_email or 'nextec.web@gmail.com'
        context['whatsapp_number'] = whatsapp_number
        context['free_shipping_threshold'] = settings_obj.free_shipping_threshold
        cart = _get_session_cart(self.request)
        wishlist = _get_session_wishlist(self.request)
        context['cart_quantity'] = int(cart.get(str(self.object.pk), {}).get('quantity', 0) or 0)
        context['in_wishlist'] = self.object.pk in wishlist
        context['related_products'] = Product.objects.filter(
            is_active=True,
            status='active',
            category=self.object.category
        ).exclude(pk=self.object.pk).order_by('-featured', '-created_at')[:6]
        return context

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        product = self.get_object()
        action = (request.POST.get('action') or 'buy_now').strip().lower()

        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1

        quantity = max(1, quantity)
        if action == 'add_to_wishlist':
            wishlist = _get_session_wishlist(request)
            if product.pk in wishlist:
                messages.info(request, 'هذا المنتج موجود بالفعل في قائمة الأحلام.')
            else:
                wishlist.append(product.pk)
                _save_session_wishlist(request, wishlist)
                messages.success(request, 'تمت إضافة المنتج إلى قائمة الأحلام.')
                record_event(
                    request,
                    'wishlist_add',
                    product=product,
                    details={'source': 'product_detail'},
                )
            return redirect('store:product_detail', pk=product.pk)

        if action == 'add_to_goal':
            goal_title = f'شراء المنتج: {product.name}'
            goal_exists = Goal.objects.filter(
                user=request.user,
                title=goal_title,
                completed=False
            ).exists()
            if goal_exists:
                messages.info(request, 'هذا المنتج مضاف مسبقًا ضمن أهدافك.')
            else:
                Goal.objects.create(
                    user=request.user,
                    title=goal_title,
                    description=f'أريد شراء المنتج "{product.name}" من المتجر.'
                )
                messages.success(request, 'تمت إضافة المنتج إلى أهدافك بنجاح.')
            return redirect('store:product_detail', pk=product.pk)

        if action == 'add_to_cart':
            if not product.in_stock:
                messages.error(request, 'هذا المنتج غير متوفر حالياً ولا يمكن إضافته للعربة.')
                return redirect('store:product_detail', pk=product.pk)
            if quantity > product.stock_quantity:
                quantity = product.stock_quantity
                messages.warning(request, f'تم تعديل الكمية إلى {quantity} حسب المتوفر.')

            _, added_quantity = _add_product_to_cart(request, product, quantity)
            record_event(
                request,
                'add_to_cart',
                product=product,
                details={
                    'requested_quantity': quantity,
                    'added_quantity': added_quantity,
                    'source': 'product_detail',
                },
            )
            if added_quantity <= 0:
                messages.info(request, 'المنتج موجود في العربة بالفعل بأقصى كمية متاحة.')
            else:
                messages.success(request, f'تمت إضافة {added_quantity} من "{product.name}" إلى العربة.')
            return redirect('store:product_detail', pk=product.pk)

        if not product.in_stock:
            messages.error(request, 'هذا المنتج غير متوفر حالياً.')
            return redirect('store:product_detail', pk=product.pk)

        if quantity > product.stock_quantity:
            quantity = product.stock_quantity
            messages.warning(request, f'تم تعديل الكمية إلى {quantity} حسب المتوفر.')

        shipping_payload = {}
        if not product.is_digital:
            customer_phone = request.POST.get('customer_phone', '').strip()
            shipping_country = request.POST.get('shipping_country', '').strip()
            shipping_city = request.POST.get('shipping_city', '').strip()
            shipping_address = request.POST.get('shipping_address', '').strip()
            shipping_latitude_raw = request.POST.get('shipping_latitude', '').strip()
            shipping_longitude_raw = request.POST.get('shipping_longitude', '').strip()

            if not all([customer_phone, shipping_country, shipping_city, shipping_address]):
                messages.error(request, 'قبل الدفع، يرجى إدخال رقم الهاتف، الدولة، المدينة، والعنوان الكامل.')
                return redirect('store:product_detail', pk=product.pk)

            try:
                shipping_latitude = Decimal(shipping_latitude_raw)
                shipping_longitude = Decimal(shipping_longitude_raw)
            except (TypeError, ValueError, ArithmeticError):
                messages.error(request, 'يرجى تحديد موقعك الدقيق من الخريطة قبل إكمال الدفع.')
                return redirect('store:product_detail', pk=product.pk)

            if not (-90 <= shipping_latitude <= 90 and -180 <= shipping_longitude <= 180):
                messages.error(request, 'إحداثيات الموقع غير صالحة. الرجاء اختيار الموقع من الخريطة مرة أخرى.')
                return redirect('store:product_detail', pk=product.pk)

            shipping_payload = {
                'phone': customer_phone,
                'address': shipping_address,
                'city': shipping_city,
                'country': shipping_country,
                'shipping_latitude': shipping_latitude,
                'shipping_longitude': shipping_longitude,
            }

        user = request.user
        price = product.current_price
        line_subtotal = price * quantity
        selected_payment_method = request.POST.get('payment_method', '').strip()
        allowed_payment_methods = dict(product.allowed_payment_methods)
        is_free_checkout = line_subtotal <= Decimal('0')

        if is_free_checkout:
            if not selected_payment_method:
                if allowed_payment_methods:
                    selected_payment_method = next(iter(allowed_payment_methods.keys()))
                else:
                    selected_payment_method = 'other'
            elif allowed_payment_methods and selected_payment_method not in allowed_payment_methods:
                messages.error(request, 'طريقة الدفع المختارة غير متاحة لهذا المنتج.')
                return redirect('store:product_detail', pk=product.pk)
        else:
            if not allowed_payment_methods:
                messages.error(request, 'هذا المنتج لا يحتوي على إعداد دفع صالح حالياً. يرجى مراجعة الإدارة.')
                return redirect('store:product_detail', pk=product.pk)

            if selected_payment_method not in allowed_payment_methods:
                messages.error(request, 'طريقة الدفع المختارة غير متاحة لهذا المنتج.')
                return redirect('store:product_detail', pk=product.pk)

        if is_free_checkout:
            order = _create_online_order(
                user,
                product,
                quantity,
                selected_payment_method,
                shipping_data=shipping_payload,
            )
            order.payment_status = 'completed'
            order.status = 'processing'
            order.transaction_id = f"FREE-{timezone.now().strftime('%Y%m%d%H%M%S')}-{order.pk}"
            order.save(update_fields=['payment_status', 'status', 'transaction_id', 'updated_at'])

            messages.success(
                request,
                f'تم إنشاء طلب تجريبي مجاني (0 { _get_currency_label() }) بنجاح. الكمية: {quantity}'
            )
            return redirect('store:orders')

        if selected_payment_method in ONLINE_PAYMENT_METHODS:
            order = _create_online_order(
                user,
                product,
                quantity,
                selected_payment_method,
                shipping_data=shipping_payload,
            )
            if selected_payment_method == 'paypal':
                try:
                    approval_url = _create_paypal_checkout_order(request, order)
                except (requests.RequestException, PaymentGatewayError):
                    order.delete()
                    messages.error(request, 'تعذر بدء PayPal Checkout الآن. تأكد من إعدادات PayPal ثم حاول مرة أخرى.')
                    return redirect('store:product_detail', pk=product.pk)
                return redirect(approval_url)

            try:
                checkout_url = _create_stripe_checkout_session(request, order)
            except (requests.RequestException, PaymentGatewayError) as exc:
                order.delete()
                error_text = str(exc)
                if 'api.stripe.com' in error_text or 'connection' in error_text.lower():
                    messages.error(
                        request,
                        'تعذر الاتصال بخادم Stripe من السيرفر. '
                        'تحقق من الإنترنت/Firewall وافتح api.stripe.com على المنفذ 443 ثم أعد المحاولة.'
                    )
                else:
                    messages.error(
                        request,
                        'تعذر بدء الدفع الإلكتروني عبر Stripe. '
                        f'التفاصيل: {error_text}'
                    )
                return redirect('store:product_detail', pk=product.pk)
            return redirect(checkout_url)

        order = Order.objects.filter(
            user=user,
            status='pending',
            payment_method=selected_payment_method,
        ).order_by('-created_at').first()

        if order:
            order.total_price += line_subtotal
            order.subtotal += line_subtotal
            if not order.full_name:
                order.full_name = user.get_full_name() or user.username
            if not order.email:
                order.email = user.email or ''
            if shipping_payload:
                order.phone = shipping_payload.get('phone', order.phone)
                order.address = shipping_payload.get('address', order.address)
                order.city = shipping_payload.get('city', order.city)
                order.country = shipping_payload.get('country', order.country)
                order.shipping_latitude = shipping_payload.get('shipping_latitude')
                order.shipping_longitude = shipping_payload.get('shipping_longitude')
            order.save()
        else:
            order = Order.objects.create(
                user=user,
                full_name=user.get_full_name() or user.username,
                email=user.email or '',
                phone=shipping_payload.get('phone', ''),
                address=shipping_payload.get('address', ''),
                city=shipping_payload.get('city', ''),
                country=shipping_payload.get('country', ''),
                shipping_latitude=shipping_payload.get('shipping_latitude'),
                shipping_longitude=shipping_payload.get('shipping_longitude'),
                total_price=line_subtotal,
                subtotal=line_subtotal,
                tax_amount=0,
                shipping_cost=0,
                discount_amount=0,
                payment_method=selected_payment_method,
            )
        OrderItem.objects.create(order=order, product=product, quantity=quantity, price=price, subtotal=line_subtotal)

        if selected_payment_method == 'cash_on_delivery':
            messages.success(request, f'تم إنشاء طلب الدفع عند الاستلام بنجاح. الكمية: {quantity}')
        else:
            messages.success(
                request,
                f'تم إنشاء الطلب مع طريقة الدفع {allowed_payment_methods[selected_payment_method]}. الكمية: {quantity}'
            )
        return redirect('store:orders')


class PaymentSuccessView(LoginRequiredMixin, View):
    """
    Handle successful return from online payment providers.
    """
    def get(self, request):
        provider = request.GET.get('provider', '').strip().lower()
        order_id = request.GET.get('order_id', '').strip()
        order = get_object_or_404(Order, order_id=order_id, user=request.user)

        if order.payment_status == 'completed':
            messages.success(
                request,
                format_html(
                    'تم تأكيد الدفع مسبقًا للطلب <strong>{}</strong>. '
                    'للتواصل السريع: <a href="{}" target="_blank" rel="noopener noreferrer">WhatsApp {}</a>.',
                    order.order_id,
                    SUPPORT_WHATSAPP_WA_LINK,
                    SUPPORT_WHATSAPP_DISPLAY,
                ),
            )
            return _popup_aware_redirect(request, 'dashboard:index')

        try:
            if provider == 'stripe':
                session_id = request.GET.get('session_id', '').strip() or order.transaction_id
                if not session_id:
                    raise PaymentGatewayError('Missing Stripe session ID.')
                payload = _confirm_stripe_payment(session_id)
                order.transaction_id = payload.get('payment_intent') or session_id
            elif provider == 'paypal':
                paypal_order_id = request.GET.get('token', '').strip() or order.transaction_id
                if not paypal_order_id:
                    raise PaymentGatewayError('Missing PayPal order token.')
                payload = _capture_paypal_payment(paypal_order_id)
                captures = payload.get('purchase_units', [{}])[0].get('payments', {}).get('captures', [])
                order.transaction_id = captures[0].get('id') if captures else paypal_order_id
            else:
                raise PaymentGatewayError('Unknown payment provider.')
        except (requests.RequestException, PaymentGatewayError):
            messages.error(request, 'تعذر تأكيد الدفع الإلكتروني. إذا خُصم المبلغ، تحقق من لوحة الدفع ثم حدّث الطلب يدويًا.')
            cancel_params = {'order_id': order.order_id}
            if provider:
                cancel_params['provider'] = provider
            if request.GET.get('popup') == '1':
                cancel_params['popup'] = '1'
            cancel_url = f"{reverse('store:payment_cancel')}?{urlencode(cancel_params)}"
            return redirect(cancel_url)

        order.payment_status = 'completed'
        order.status = 'processing'
        order.save(update_fields=['payment_status', 'status', 'transaction_id', 'updated_at'])
        messages.success(
            request,
            format_html(
                'تمت عملية الدفع بنجاح للطلب <strong>{}</strong>. '
                'يمكنك التحدث معي مباشرة عبر <a href="{}" target="_blank" rel="noopener noreferrer">WhatsApp {}</a>.',
                order.order_id,
                SUPPORT_WHATSAPP_WA_LINK,
                SUPPORT_WHATSAPP_DISPLAY,
            ),
        )
        return _popup_aware_redirect(request, 'dashboard:index')


class PayPalCheckoutView(LoginRequiredMixin, View):
    """
    Dedicated internal page before redirecting the user to PayPal checkout.
    """
    template_name = 'store/paypal_checkout.html'

    def get_order(self, request, order_id):
        return get_object_or_404(
            Order.objects.prefetch_related('items__product'),
            order_id=order_id,
            user=request.user,
            payment_method='paypal',
        )

    def get(self, request, order_id):
        order = self.get_order(request, order_id)

        if order.payment_status == 'completed':
            messages.success(request, f'Order {order.order_id} is already paid.')
            return redirect('store:orders')

        charge = _get_paypal_charge_details(order.total_price)
        context = {
            'profile': get_profile(request),
            'order': order,
            'currency_label': _get_currency_label(),
            'paypal_charge': charge,
        }
        return render(request, self.template_name, context)

    def post(self, request, order_id):
        order = self.get_order(request, order_id)

        if order.payment_status == 'completed':
            messages.success(request, f'Order {order.order_id} is already paid.')
            return redirect('store:orders')

        try:
            approval_url = _create_paypal_checkout_order(request, order)
        except (requests.RequestException, PaymentGatewayError):
            messages.error(request, 'تعذر بدء PayPal Checkout الآن. تأكد من إعدادات PayPal ثم حاول مرة أخرى.')
            return redirect('store:paypal_checkout', order_id=order.order_id)

        return redirect(approval_url)


class PaymentCancelView(LoginRequiredMixin, View):
    """
    Handle canceled online payment attempts.
    """
    def get(self, request):
        order_id = request.GET.get('order_id', '').strip()
        provider = request.GET.get('provider', '').strip().lower()
        order = get_object_or_404(Order, order_id=order_id, user=request.user)

        if order.payment_status != 'completed':
            order.payment_status = 'failed'
            order.status = 'cancelled'
            order.save(update_fields=['payment_status', 'status', 'updated_at'])
            status_kind = 'cancelled'
            cancel_message = f'تم إلغاء الدفع الإلكتروني للطلب {order.order_id}.'
        else:
            status_kind = 'already_paid'
            cancel_message = f'الطلب {order.order_id} مدفوع بالفعل.'

        if request.GET.get('popup') == '1':
            cancel_params = {'order_id': order.order_id}
            if provider:
                cancel_params['provider'] = provider
            cancel_url = f"{reverse('store:payment_cancel')}?{urlencode(cancel_params)}"
            return _popup_aware_redirect(request, target_url=cancel_url)

        first_item = order.items.select_related('product').first()
        retry_url = reverse('store:store')
        if first_item and first_item.product:
            retry_url = reverse('store:product_detail', args=[first_item.product.pk])

        context = {
            'profile': get_profile(request),
            'order': order,
            'provider': provider,
            'cancel_message': cancel_message,
            'status_kind': status_kind,
            'retry_url': retry_url,
        }
        return render(request, 'store/payment_cancel.html', context)


class CartView(LoginRequiredMixin, View):
    template_name = 'store/cart.html'

    def get(self, request):
        cart = _get_session_cart(request)
        product_ids = [int(product_id) for product_id in cart.keys()]
        products_by_id = Product.objects.filter(id__in=product_ids).in_bulk()

        cart_items = []
        cod_items = []
        online_items = []
        cart_total = Decimal('0')
        cod_total = Decimal('0')
        online_total = Decimal('0')
        cod_units = 0
        online_units = 0
        cart_changed = False

        for product_id_str, entry in list(cart.items()):
            product_id = int(product_id_str)
            product = products_by_id.get(product_id)
            if not product:
                cart.pop(product_id_str, None)
                cart_changed = True
                continue

            quantity = int(entry.get('quantity', 1) or 1)
            quantity = max(1, quantity)
            if product.stock_quantity > 0 and quantity > product.stock_quantity:
                quantity = product.stock_quantity
                cart[product_id_str] = {'quantity': quantity}
                cart_changed = True

            line_total = product.current_price * quantity
            cart_total += line_total
            item_payload = {
                'product': product,
                'quantity': quantity,
                'line_total': line_total,
                'is_online_payment': product.requires_online_payment,
                'payment_mode_label': product.get_payment_mode_display(),
            }
            cart_items.append(item_payload)

            if product.requires_online_payment:
                online_items.append(item_payload)
                online_total += line_total
                online_units += quantity
            else:
                cod_items.append(item_payload)
                cod_total += line_total
                cod_units += quantity

        if cart_changed:
            _save_session_cart(request, cart)

        context = {
            'profile': get_profile(request),
            'cart_items': cart_items,
            'cod_items': cod_items,
            'online_items': online_items,
            'cart_total': cart_total,
            'cod_total': cod_total,
            'online_total': online_total,
            'cod_units': cod_units,
            'online_units': online_units,
            'currency_label': _get_currency_label(),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = (request.POST.get('action') or '').strip().lower()
        cart = _get_session_cart(request)

        if action == 'clear':
            _save_session_cart(request, {})
            messages.info(request, 'تم تفريغ العربة.')
            return redirect('store:cart')

        product_id_raw = request.POST.get('product_id', '').strip()
        try:
            product_id = int(product_id_raw)
        except (TypeError, ValueError):
            messages.error(request, 'المنتج غير صالح.')
            return redirect('store:cart')

        product_key = str(product_id)
        if product_key not in cart:
            messages.info(request, 'هذا المنتج غير موجود في العربة.')
            return redirect('store:cart')

        if action == 'remove':
            cart.pop(product_key, None)
            _save_session_cart(request, cart)
            messages.success(request, 'تم حذف المنتج من العربة.')
            return redirect('store:cart')

        if action == 'update':
            try:
                quantity = int(request.POST.get('quantity', 1))
            except (TypeError, ValueError):
                quantity = 1
            quantity = max(1, quantity)

            product = Product.objects.filter(pk=product_id).first()
            if product and product.stock_quantity > 0:
                quantity = min(quantity, product.stock_quantity)

            cart[product_key] = {'quantity': quantity}
            _save_session_cart(request, cart)
            messages.success(request, 'تم تحديث كمية المنتج في العربة.')
            return redirect('store:cart')

        return redirect('store:cart')


class WishlistView(LoginRequiredMixin, View):
    template_name = 'store/wishlist.html'

    def get(self, request):
        wishlist = _get_session_wishlist(request)
        products_by_id = Product.objects.filter(id__in=wishlist).in_bulk()
        ordered_products = [products_by_id[product_id] for product_id in wishlist if product_id in products_by_id]

        if len(ordered_products) != len(wishlist):
            cleaned = [product.id for product in ordered_products]
            _save_session_wishlist(request, cleaned)

        context = {
            'profile': get_profile(request),
            'wishlist_products': ordered_products,
            'currency_label': _get_currency_label(),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = (request.POST.get('action') or '').strip().lower()
        wishlist = _get_session_wishlist(request)

        if action == 'clear':
            _save_session_wishlist(request, [])
            messages.info(request, 'تم تفريغ قائمة الأحلام.')
            return redirect('store:wishlist')

        product_id_raw = request.POST.get('product_id', '').strip()
        try:
            product_id = int(product_id_raw)
        except (TypeError, ValueError):
            messages.error(request, 'المنتج غير صالح.')
            return redirect('store:wishlist')

        if product_id not in wishlist:
            messages.info(request, 'هذا المنتج غير موجود في قائمة الأحلام.')
            return redirect('store:wishlist')

        if action == 'remove':
            wishlist = [item for item in wishlist if item != product_id]
            _save_session_wishlist(request, wishlist)
            messages.success(request, 'تم حذف المنتج من قائمة الأحلام.')
            return redirect('store:wishlist')

        if action == 'move_to_cart':
            product = Product.objects.filter(pk=product_id).first()
            if not product:
                wishlist = [item for item in wishlist if item != product_id]
                _save_session_wishlist(request, wishlist)
                messages.error(request, 'هذا المنتج لم يعد متوفرًا.')
                return redirect('store:wishlist')

            if not product.in_stock:
                messages.error(request, 'المنتج غير متوفر حاليًا ولا يمكن نقله للعربة.')
                return redirect('store:wishlist')

            _add_product_to_cart(request, product, 1)
            wishlist = [item for item in wishlist if item != product_id]
            _save_session_wishlist(request, wishlist)
            messages.success(request, 'تم نقل المنتج من قائمة الأحلام إلى العربة.')
            return redirect('store:wishlist')

        return redirect('store:wishlist')


class OrdersListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'store/orders.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_profile(self.request)
        return context


class ChatView(LoginRequiredMixin, View):
    """Redirect users to the real-time support chat app."""

    def get(self, request):
        return redirect('chat:chat')

    def post(self, request):
        return redirect('chat:chat')
