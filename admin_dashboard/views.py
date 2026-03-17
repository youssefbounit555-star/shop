from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.shortcuts import render
from analytics.models import Insight
from analytics.insights import ensure_recent_insights
from analytics.utils import get_live_counts, LIVE_WINDOW_MINUTES
from store.models import Product

class AdminOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class DashboardView(AdminOnlyMixin, TemplateView):
    template_name = 'admin_dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add statistics and chart data here
        context['total_users'] = 0
        context['total_products'] = 0
        context['total_orders'] = 0
        context['total_revenue'] = 0
        context['new_messages'] = 0
        context['new_reservations'] = 0
        # ...add chart data
        return context

class AnalyticsView(AdminOnlyMixin, TemplateView):
    template_name = 'admin_dashboard/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ensure_recent_insights(days=7, max_age_hours=24)
        context['insights'] = Insight.objects.filter(is_archived=False).order_by('-generated_at')
        live_products = list(
            Product.objects.filter(is_active=True, status='active').order_by('name')
        )
        live_counts = get_live_counts([product.id for product in live_products])
        context['live_products'] = [
            {
                'product': product,
                'count': live_counts.get(product.id, 0),
            }
            for product in live_products
        ]
        context['live_window_minutes'] = LIVE_WINDOW_MINUTES
        return context

# Add Product, Order, Customer, Chat, Settings views here as CBVs
