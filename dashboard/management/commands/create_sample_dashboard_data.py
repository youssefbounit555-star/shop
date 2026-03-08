#!/usr/bin/env python

"""
Management command to create sample dashboard data for testing.
Usage: python manage.py create_sample_dashboard_data

This command creates:
- Sample goals for testing
- Sample messages between users
- Sample orders

WARNING: This will create test data in your database.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from user.models import UserProfile
from dashboard.models import Goal, Message, Order
import random
from datetime import timedelta


class Command(BaseCommand):
    help = 'Create sample dashboard data for testing'

    def handle(self, *args, **options):
        # Get all users
        users = list(UserProfile.objects.all())
        
        if len(users) < 2:
            self.stdout.write(
                self.style.ERROR('Need at least 2 users to create sample data.')
            )
            return
        
        # Create sample goals
        self.stdout.write('Creating sample goals...')
        current_user = users[0]
        goals_titles = [
            'Complete Django project',
            'Learn TypeScript',
            'Exercise 30 minutes daily',
            'Read 2 books a month',
            'Improve CSS skills',
            'Master REST APIs',
            'Build portfolio website',
            'Learn Docker',
        ]
        
        for i, title in enumerate(goals_titles):
            goal = Goal.objects.create(
                user=current_user,
                title=title,
                description=f'Sample goal description for {title}',
                completed=i % 3 == 0,  # Make every 3rd goal completed
            )
            self.stdout.write(f'  ✓ Created goal: {title}')
        
        # Create sample messages
        self.stdout.write('Creating sample messages...')
        sender = users[0]
        receiver = users[1]
        
        messages_text = [
            'Hey, how are you doing?',
            'I\'m doing great! How about you?',
            'Did you check the new project updates?',
            'Yes, looks amazing!',
            'Let\'s discuss it over coffee',
            'Sounds good to me!',
            'Thanks for the help yesterday',
            'Happy to help anytime',
        ]
        
        now = timezone.now()
        for i, msg_text in enumerate(messages_text):
            message = Message.objects.create(
                sender=sender if i % 2 == 0 else receiver,
                receiver=receiver if i % 2 == 0 else sender,
                message=msg_text,
                timestamp=now - timedelta(hours=len(messages_text) - i),
                read=True if i < len(messages_text) - 2 else False,
            )
            self.stdout.write(f'  ✓ Created message: {msg_text[:30]}...')
        
        # Create sample orders
        self.stdout.write('Creating sample orders...')
        status_choices = ['pending', 'completed', 'cancelled']
        products = [
            'Classic Blue Notebook',
            'Wireless Bluetooth Headphones',
            'Stainless Steel Water Bottle',
            'USB-C Charging Cable',
            'Premium Coffee Maker',
            'Yoga Mat Pro',
            'Desktop Monitor Stand',
            'Mechanical Keyboard RGB',
            'Phone Ring Stand',
            'Portable Phone Charger',
        ]
        
        now = timezone.now()
        for i, product in enumerate(products):
            order = Order.objects.create(
                user=current_user,
                order_id=f'ORD-{2024}{i+1:04d}',
                product=product,
                status=status_choices[i % 3],
                price=round(random.uniform(10, 200), 2),
                description=f'Sample order for {product}',
                date=now - timedelta(days=random.randint(1, 30))
            )
            self.stdout.write(f'  ✓ Created order: {product}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully created sample dashboard data!'
            )
        )
        self.stdout.write('  - Goals: 8')
        self.stdout.write('  - Messages: 8')
        self.stdout.write('  - Orders: 10')
