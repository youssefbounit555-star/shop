from django.urls import path, include
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.StoreProductListView.as_view(), name='store'),
    path('home/', views.home, name='home'),
    path('discounts/', views.DiscountedProductsView.as_view(), name='discounts'),
    path('cart/', views.CartView.as_view(), name='cart'),
    path('wishlist/', views.WishlistView.as_view(), name='wishlist'),
    path('about/', views.about, name='about'),
    path('agents/', views.AgentsHubView.as_view(), name='agents_hub'),
    path('agents/api/chat/', views.ai_agent_chat, name='ai_agent_chat'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('orders/', views.OrdersListView.as_view(), name='orders'),
    path('payments/paypal/<str:order_id>/', views.PayPalCheckoutView.as_view(), name='paypal_checkout'),
    path('payments/success/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('payments/cancel/', views.PaymentCancelView.as_view(), name='payment_cancel'),
    path('chat/', views.ChatView.as_view(), name='chat'),
]
