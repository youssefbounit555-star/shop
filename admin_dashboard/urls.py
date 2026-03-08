from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    # Add product, order, customer, chat, settings URLs here
]
