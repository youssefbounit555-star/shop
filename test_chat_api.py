#!/usr/bin/env python
import os
import django
import json
from io import BytesIO

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from chat.models import Conversation, Message

print("=" * 60)
print("TESTING CHAT API")
print("=" * 60)

# Get test user
test_user = User.objects.get(username='naroman')
print(f"\n✓ Test user: {test_user.username} (id={test_user.id})")

# Create client and login
client = Client()
logged_in = client.login(username='naroman', password='123')
print(f"✓ Logged in: {logged_in}")

# Get CSRF token
response = client.get('/chat/')
csrf_token = response.wsgi_request.META.get('CSRF_COOKIE', 'NOT_FOUND')
print(f"✓ CSRF token obtained: {csrf_token[:20] if len(csrf_token) > 20 else csrf_token}...")

# Try to send a message
print("\n" + "-" * 60)
print("SENDING TEST MESSAGE")
print("-" * 60)

data = {
    'text': 'Hello, this is a test message!',
    'conversation_id': '',  # Will be empty, conversation should be created
}

# Get the send message endpoint
send_url = reverse('chat:send_message')
print(f"✓ Endpoint URL: {send_url}")

# Send POST request
response = client.post(send_url, data=data, HTTP_X_CSRFTOKEN=csrf_token)
print(f"✓ Response status: {response.status_code}")
print(f"✓ Response content-type: {response.get('Content-Type', 'NOT_SET')}")

# Parse response
try:
    response_data = response.json()
    print(f"✓ Response JSON: {json.dumps(response_data, indent=2)}")
except:
    print(f"✓ Response text: {response.content.decode()}")

# Check database
print("\n" + "-" * 60)
print("DATABASE STATE AFTER SEND")
print("-" * 60)

convs = Conversation.objects.all()
print(f"✓ Total conversations: {convs.count()}")
for conv in convs:
    print(f"  - {conv.user.username} ↔ {conv.admin.username if conv.admin else 'None'} (id={conv.id})")

msgs = Message.objects.all()
print(f"✓ Total messages: {msgs.count()}")
for msg in msgs:
    print(f"  - {msg.sender.username}: {msg.text}")

print("\n" + "=" * 60)
print("END TEST")
print("=" * 60)
