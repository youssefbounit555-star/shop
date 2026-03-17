from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, View, TemplateView
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db.models import Q, Count
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Conversation, Message

MAX_CHAT_UPLOAD_MB = 25
MAX_CHAT_UPLOAD_BYTES = MAX_CHAT_UPLOAD_MB * 1024 * 1024
ALLOWED_FILE_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp',
    'mp4', 'mov', 'avi', 'mkv', 'webm',
}
ALLOWED_AUDIO_EXTENSIONS = {'webm', 'mp3', 'wav', 'ogg', 'm4a', 'aac'}

def get_default_admin():
    """Get the default admin user (store manager)."""
    return User.objects.filter(is_staff=True, is_superuser=True).first() or User.objects.filter(is_staff=True).first()


def _get_file_extension(uploaded) -> str:
    if not uploaded:
        return ''
    name = (uploaded.name or '').lower()
    if '.' not in name:
        return ''
    return name.rsplit('.', 1)[-1]


def _serialize_message(message: Message) -> dict:
    return {
        'id': message.id,
        'sender': message.sender.username,
        'sender_id': message.sender.id,
        'text': message.text,
        'file_url': message.file.url if message.file else None,
        'file_type': message.get_file_type() if message.file else None,
        'file_name': message.file.name.split('/')[-1] if message.file else None,
        'audio_url': message.audio.url if message.audio else None,
        'created_at': message.created_at.isoformat(),
        'created_label': message.created_at.strftime('%H:%M'),
        'is_read': message.is_read,
        'sender_is_admin': message.sender.is_staff,
    }


def _validate_message_uploads(file, audio) -> str | None:
    if file:
        if file.size > MAX_CHAT_UPLOAD_BYTES:
            return f"File is too large. Maximum size is {MAX_CHAT_UPLOAD_MB}MB."
        ext = _get_file_extension(file)
        if ext not in ALLOWED_FILE_EXTENSIONS:
            return "Only image or video files are allowed."

    if audio:
        if audio.size > MAX_CHAT_UPLOAD_BYTES:
            return f"Audio is too large. Maximum size is {MAX_CHAT_UPLOAD_MB}MB."
        ext = _get_file_extension(audio)
        if ext and ext not in ALLOWED_AUDIO_EXTENSIONS:
            return "Unsupported audio format."

    return None


def _resolve_admin_conversation(admin_user, conv_id: str | int):
    conversation = get_object_or_404(Conversation, id=conv_id)
    if admin_user.is_superuser:
        return conversation
    if conversation.admin_id and conversation.admin_id != admin_user.id:
        raise PermissionDenied("Conversation assigned to another admin.")
    if conversation.admin is None:
        conversation.admin = admin_user
        conversation.save(update_fields=['admin'])
    return conversation


class ChatView(LoginRequiredMixin, TemplateView):
    """User chat view - chat with admin."""
    template_name = 'store/chat.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get or create conversation
        conversation, created = Conversation.objects.get_or_create(
            user=self.request.user,
            defaults={'admin': get_default_admin()}
        )
        
        # Mark messages as read
        conversation.mark_as_read_for(self.request.user)
        
        # Get all messages
        messages = conversation.message_set.all()
        
        context['conversation'] = conversation
        context['messages'] = messages
        context['initial_messages'] = [_serialize_message(msg) for msg in messages]
        context['is_admin'] = False
        
        return context


class AdminChatListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Admin view - see all user conversations."""
    template_name = 'admin/chat/list.html'
    context_object_name = 'conversations'
    paginate_by = 20
    
    def test_func(self):
        """Only admins/staff can access."""
        return self.request.user.is_staff
    
    def get_queryset(self):
        """Get conversations assigned to this admin."""
        qs = Conversation.objects.annotate(unread_count=Count('message', filter=Q(message__is_read=False) & ~Q(message__sender=self.request.user)))
        if not self.request.user.is_superuser:
            qs = qs.filter(admin=self.request.user)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get total unread count from annotated field
        context['total_unread'] = sum(conv.unread_count or 0 for conv in self.get_queryset())
        return context


class AdminChatDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Admin view - chat with specific user."""
    model = Conversation
    template_name = 'admin/chat/detail.html'
    context_object_name = 'conversation'
    
    def test_func(self):
        """Only admins/staff can access."""
        if not self.request.user.is_staff:
            return False
        if self.request.user.is_superuser:
            return True
        conversation = self.get_object()
        return conversation.admin_id in (None, self.request.user.id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = self.get_object()
        if conversation.admin is None and self.request.user.is_staff:
            conversation.admin = self.request.user
            conversation.save(update_fields=['admin'])
        
        # Mark as read for admin
        conversation.mark_as_read_for(self.request.user)
        
        context['messages'] = conversation.message_set.all()
        context['initial_messages'] = [_serialize_message(msg) for msg in context['messages']]
        context['is_admin'] = True
        
        return context


@login_required
@require_http_methods(["POST"])
def send_message(request):
    """AJAX endpoint to send a message."""
    
    # Get or create conversation
    if request.user.is_staff:
        # Admin sending message - get conversation by ID
        conv_id = request.POST.get('conversation_id')
        if not conv_id:
            return JsonResponse({'error': 'conversation_id is required for admin messages.'}, status=400)

        try:
            conversation = _resolve_admin_conversation(request.user, conv_id)
        except PermissionDenied:
            return JsonResponse({'error': 'Not authorized for this conversation.'}, status=403)
    else:
        # Regular user sending message - get or create conversation
        conversation, _ = Conversation.objects.get_or_create(
            user=request.user,
            defaults={'admin': get_default_admin()}
        )
    
    text = request.POST.get('text', '').strip()
    file = request.FILES.get('file')
    audio = request.FILES.get('audio')
    
    if not text and not file and not audio:
        return JsonResponse({'error': 'Message is empty'}, status=400)

    validation_error = _validate_message_uploads(file, audio)
    if validation_error:
        return JsonResponse({'error': validation_error}, status=400)

    if len(text) > 4000:
        return JsonResponse({'error': 'Message is too long. Maximum length is 4000 characters.'}, status=400)
    
    # Create message
    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        text=text,
        file=file,
        audio=audio
    )

    # Keep conversation ordering fresh
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=['updated_at'])
    
    # Return message data
    return JsonResponse(_serialize_message(message))


@login_required
def load_messages(request):
    """AJAX endpoint to load messages (for long polling)."""
    
    # Get or create conversation
    if request.user.is_staff:
        # Admin loading messages - get conversation by ID
        conv_id = request.GET.get('conversation_id')
        if not conv_id:
            return JsonResponse({'error': 'conversation_id is required.'}, status=400)
        try:
            conversation = _resolve_admin_conversation(request.user, conv_id)
        except PermissionDenied:
            return JsonResponse({'error': 'Not authorized for this conversation.'}, status=403)
    else:
        # Regular user loading messages - get or create conversation
        conversation, _ = Conversation.objects.get_or_create(
            user=request.user,
            defaults={'admin': get_default_admin()}
        )
    
    # Get messages since last check
    try:
        last_message_id = int(request.GET.get('last_message_id', 0))
    except (TypeError, ValueError):
        last_message_id = 0
    messages = conversation.message_set.filter(id__gt=last_message_id).order_by('created_at')

    # Mark incoming unread messages as read in bulk
    conversation.message_set.filter(
        id__gt=last_message_id
    ).exclude(
        sender=request.user
    ).filter(
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    # Return messages
    return JsonResponse({
        'messages': [_serialize_message(msg) for msg in messages],
        'conversation_id': conversation.id
    })


@login_required
def get_unread_count(request):
    """AJAX endpoint to get unread message count."""
    
    if request.user.is_staff:
        # Admin - count messages from all their conversations
        count = Message.objects.filter(
            conversation__admin=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
    else:
        # User - count messages from their conversation
        conversation, _ = Conversation.objects.get_or_create(
            user=request.user,
            defaults={'admin': User.objects.filter(is_staff=True).first()}
        )
        count = conversation.get_unread_count(request.user)
    
    return JsonResponse({'unread_count': count})


@login_required
@require_http_methods(["POST"])
def update_typing_status(request):
    """Update user typing status."""
    from .models import TypingIndicator
    
    is_typing = request.POST.get('is_typing', 'false').lower() == 'true'
    
    if request.user.is_staff:
        conv_id = request.POST.get('conversation_id')
        if not conv_id:
            return JsonResponse({'error': 'conversation_id is required.'}, status=400)
        try:
            conversation = _resolve_admin_conversation(request.user, conv_id)
        except PermissionDenied:
            return JsonResponse({'error': 'Not authorized for this conversation.'}, status=403)
    else:
        conversation, _ = Conversation.objects.get_or_create(
            user=request.user,
            defaults={'admin': User.objects.filter(is_staff=True).first()}
        )
    
    typing_indicator, _ = TypingIndicator.objects.get_or_create(
        conversation=conversation
    )
    typing_indicator.user = request.user
    typing_indicator.is_typing = is_typing
    typing_indicator.save()
    
    return JsonResponse({
        'success': True,
        'is_typing': is_typing
    })


@login_required
def get_typing_status(request):
    """Get typing status for a conversation."""
    from .models import TypingIndicator
    from django.utils import timezone
    from datetime import timedelta
    
    if request.user.is_staff:
        conv_id = request.GET.get('conversation_id')
        if not conv_id:
            return JsonResponse({'error': 'conversation_id is required.'}, status=400)
        try:
            conversation = _resolve_admin_conversation(request.user, conv_id)
        except PermissionDenied:
            return JsonResponse({'error': 'Not authorized for this conversation.'}, status=403)
    else:
        conversation, _ = Conversation.objects.get_or_create(
            user=request.user,
            defaults={'admin': User.objects.filter(is_staff=True).first()}
        )
    
    try:
        typing = TypingIndicator.objects.get(conversation=conversation)
        # Reset typing if it hasn't been updated in 10 seconds
        if typing.updated_at < timezone.now() - timedelta(seconds=10):
            typing.is_typing = False
        return JsonResponse({
            'is_typing': typing.is_typing and typing.user != request.user,
            'user_name': typing.user.get_full_name() or typing.user.username
        })
    except TypingIndicator.DoesNotExist:
        return JsonResponse({'is_typing': False})


@login_required
def get_quick_replies(request):
    """Get quick replies for current admin."""
    from .models import QuickReply
    
    if not request.user.is_staff:
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    category = request.GET.get('category', 'general')
    replies = QuickReply.objects.filter(
        admin=request.user,
        is_active=True,
        category=category
    )
    
    return JsonResponse({
        'replies': [
            {
                'id': r.id,
                'title': r.title,
                'message': r.message
            }
            for r in replies
        ]
    })


@login_required
@require_http_methods(["POST"])
def search_messages(request):
    """Search messages in a conversation."""
    search_term = request.POST.get('q', '').strip()
    
    if request.user.is_staff:
        conv_id = request.POST.get('conversation_id')
        if not conv_id:
            return JsonResponse({'error': 'conversation_id is required.'}, status=400)
        try:
            conversation = _resolve_admin_conversation(request.user, conv_id)
        except PermissionDenied:
            return JsonResponse({'error': 'Not authorized for this conversation.'}, status=403)
    else:
        conversation, _ = Conversation.objects.get_or_create(
            user=request.user,
            defaults={'admin': User.objects.filter(is_staff=True).first()}
        )
    
    if not search_term:
        return JsonResponse({'messages': []})
    
    messages = conversation.message_set.filter(text__icontains=search_term)
    
    return JsonResponse({
        'messages': [{
            'id': msg.id,
            'sender': msg.sender.username,
            'text': msg.text,
            'created_at': msg.created_at.isoformat(),
            'sender_is_admin': msg.sender.is_staff
        } for msg in messages]
    })


@login_required
@require_http_methods(["POST"])
def pin_message(request):
    """Pin or unpin a message."""
    msg_id = request.POST.get('message_id')
    message = get_object_or_404(Message, id=msg_id)
    
    # Check access
    if request.user != message.sender and not (request.user.is_staff and message.conversation.admin == request.user):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    message.is_pinned = not message.is_pinned
    message.save(update_fields=['is_pinned'])
    
    return JsonResponse({
        'success': True,
        'is_pinned': message.is_pinned
    })


@login_required
@require_http_methods(["POST"])
def update_conversation_status(request):
    """Update conversation status (admin only)."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    conv_id = request.POST.get('conversation_id')
    status = request.POST.get('status')
    priority = request.POST.get('priority')
    tags = request.POST.get('tags', '')
    
    conversation = get_object_or_404(Conversation, id=conv_id, admin=request.user)
    
    if status and status in dict(Conversation.STATUS_CHOICES):
        conversation.status = status
    if priority and priority in dict(Conversation.PRIORITY_CHOICES):
        conversation.priority = priority
    if tags is not None:
        conversation.tags = tags
    
    conversation.save()
    
    return JsonResponse({
        'success': True,
        'status': conversation.get_status_display(),
        'priority': conversation.get_priority_display()
    })

