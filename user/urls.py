from django.urls import path
from . import views

app_name = 'user'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('login-verify/', views.login_verify_view, name='login_verify'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('password-reset/', views.password_reset, name='password_reset'),
    path('password-reset-confirm/', views.password_reset_confirm, name='password_reset_confirm'),
]
