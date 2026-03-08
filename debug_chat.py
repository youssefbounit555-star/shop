#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from chat.models import Conversation, Message

print("=" * 60)
print("CHAT SYSTEM DEBUG")
print("=" * 60)

# Check admin users
admins = User.objects.filter(is_staff=True)
print(f"\n✓ Admin users: {admins.count()}")
for admin in admins:
    print(f"  - {admin.username} (id={admin.id})")

if admins.count() == 0:
    print("  ⚠️  WARNING: No admin users found!")

# Check all users
all_users = User.objects.all()
print(f"\n✓ All users: {all_users.count()}")
for user in all_users:
    print(f"  - {user.username} (staff={user.is_staff}, id={user.id})")

# Check conversations
convs = Conversation.objects.all()
print(f"\n✓ Total conversations: {convs.count()}")
for conv in convs:
    admin_name = conv.admin.username if conv.admin else "None"
    msg_count = conv.message_set.count()
    print(f"  - User: {conv.user.username} ↔ Admin: {admin_name} | Messages: {msg_count} (id={conv.id})")

# Check messages
msgs = Message.objects.all()
print(f"\n✓ Total messages: {msgs.count()}")
for msg in msgs[:5]:  # First 5
    print(f"  - {msg.sender.username}: {msg.text[:30]}... (conv_id={msg.conversation_id})")

print("\n" + "=" * 60)
print("END DEBUG")
print("=" * 60)
