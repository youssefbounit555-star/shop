from django.test import TestCase
from django.contrib.auth.models import User
from .models import Conversation, Message, MessageAttachment, VoiceMessage, MessageReaction, UserStatus

class ConversationModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
    
    def test_create_conversation(self):
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)
        self.assertEqual(conversation.participants.count(), 2)
    
    def test_get_other_user(self):
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)
        other = conversation.get_other_user(self.user1)
        self.assertEqual(other, self.user2)

class MessageModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)
    
    def test_create_message(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            receiver=self.user2,
            content='Test message'
        )
        self.assertEqual(message.content, 'Test message')
        self.assertEqual(message.status, 'sent')
        self.assertFalse(message.is_read)

class UserStatusTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', password='pass123')
    
    def test_create_user_status(self):
        status = UserStatus.objects.create(user=self.user, is_online=True)
        self.assertTrue(status.is_online)
