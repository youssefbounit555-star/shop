import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Conversation, Message, MessageReaction, UserStatus
from datetime import datetime

class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat."""
    
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.user = self.scope['user']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        # Update user status
        await self.update_user_status(True)
        
        # Notify others user is online
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status_change',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_online': True,
            }
        )
    
    async def disconnect(self, close_code):
        # Update user status
        await self.update_user_status(False)
        
        # Notify others user went offline
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status_change',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_online': False,
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'chat_message':
            await self.handle_chat_message(data)
        elif message_type == 'typing':
            await self.handle_typing(data)
        elif message_type == 'read_message':
            await self.handle_read_message(data)
        elif message_type == 'reaction':
            await self.handle_reaction(data)
        elif message_type == 'edit_message':
            await self.handle_edit_message(data)
        elif message_type == 'delete_message':
            await self.handle_delete_message(data)
    
    async def handle_chat_message(self, data):
        """Handle incoming chat message."""
        content = data.get('message', '')
        receiver_id = data.get('receiver_id')
        
        # Save message to database
        message = await self.save_message(content, receiver_id)
        
        # Broadcast to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message.id,
                'sender_id': self.user.id,
                'sender_username': self.user.username,
                'receiver_id': receiver_id,
                'content': content,
                'timestamp': message.created_at.isoformat(),
                'status': 'delivered',
            }
        )
    
    async def handle_typing(self, data):
        """Handle typing indicator."""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing,
            }
        )
    
    async def handle_read_message(self, data):
        """Mark message as read."""
        message_id = data.get('message_id')
        await self.mark_message_read(message_id)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_read',
                'message_id': message_id,
                'read_by': self.user.id,
            }
        )
    
    async def handle_reaction(self, data):
        """Handle emoji reaction."""
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        action = data.get('action', 'add')  # add or remove
        
        await self.update_reaction(message_id, emoji, action)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_reaction',
                'message_id': message_id,
                'user_id': self.user.id,
                'username': self.user.username,
                'emoji': emoji,
                'action': action,
            }
        )
    
    async def handle_edit_message(self, data):
        """Handle message edit."""
        message_id = data.get('message_id')
        new_content = data.get('content')
        
        await self.edit_message(message_id, new_content)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_edited',
                'message_id': message_id,
                'new_content': new_content,
                'edited_by': self.user.id,
            }
        )
    
    async def handle_delete_message(self, data):
        """Handle message delete."""
        message_id = data.get('message_id')
        delete_for = data.get('delete_for', 'me')  # me or everyone
        
        if delete_for == 'everyone':
            await self.delete_message(message_id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id,
                    'deleted_for': 'everyone',
                }
            )
        else:
            # Hide message only for this user (archive it)
            pass
    
    # Event handlers
    async def chat_message(self, event):
        """Send message to WebSocket."""
        await self.send(text_data=json.dumps(event))
    
    async def typing_indicator(self, event):
        """Send typing indicator."""
        await self.send(text_data=json.dumps(event))
    
    async def message_read(self, event):
        """Send read receipt."""
        await self.send(text_data=json.dumps(event))
    
    async def message_reaction(self, event):
        """Send reaction update."""
        await self.send(text_data=json.dumps(event))
    
    async def message_edited(self, event):
        """Send edited message."""
        await self.send(text_data=json.dumps(event))
    
    async def message_deleted(self, event):
        """Send deleted message."""
        await self.send(text_data=json.dumps(event))
    
    async def user_status_change(self, event):
        """Send user status change."""
        await self.send(text_data=json.dumps(event))
    
    # Database operations
    @database_sync_to_async
    def save_message(self, content, receiver_id):
        """Save message to database."""
        receiver = User.objects.get(id=receiver_id)
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            receiver=receiver,
            content=content,
            status='delivered'
        )
        return message
    
    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Mark message as read."""
        Message.objects.filter(id=message_id).update(is_read=True, status='read')
    
    @database_sync_to_async
    def update_reaction(self, message_id, emoji, action):
        """Add or remove emoji reaction."""
        message = Message.objects.get(id=message_id)
        if action == 'add':
            MessageReaction.objects.get_or_create(
                message=message,
                user=self.user,
                emoji=emoji
            )
        else:
            MessageReaction.objects.filter(
                message=message,
                user=self.user,
                emoji=emoji
            ).delete()
    
    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        """Edit message content."""
        Message.objects.filter(id=message_id).update(
            content=new_content,
            is_edited=True,
            edited_at=datetime.now()
        )
    
    @database_sync_to_async
    def delete_message(self, message_id):
        """Delete message."""
        Message.objects.filter(id=message_id).delete()
    
    @database_sync_to_async
    def update_user_status(self, is_online):
        """Update user online status."""
        status, created = UserStatus.objects.get_or_create(user=self.user)
        status.is_online = is_online
        status.save()
