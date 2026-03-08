from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q


class Conversation(models.Model):
    """Customer support conversation between user and admin."""
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('waiting', 'Waiting for Customer'),
        ('pending', 'Pending'),
        ('closed', 'Closed'),
        ('resolved', 'Resolved'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low Priority'),
        ('normal', 'Normal'),
        ('high', 'High Priority'),
        ('urgent', 'Urgent'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='support_conversation')
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_conversations', limit_choices_to={'is_staff': True})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    tags = models.CharField(max_length=300, blank=True, help_text="Comma-separated tags for organization")
    is_closed = models.BooleanField(default=False)
    satisfaction_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    notes = models.TextField(blank=True, help_text="Internal notes for admin only")
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-updated_at']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"Support Chat: {self.user.username} ({self.get_status_display()})"
    
    def get_unread_count(self, viewer):
        """Get unread message count for a viewer (user or admin)."""
        return self.message_set.exclude(sender=viewer).filter(is_read=False).count()
    
    def get_last_message(self):
        """Get the last message in this conversation."""
        return self.message_set.last()
    
    def mark_as_read_for(self, user):
        """Mark all messages as read for a specific user."""
        self.message_set.exclude(sender=user).update(is_read=True)
    
    def get_response_time(self):
        """Calculate average response time in minutes."""
        if not self.first_response_at:
            return None
        return int((self.first_response_at - self.created_at).total_seconds() / 60)
    
    def set_first_response_if_needed(self):
        """Set first response time if admin hasn't replied yet."""
        if not self.first_response_at and self.admin:
            first_admin_msg = self.message_set.filter(sender__is_staff=True).first()
            if first_admin_msg:
                self.first_response_at = first_admin_msg.created_at
                self.save(update_fields=['first_response_at'])
    
    def get_tags_list(self):
        """Return tags as a list."""
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]


class Message(models.Model):
    """Support chat message model."""
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_messages')
    text = models.TextField(blank=True)
    file = models.FileField(upload_to='chat_files/', null=True, blank=True)
    audio = models.FileField(upload_to='chat_audio/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    reaction_emoji = models.CharField(max_length=100, blank=True, help_text="Emoji reactions as JSON")
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', '-created_at']),
            models.Index(fields=['is_read']),
        ]
    
    def __str__(self):
        return f"{self.sender.username}: {self.text[:50]}"
    
    def get_file_type(self):
        """Determine file type from extension."""
        if not self.file:
            return None
        
        ext = self.file.name.split('.')[-1].lower()
        
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return 'image'
        elif ext in ['mp4', 'mov', 'avi', 'mkv', 'webm']:
            return 'video'
        elif ext in ['mp3', 'wav', 'ogg', 'm4a', 'aac']:
            return 'audio'
        elif ext == 'pdf':
            return 'pdf'
        elif ext in ['doc', 'docx']:
            return 'document'
        elif ext in ['xls', 'xlsx']:
            return 'spreadsheet'
        elif ext == 'zip':
            return 'archive'
        else:
            return 'file'
    
    def mark_as_read(self):
        """Mark message as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
            
            # Set first response time if admin is sending
            if self.sender.is_staff and not self.conversation.first_response_at:
                self.conversation.set_first_response_if_needed()


class QuickReply(models.Model):
    """Pre-written responses for admins."""
    
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quick_replies', limit_choices_to={'is_staff': True})
    title = models.CharField(max_length=100)
    message = models.TextField()
    category = models.CharField(max_length=50, default='general')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'title']
        verbose_name_plural = 'Quick Replies'
    
    def __str__(self):
        return f"{self.title} ({self.admin.username})"


class ConversationTag(models.Model):
    """Tags for organizing conversations."""
    
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#425ed8', help_text="Hex color code")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class TypingIndicator(models.Model):
    """Real-time typing status."""
    
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name='typing_indicator')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_typing = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['conversation']),
        ]
    
    def __str__(self):
        return f"{self.user.username} in {self.conversation}"
