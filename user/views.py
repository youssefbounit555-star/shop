import random
import string
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import (
    LoginVerificationForm,
    PasswordResetConfirmForm,
    PasswordResetForm,
    UserLoginForm,
    UserRegisterForm,
    UserUpdateForm,
)
from .models import UserProfile


LOGIN_VERIFICATION_SESSION_KEY = 'pending_login_verification'
LOGIN_VERIFICATION_TTL_MINUTES = 10
LOGIN_VERIFICATION_MAX_ATTEMPTS = 5


def _mask_email(email: str) -> str:
    if '@' not in email:
        return email
    local_part, domain = email.split('@', 1)
    if len(local_part) <= 2:
        masked_local = local_part[:1] + '*'
    else:
        masked_local = local_part[:2] + ('*' * (len(local_part) - 2))
    return f'{masked_local}@{domain}'


def _generate_login_verification_code() -> str:
    return ''.join(random.choices(string.digits, k=6))


def _clear_pending_login(request) -> None:
    request.session.pop(LOGIN_VERIFICATION_SESSION_KEY, None)


def _get_pending_login(request):
    pending = request.session.get(LOGIN_VERIFICATION_SESSION_KEY)
    if not isinstance(pending, dict):
        return None
    return pending


def _send_login_verification_email(user: User, code: str) -> None:
    send_mail(
        subject='ElegantShop Login Verification Code',
        message=(
            f'Hello {user.username},\n\n'
            f'Your login verification code is: {code}\n\n'
            f'This code expires in {LOGIN_VERIFICATION_TTL_MINUTES} minutes.\n'
            'If you did not try to sign in, please ignore this message.'
        ),
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost'),
        recipient_list=[user.email],
        fail_silently=False,
    )


def _start_login_verification(request, user: User) -> None:
    code = _generate_login_verification_code()
    expires_at = timezone.now() + timedelta(minutes=LOGIN_VERIFICATION_TTL_MINUTES)

    _send_login_verification_email(user, code)
    request.session[LOGIN_VERIFICATION_SESSION_KEY] = {
        'user_id': user.id,
        'email': user.email,
        'code': code,
        'expires_at_ts': expires_at.timestamp(),
        'attempts': 0,
    }
    request.session.modified = True


def register(request):
    """
    User registration view.
    Handles GET (display form) and POST (process registration).
    """
    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()            
            messages.success(
                request,
                f'Account created successfully! Welcome {user.username}. You can now log in.'
            )
            return redirect('user:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = UserRegisterForm()
    
    return render(request, 'user/register.html', {'form': form})


def login_view(request):
    """
    User login view.
    Authenticates user based on username/email and password.
    Uses session to store logged-in user ID.
    """
    if request.user.is_authenticated:
        # User already logged in
        return redirect('store:home')

    if request.method == 'GET' and _get_pending_login(request):
        return redirect('user:login_verify')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            # Get authenticated user from form
            user = form.user
            if not user.email:
                messages.error(
                    request,
                    'لا يمكن إكمال تسجيل الدخول لأن الحساب لا يحتوي على بريد إلكتروني.'
                )
                return render(request, 'user/login.html', {'form': form})

            try:
                _start_login_verification(request, user)
            except Exception:
                messages.error(
                    request,
                    'تعذر إرسال رمز التحقق للبريد الإلكتروني. حاول مرة أخرى.'
                )
                return render(request, 'user/login.html', {'form': form})

            messages.info(
                request,
                f'أرسلنا رمز تحقق إلى {user.email}. أدخل الرمز لإكمال تسجيل الدخول.'
            )
            return redirect('user:login_verify')
        else:
            for field, errors in form.errors.items():
                if field != '__all__':
                    messages.error(request, errors[0])
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)

    else:
        form = UserLoginForm()
    return render(request, 'user/login.html', {'form': form})


def logout_view(request):
    """
    User logout view.
    Clears session data.
    """
    username = request.session.get('username')
    if not username and request.user.is_authenticated:
        username = request.user.username
    if not username:
        username = 'User'

    auth_logout(request)
    _clear_pending_login(request)
    messages.success(request, f'Goodbye {username}! You have been logged out.')
    
    return redirect('store:home')


def login_verify_view(request):
    """
    Second step login verification using a code sent to user email.
    """
    if request.user.is_authenticated:
        return redirect('store:home')

    pending = _get_pending_login(request)
    if not pending:
        messages.error(request, 'لا يوجد طلب تحقق نشط. سجل الدخول أولاً.')
        return redirect('user:login')

    user_id = pending.get('user_id')
    email = (pending.get('email') or '').strip()
    expected_code = str(pending.get('code') or '').strip()
    expires_at_ts = float(pending.get('expires_at_ts') or 0)
    attempts = int(pending.get('attempts') or 0)

    user = User.objects.filter(id=user_id).first()
    if not user or not email or user.email != email:
        _clear_pending_login(request)
        messages.error(request, 'بيانات التحقق غير صالحة. سجل الدخول مرة أخرى.')
        return redirect('user:login')

    now_ts = timezone.now().timestamp()
    if now_ts > expires_at_ts:
        _clear_pending_login(request)
        messages.error(request, 'انتهت صلاحية رمز التحقق. سجل الدخول لإرسال رمز جديد.')
        return redirect('user:login')

    if request.method == 'POST' and request.POST.get('action') == 'resend':
        try:
            _start_login_verification(request, user)
        except Exception:
            messages.error(request, 'تعذر إعادة إرسال الرمز. حاول بعد لحظات.')
        else:
            messages.success(request, f'تم إرسال رمز جديد إلى {user.email}.')
        return redirect('user:login_verify')

    if request.method == 'POST':
        form = LoginVerificationForm(request.POST)
        if form.is_valid():
            entered_code = form.cleaned_data['verification_code']

            if entered_code != expected_code:
                attempts += 1
                pending['attempts'] = attempts
                request.session[LOGIN_VERIFICATION_SESSION_KEY] = pending
                request.session.modified = True

                if attempts >= LOGIN_VERIFICATION_MAX_ATTEMPTS:
                    _clear_pending_login(request)
                    messages.error(
                        request,
                        'تم تجاوز عدد محاولات التحقق المسموح بها. سجل الدخول مرة أخرى.'
                    )
                    return redirect('user:login')

                remaining_attempts = LOGIN_VERIFICATION_MAX_ATTEMPTS - attempts
                form.add_error(
                    'verification_code',
                    f'رمز التحقق غير صحيح. تبقى {remaining_attempts} محاولة.'
                )
            else:
                _clear_pending_login(request)
                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                messages.success(request, f'تم التحقق بنجاح. مرحبًا {user.username}!')
                return redirect('store:home')
    else:
        form = LoginVerificationForm()

    context = {
        'form': form,
        'pending_email': email,
        'masked_email': _mask_email(email),
        'remaining_attempts': LOGIN_VERIFICATION_MAX_ATTEMPTS - attempts,
    }
    return render(request, 'user/login_verify.html', context)


def get_profile(request):
    """Helper function to get profile from session."""
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if request.session.get('user_id') != request.user.id:
            request.session['user_id'] = request.user.id
        if request.session.get('username') != request.user.username:
            request.session['username'] = request.user.username
        return profile

    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            return profile
        except User.DoesNotExist:
            request.session.pop('user_id', None)
            request.session.pop('username', None)
            return None
    return None

def profile(request):
    profile = get_profile(request)
    if not profile:
        messages.info(request, 'Please log in to access your profile.')
        return redirect('user:login')

    context = {
        'profile': profile,
    }
    return render(request, 'user/profile.html', context)


def password_reset(request):
    """
    Password reset request view.
    User enters their username or email to initiate password reset.
    """
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            # Store user ID in session temporarily for reset flow
            user = form.user
            request.session['reset_user_id'] = user.id
            request.session['reset_user_email'] = user.email
            
            messages.success(request, f'Password reset instructions have been sent to {user.email}')
            return redirect('user:password_reset_confirm')
    else:
        form = PasswordResetForm()
    
    return render(request, 'registration/password_reset.html', {'form': form})


def password_reset_confirm(request):
    """
    Password reset confirmation view.
    User sets their new password after verification.
    """
    # Check if user has initiated password reset
    reset_user_id = request.session.get('reset_user_id')
    reset_user_email = request.session.get('reset_user_email')
    
    if not reset_user_id or not reset_user_email:
        messages.error(request, 'Failed to validate password reset request. Please try again.')
        return redirect('user:password_reset')
    
    try:
        user = User.objects.get(id=reset_user_id, email=reset_user_email)
    except User.DoesNotExist:
        messages.error(request, 'Invalid password reset request.')
        return redirect('user:password_reset')
    
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            # Update user password
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            
            # Clear reset session data
            if 'reset_user_id' in request.session:
                del request.session['reset_user_id']
            if 'reset_user_email' in request.session:
                del request.session['reset_user_email']
            
            messages.success(request, 'Password reset successfully! You can now log in with your new password.')
            return redirect('user:login')
    else:
        form = PasswordResetConfirmForm()
    
    context = {
        'form': form,
        'user_email': reset_user_email,
    }
    return render(request, 'registration/password_reset_confirm.html', context)
