from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('track_event/', views.track_event, name='track_event'),
    path('track_live/', views.track_live, name='track_live'),
    path('live_counts/', views.live_counts, name='live_counts'),
]
