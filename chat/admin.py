from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Conversation, Message, QuickReply, ConversationTag, TypingIndicator


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'admin_name', 'status_badge', 'priority_badge', 'unread_count', 'created_at', 'response_time_display')
    list_filter = ('status', 'priority', 'created_at', 'is_closed')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'tags')
    readonly_fields = ('created_at', 'updated_at', 'first_response_at', 'get_message_count')
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'admin')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'is_closed')
        }),
        ('Organization', {
            'fields': ('tags', 'notes')
        }),
        ('Satisfaction & Tracking', {
            'fields': ('satisfaction_rating', 'first_response_at', 'get_message_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    customer_name.short_description = 'Customer'
    
    def admin_name(self, obj):
        if obj.admin:
            return obj.admin.get_full_name() or obj.admin.username
        return '—'
    admin_name.short_description = 'Assigned Admin'
    
    def status_badge(self, obj):
        colors = {
            'open': '#007bff',
            'waiting': '#ffc107',
            'pending': '#fd7e14',
            'closed': '#6c757d',
            'resolved': '#28a745'
        }
        color = colors.get(obj.status, '#000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def priority_badge(self, obj):
        colors = {
            'low': '#17a2b8',
            'normal': '#6c757d',
            'high': '#fd7e14',
            'urgent': '#dc3545'
        }
        color = colors.get(obj.priority, '#000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def unread_count(self, obj):
        count = obj.get_unread_count(obj.admin or obj.user)
        if count > 0:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 3px;">{} unread</span>',
                count
            )
        return '—'
    unread_count.short_description = 'Unread'
    
    def response_time_display(self, obj):
        time = obj.get_response_time()
        if time is None:
            return '—'
        return f'{time} min'
    response_time_display.short_description = 'Response Time'
    
    def get_message_count(self, obj):
        return obj.message_set.count()
    get_message_count.short_description = 'Total Messages'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(admin=request.user)
        return qs


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender_name', 'conversation_link', 'message_preview', 'read_status', 'created_at')
    list_filter = ('is_read', 'created_at', 'sender__is_staff')
    search_fields = ('text', 'conversation__user__username')
    readonly_fields = ('created_at', 'edited_at', 'read_at', 'sender', 'conversation')
    fieldsets = (
        ('Message Content', {
            'fields': ('conversation', 'sender', 'text', 'file', 'audio')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'is_pinned')
        }),
        ('Editing', {
            'fields': ('is_edited', 'edited_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username
    sender_name.short_description = 'Sender'
    
    def conversation_link(self, obj):
        url = reverse('admin:chat_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">{} - {}</a>', url, obj.conversation.user.username, obj.conversation.get_status_display())
    conversation_link.short_description = 'Conversation'
    
    def message_preview(self, obj):
        preview = obj.text[:50] if obj.text else '[File/Audio]'
        return preview
    message_preview.short_description = 'Message'
    
    def read_status(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: orange;">⚪ Unread</span>')
    read_status.short_description = 'Status'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(conversation__admin=request.user)
        return qs


@admin.register(QuickReply)
class QuickReplyAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'admin_name', 'is_active', 'updated_at')
    list_filter = ('category', 'is_active', 'admin')
    search_fields = ('title', 'message')
    fieldsets = (
        ('Quick Reply Information', {
            'fields': ('admin', 'title', 'category')
        }),
        ('Message Template', {
            'fields': ('message',),
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
    )
    
    def admin_name(self, obj):
        return obj.admin.get_full_name() or obj.admin.username
    admin_name.short_description = 'Admin'


@admin.register(ConversationTag)
class ConversationTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_display', 'description', 'created_at')
    fields = ('name', 'color', 'description')
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; border-radius: 3px;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'


@admin.register(TypingIndicator)
class TypingIndicatorAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'conversation_link', 'is_typing', 'updated_at')
    list_filter = ('is_typing', 'updated_at')
    readonly_fields = ('updated_at',)
    
    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = 'User'
    
    def conversation_link(self, obj):
        url = reverse('admin:chat_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">{}</a>', url, obj.conversation.user.username)
    conversation_link.short_description = 'Conversation'
