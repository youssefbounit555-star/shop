from django.urls import reverse

from .ai_agents import get_agent_catalog
from .geo import get_geo_profile, get_locale_strings


def _cart_count_from_session(request):
    raw_cart = request.session.get('store_cart', {})
    if not isinstance(raw_cart, dict):
        return 0

    total = 0
    for item in raw_cart.values():
        quantity = 0
        if isinstance(item, dict):
            quantity = item.get('quantity', 0)
        else:
            quantity = item
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 0
        if quantity > 0:
            total += quantity
    return total


def _wishlist_count_from_session(request):
    raw_wishlist = request.session.get('store_wishlist', [])
    if not isinstance(raw_wishlist, list):
        return 0

    valid_ids = set()
    for product_id in raw_wishlist:
        try:
            valid_ids.add(int(product_id))
        except (TypeError, ValueError):
            continue
    return len(valid_ids)


def ai_agents_widget_context(request):
    catalog = get_agent_catalog()
    agents = list(catalog.values())
    default_agent_id = agents[0]["id"] if agents else ""

    return {
        "cart_items_count": _cart_count_from_session(request),
        "wishlist_items_count": _wishlist_count_from_session(request),
        "ai_agent_widget": {
            "agents": agents,
            "default_agent_id": default_agent_id,
            "agent_prompts": {agent["id"]: agent["quick_prompts"] for agent in agents},
            "chat_endpoint": reverse("store:ai_agent_chat"),
        }
    }


def geo_context(request):
    profile = getattr(request, "geo_profile", None) or get_geo_profile(request)
    locale_strings = get_locale_strings(profile.language)
    return {
        "geo_profile": {
            "country": profile.country,
            "language": profile.language,
            "currency": profile.currency,
            "currency_label": profile.currency_label,
            "theme": profile.theme,
            "direction": profile.direction,
        },
        "geo_strings": locale_strings,
    }
