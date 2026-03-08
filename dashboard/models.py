from django.db import models
from django.contrib.auth.models import User
from user.models import UserProfile


class Goal(models.Model):
    """
    User's personal goals/todo items in the dashboard.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Goal'
        verbose_name_plural = 'Goals'

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class Message(models.Model):
    """
    Direct messages between users.
    """
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username}"
