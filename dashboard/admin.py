from django.contrib import admin
from .models import Goal, Message


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    """
    Admin interface for Goal model.
    """
    list_display = ('title', 'user', 'completed', 'created_at')
    list_filter = ('completed', 'created_at', 'user')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Goal Information', {
            'fields': ('user', 'title', 'description', 'completed')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Only show goals of the current user if not admin."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(user=request.user)
        return qs


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin interface for Message model.
    """
    list_display = ('sender', 'receiver', 'is_read', 'timestamp')
    list_filter = ('is_read', 'timestamp', 'sender', 'receiver')
    search_fields = ('message', 'sender__username', 'receiver__username')
    readonly_fields = ('timestamp', 'message')
    
    fieldsets = (
        ('Message Information', {
            'fields': ('sender', 'receiver', 'message', 'is_read')
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Only show messages sent/received by current user if not admin."""
        from django.db.models import Q
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(Q(sender=request.user) | Q(receiver=request.user))
        return qs