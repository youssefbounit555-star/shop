from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.DashboardView.as_view(), name='index'),
    
    # Goals/Todos management
    path('goals/', views.GoalsView.as_view(), name='goals'),
    path('goals/add/', views.AddGoalView.as_view(), name='add_goal'),
    path('goals/<int:goal_id>/toggle/', views.ToggleGoalView.as_view(), name='toggle_goal'),
    path('goals/<int:pk>/delete/', views.DeleteGoalView.as_view(), name='delete_goal'),
    
    # Chat/Messaging
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('chat/send/', views.SendMessageView.as_view(), name='send_message'),
    
    # Orders
    path('orders/', views.OrdersView.as_view(), name='orders'),
    path('orders/pending/', views.PendingOrdersView.as_view(), name='pending_orders'),
    path('orders/pending/<int:order_id>/confirm/', views.ConfirmOrderView.as_view(), name='confirm_order'),
    path('orders/pending/<int:order_id>/cancel/', views.CancelOrderView.as_view(), name='cancel_order'),
    
    # Profile
    path('profile/', views.ProfileWidgetView.as_view(), name='profile'),
]
