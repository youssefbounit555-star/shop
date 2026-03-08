#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from chat.models import Conversation, Message

print("=" * 60)
print("TEST CHAT MESSAGE SENDING")
print("=" * 60)

# Get users
user = User.objects.get(username='naroman')
admin = User.objects.get(username='octinz')

print(f"\n✓ User: {user.username} (id={user.id})")
print(f"✓ Admin: {admin.username} (id={admin.id})")

# Create conversation manually
print("\n" + "-" * 60)
print("CREATING CONVERSATION MANUALLY")
print("-" * 60)

conversation, created = Conversation.objects.get_or_create(
    user=user,
    defaults={'admin': admin}
)
print(f"✓ Conversation: {conversation} (created={created}, id={conversation.id})")

# Create message manually
print("\n" + "-" * 60)
print("CREATING MESSAGE MANUALLY")
print("-" * 60)

message = Message.objects.create(
    conversation=conversation,
    sender=user,
    text="This is a test message from naroman"
)
print(f"✓ Message created: id={message.id}, text='{message.text}'")

# Check database
print("\n" + "-" * 60)
print("DATABASE STATE")
print("-" * 60)

convs = Conversation.objects.all()
print(f"✓ Total conversations: {convs.count()}")
for conv in convs:
    msg_count = conv.message_set.count()
    print(f"  - {conv.user.username} ↔ {conv.admin.username} | Messages: {msg_count}")

msgs = Message.objects.all()
print(f"✓ Total messages: {msgs.count()}")
for msg in msgs:
    print(f"  - {msg.sender.username}: '{msg.text[:40]}...'")

# Now test the API with client
print("\n" + "-" * 60)
print("TESTING API ENDPOINT")
print("-" * 60)

# Delete messages and conversations for clean test
Message.objects.all().delete()
Conversation.objects.all().delete()
print("✓ Cleaned up database")

# Now test with client
client = Client()
login_success = client.login(username='naroman', password='123')
print(f"✓ Login: {login_success}")

if login_success:
    # Get conversation ID through ChatView first
    response = client.get('/chat/')
    print(f"✓ GET /chat/ status: {response.status_code}")
    
    # Now try to send message using the API
    response = client.post('/chat/api/send/', {
        'text': 'Test message from API',
        'conversation_id': '1'  # Will try 1, but should use get_or_create
    })
    
    print(f"✓ POST /chat/api/send/ status: {response.status_code}")
    print(f"✓ Response content-type: {response.get('Content-Type', 'NOT_SET')}")
    
    try:
        import json
        resp_json = response.json()
        print(f"✓ Response JSON: {resp_json}")
    except:
        print(f"✓ Response: {response.content.decode()[:200]}")
    
    # Check if message was created
    print("\n" + "-" * 60)
    print("FINAL DATABASE STATE")
    print("-" * 60)
    
    convs = Conversation.objects.all()
    msgs = Message.objects.all()
    
    print(f"✓ Conversations: {convs.count()}")
    print(f"✓ Messages: {msgs.count()}")
    
    for msg in msgs:
        print(f"  - {msg.sender.username}: '{msg.text}'")

print("\n" + "=" * 60)
print("END TEST")
print("=" * 60)
