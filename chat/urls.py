from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # User chat
    path('', views.ChatView.as_view(), name='chat'),
    
    # Admin chat
    path('admin/', views.AdminChatListView.as_view(), name='admin_chat_list'),
    path('admin/<int:pk>/', views.AdminChatDetailView.as_view(), name='admin_chat_detail'),
    
    # AJAX endpoints
    path('api/send/', views.send_message, name='send_message'),
    path('api/load/', views.load_messages, name='load_messages'),
    path('api/unread/', views.get_unread_count, name='get_unread_count'),
    path('api/typing/update/', views.update_typing_status, name='update_typing'),
    path('api/typing/get/', views.get_typing_status, name='get_typing'),
    path('api/quick-replies/', views.get_quick_replies, name='quick_replies'),
    path('api/search/', views.search_messages, name='search_messages'),
    path('api/pin/', views.pin_message, name='pin_message'),
    path('api/status/', views.update_conversation_status, name='update_status'),
]
