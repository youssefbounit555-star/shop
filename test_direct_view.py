#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client, RequestFactory
from django.middleware.csrf import CsrfViewMiddleware
from chat.models import Conversation, Message
from chat import views

print("=" * 60)
print("DIRECT VIEW TEST")
print("=" * 60)

# Create or get test users
admin_user, _ = User.objects.get_or_create(
    username='view_test_admin',
    defaults={
        'password': 'pass',
        'is_staff': True,
        'is_superuser': True
    }
)
admin_user.set_password('pass')
admin_user.save()

regular_user, _ = User.objects.get_or_create(
    username='view_test_user',
    defaults={'password': 'pass'}
)
regular_user.set_password('pass')
regular_user.save()

print(f"\n✓ Admin: {admin_user.username} (id={admin_user.id})")
print(f"✓ User: {regular_user.username} (id={regular_user.id})")

# Clear old data
Message.objects.filter(sender__in=[admin_user, regular_user]).delete()
Conversation.objects.filter(user=regular_user).delete()

# Create a request factory
factory = RequestFactory()

print("\n" + "=" * 60)
print("TEST 1: GET /chat/ (Create Conversation)")
print("=" * 60)

# Create GET request for ChatView
request = factory.get('/chat/')
request.user = regular_user

# Call view
chat_view = views.ChatView.as_view()
response = chat_view(request)

print(f"✓ Response status: {response.status_code}")

# Check if conversation was created
convs = Conversation.objects.filter(user=regular_user)
print(f"✓ Conversation created: {convs.exists()}")
if convs.exists():
    conv = convs.first()
    print(f"  - ID: {conv.id}")
    print(f"  - Admin: {conv.admin.username if conv.admin else 'None'}")

print("\n" + "=" * 60)
print("TEST 2: POST /chat/api/send/ (Send Message)")
print("=" * 60)

# Create POST request for send_message
post_request = factory.post('/chat/api/send/', {
    'text': 'Hello from direct view test!',
    'conversation_id': str(convs.first().id) if convs.exists() else '',
})
post_request.user = regular_user

# Add CSRF token
post_request.META['CSRF_COOKIE'] = 'dummy_token'

# Call view
try:
    response = views.send_message(post_request)
    print(f"✓ Response status: {response.status_code}")
    
    import json
    resp_data = json.loads(response.content)
    print(f"✓ Response JSON: {resp_data}")
    
    if 'error' not in resp_data:
        print(f"✓ Message sent successfully!")
        print(f"  - Message ID: {resp_data.get('id')}")
        print(f"  - Text: {resp_data.get('text')}")
except Exception as e:
    print(f"✗ Error: {str(e)}")

print("\n" + "=" * 60)
print("FINAL DATABASE STATE")
print("=" * 60)

msgs = Message.objects.all()
convs = Conversation.objects.all()

print(f"\n✓ Total conversations: {convs.count()}")
print(f"✓ Total messages: {msgs.count()}")

for msg in msgs:
    conv = msg.conversation
    print(f"\n  Message ID: {msg.id}")
    print(f"  From: {msg.sender.username}")
    print(f"  Text: '{msg.text}'")
    print(f"  Conversation: {conv.user.username} ↔ {conv.admin.username if conv.admin else 'None'}")

print("\n" + "=" * 60)
print("END TEST")
print("=" * 60)
