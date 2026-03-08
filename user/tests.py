from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User

from .views import LOGIN_VERIFICATION_SESSION_KEY


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class LoginEmailVerificationTests(TestCase):
    def setUp(self):
        self.password = 'StrongPass123!'
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password=self.password,
        )
        self.user_without_email = User.objects.create_user(
            username='noemailuser',
            email='',
            password=self.password,
        )

    def test_login_sends_email_code_and_redirects_to_verify(self):
        response = self.client.post(reverse('user:login'), {
            'username': self.user.username,
            'password': self.password,
        })

        self.assertRedirects(response, reverse('user:login_verify'))

        session = self.client.session
        pending = session.get(LOGIN_VERIFICATION_SESSION_KEY)
        self.assertIsInstance(pending, dict)
        self.assertEqual(pending.get('user_id'), self.user.id)
        self.assertEqual(pending.get('email'), self.user.email)
        self.assertNotIn('_auth_user_id', session)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('verification code', mail.outbox[0].subject.lower())

    def test_verify_code_completes_login(self):
        self.client.post(reverse('user:login'), {
            'username': self.user.username,
            'password': self.password,
        })

        session = self.client.session
        pending = session.get(LOGIN_VERIFICATION_SESSION_KEY)
        code = pending.get('code')

        response = self.client.post(reverse('user:login_verify'), {
            'verification_code': code,
        })

        self.assertRedirects(response, reverse('store:home'))
        session = self.client.session
        self.assertEqual(session.get('_auth_user_id'), str(self.user.id))
        self.assertIsNone(session.get(LOGIN_VERIFICATION_SESSION_KEY))

    def test_invalid_code_does_not_login_user(self):
        self.client.post(reverse('user:login'), {
            'username': self.user.username,
            'password': self.password,
        })

        response = self.client.post(reverse('user:login_verify'), {
            'verification_code': '000000',
        })

        self.assertEqual(response.status_code, 200)
        session = self.client.session
        pending = session.get(LOGIN_VERIFICATION_SESSION_KEY)
        self.assertIsInstance(pending, dict)
        self.assertEqual(pending.get('attempts'), 1)
        self.assertNotIn('_auth_user_id', session)

    def test_login_is_blocked_when_account_has_no_email(self):
        response = self.client.post(reverse('user:login'), {
            'username': self.user_without_email.username,
            'password': self.password,
        })

        self.assertEqual(response.status_code, 200)
        session = self.client.session
        self.assertIsNone(session.get(LOGIN_VERIFICATION_SESSION_KEY))
        self.assertNotIn('_auth_user_id', session)
        self.assertEqual(len(mail.outbox), 0)
