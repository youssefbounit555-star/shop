from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.shortcuts import render

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

# Add Product, Order, Customer, Chat, Settings views here as CBVs
