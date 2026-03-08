from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for UserProfile model.
    """
    list_display = ('get_username', 'get_email', 'country', 'city')
    list_filter = ('country', 'city', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('get_username', 'get_email', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'get_username', 'get_email')
        }),
        ('Address', {
            'fields': ('address', 'city', 'country')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Interests & Avatar', {
            'fields': ('interesting', 'avatar'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_username(self, obj):
        """Display username from related User model."""
        return obj.user.username
    get_username.short_description = 'Username'

    def get_email(self, obj):
        """Display email from related User model."""
        return obj.user.email
    get_email.short_description = 'Email'
    
    def has_add_permission(self, request):
        """Prevent manual profile creation - use signals instead."""
        return False