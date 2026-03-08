#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

# Delete old test users
User.objects.filter(username__startswith='test_').delete()

# Create test users
admin = User.objects.create_user(
    username='test_admin',
    password='testpass123',
    is_staff=True,
    is_superuser=True
)

user = User.objects.create_user(
    username='test_user',
    password='testpass123',
)

print("=" * 60)
print("TEST USERS CREATED")
print("=" * 60)
print(f"\nAdmin User:")
print(f"  Username: {admin.username}")
print(f"  Password: testpass123")
print(f"  ID: {admin.id}")

print(f"\nRegular User:")
print(f"  Username: {user.username}")
print(f"  Password: testpass123")
print(f"  ID: {user.id}")

# Now test login
from django.test import Client

client = Client()
result = client.login(username='test_user', password='testpass123')
print(f"\nLogin Test: {'✓ SUCCESS' if result else '✗ FAILED'}")

# Now test API
if result:
    print("\n" + "=" * 60)
    print("TESTING CHAT API")
    print("=" * 60)
    
    from chat.models import Conversation, Message
    
    # Clear database
    Message.objects.all().delete()
    Conversation.objects.all().delete()
    
    # Test GET /chat/ first to create conversation
    response = client.get('/chat/')
    print(f"\n✓ GET /chat/ status: {response.status_code}")
    
    # Test POST send_message
    response = client.post('/chat/api/send/', {
        'text': 'Hello from test user!',
    })
    
    print(f"✓ POST /chat/api/send/ status: {response.status_code}")
    
    try:
        import json
        resp_json = response.json()
        print(f"✓ Response: {json.dumps(resp_json, indent=2)}")
    except Exception as e:
        print(f"✓ Response error: {str(e)}")
        print(f"✓ Response content: {response.content.decode()[:300]}")
    
    # Check database
    print("\n" + "=" * 60)
    print("FINAL DATABASE STATE")
    print("=" * 60)
    
    convs = Conversation.objects.all()
    msgs = Message.objects.all()
    
    print(f"\n✓ Conversations: {convs.count()}")
    for conv in convs:
        print(f"  - {conv.user.username} ↔ {conv.admin.username if conv.admin else 'None'}")
    
    print(f"\n✓ Messages: {msgs.count()}")
    for msg in msgs:
        print(f"  - From: {msg.sender.username}")
        print(f"    Text: '{msg.text}'")
        print(f"    Conv: {msg.conversation.id}")
