from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Dashboard
    path('', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='products_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='products_create'),
    path('products/export/', views.ProductExportView.as_view(), name='products_export'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='products_detail'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='products_update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='products_delete'),
    path('products/bulk-action/', views.BulkProductActionView.as_view(), name='bulk_product_action'),
    path('discounts/', views.DiscountsManagementView.as_view(), name='discounts'),
    
    # Orders
    path('orders/', views.OrderListView.as_view(), name='orders_list'),
    path('orders/export/', views.OrderExportView.as_view(), name='orders_export'),
    path('orders/<str:order_id>/', views.OrderDetailView.as_view(), name='orders_detail'),
    path('orders/<str:order_id>/edit/', views.OrderUpdateView.as_view(), name='orders_update'),
    
    # Customers
    path('customers/', views.CustomerListView.as_view(), name='customers_list'),
    path('customers/<str:email>/', views.CustomerDetailView.as_view(), name='customers_detail'),
    path('customers/<str:email>/delete/', views.CustomerDeleteView.as_view(), name='customers_delete'),
    
    # Chat
    path('chat/', views.ChatListView.as_view(), name='chat_list'),
    path('chat/<int:user_id>/', views.ChatDetailView.as_view(), name='chat_detail'),
    
    # Settings
    path('settings/', views.SiteSettingsView.as_view(), name='settings'),
    
    # Analytics
    path('analytics/', views.AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
]
