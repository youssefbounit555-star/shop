import json

from django.test import TestCase
from django.urls import reverse

from .models import Product


class AgentsHubTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name='Test Smart Watch',
            short_description='Premium test watch for agents',
            description='Durable and stylish watch for daily use.',
            price=199.99,
            discount_price=149.99,
            stock_quantity=12,
            category='Watch',
            brand='Elegant',
            tags='watch,smart,fitness',
            featured=True,
            is_active=True,
            status='active',
            sku='WATCH-TEST-001',
        )

    def test_agents_page_loads(self):
        response = self.client.get(reverse('store:agents_hub'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI AGENTS LAB')

    def test_ai_agent_chat_api_returns_reply(self):
        payload = {
            'agent_id': 'shop_strategist',
            'message': 'I need a stylish watch under 200 dollars',
        }
        response = self.client.post(
            reverse('store:ai_agent_chat'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertIn('reply', data)
        self.assertGreaterEqual(len(data['recommendations']), 1)

    def test_ai_agent_chat_stores_conversation_history_in_session(self):
        first_payload = {
            'agent_id': 'shop_strategist',
            'message': 'I need a practical watch for work',
        }
        second_payload = {
            'agent_id': 'shop_strategist',
            'message': 'My budget is 180 and I prefer black color',
        }

        first_response = self.client.post(
            reverse('store:ai_agent_chat'),
            data=json.dumps(first_payload),
            content_type='application/json',
        )
        second_response = self.client.post(
            reverse('store:ai_agent_chat'),
            data=json.dumps(second_payload),
            content_type='application/json',
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)

        session = self.client.session
        history_map = session.get('ai_agent_history_by_agent')
        self.assertIsInstance(history_map, dict)
        self.assertIn('shop_strategist', history_map)

        history = history_map['shop_strategist']
        self.assertGreaterEqual(len(history), 4)
        self.assertEqual(history[-2]['role'], 'user')
        self.assertEqual(history[-1]['role'], 'assistant')
        self.assertIn('budget is 180', history[-2]['content'])

    def test_ai_agent_chat_blocks_out_of_scope_questions(self):
        payload = {
            'agent_id': 'shop_strategist',
            'message': 'Who won the world cup in 2010?',
        }
        response = self.client.post(
            reverse('store:ai_agent_chat'),
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertIn('ElegantShop services only', data['reply'])

    def test_ai_agent_chat_allows_short_followup_with_store_context(self):
        first_payload = {
            'agent_id': 'shop_strategist',
            'message': 'I want a watch under 200 with good battery',
        }
        second_payload = {
            'agent_id': 'shop_strategist',
            'message': 'What about this one?',
        }

        first_response = self.client.post(
            reverse('store:ai_agent_chat'),
            data=json.dumps(first_payload),
            content_type='application/json',
        )
        second_response = self.client.post(
            reverse('store:ai_agent_chat'),
            data=json.dumps(second_payload),
            content_type='application/json',
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)

        data = second_response.json()
        self.assertTrue(data['ok'])
        self.assertNotIn('ElegantShop services only', data['reply'])
