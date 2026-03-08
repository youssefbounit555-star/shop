from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django_countries.widgets import CountrySelectWidget
from .models import UserProfile


class UserRegisterForm(UserCreationForm):
    """
    Registration form using Django's built-in User model + UserProfile.
    Bootstrap 5 styling applied.
    """
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name',
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name',
        })
    )
    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Street address',
        })
    )
    city = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City',
        })
    )
    country = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Country',
        })
    )
    interesting = forms.ChoiceField(
        choices=[('', '--- Select your interest ---')] + list(UserProfile.CATEGORY_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password',
        })
        # Add helpful text to password fields
        self.fields['password1'].help_text = 'Must contain at least 8 characters'
        self.fields['password2'].label = 'Confirm Password'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already registered.')
        return email

    def save(self, commit=True):
        """Save User and create UserProfile"""
        user = super().save(commit=commit)
        
        if commit:
            # Create or update UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.address = self.cleaned_data.get('address', '')
            profile.city = self.cleaned_data.get('city', '')
            profile.interesting = self.cleaned_data.get('interesting', '')
            
            # Handle country
            country = self.cleaned_data.get('country', '')
            if country:
                from django_countries.fields import countries
                # Try to find country code
                for code, name in countries:
                    if name.lower() == country.lower() or code.lower() == country.lower():
                        profile.country = code
                        break
            
            # Handle avatar
            avatar = self.cleaned_data.get('avatar')
            if avatar:
                profile.avatar = avatar
            
            profile.save()
        
        return user


class UserLoginForm(forms.Form):
    """
    Login form for Django User model (username + password).
    Bootstrap 5 styling applied.
    """
    username = forms.CharField(
        label='Username',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if not username or not password:
            raise forms.ValidationError('Please enter username and password.')
        
        # Authenticate user
        try:
            user = User.objects.get(username=username)
            if not user.check_password(password):
                raise forms.ValidationError('Invalid username or password.')
            # Store user for later retrieval
            self.user = user
        except User.DoesNotExist:
            raise forms.ValidationError('Invalid username or password.')
        
        return cleaned_data


class UserUpdateForm(forms.ModelForm):
    """
    Form to update Django User model basic information.
    Bootstrap 5 styling applied.
    """
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email',
            }),
        }


class UserProfileUpdateForm(forms.ModelForm):
    """
    Form to update UserProfile extended information.
    Bootstrap 5 styling applied.
    """
    class Meta:
        model = UserProfile
        fields = ('address', 'city', 'country', 'interesting', 'avatar')
        widgets = {
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street address',
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City',
            }),
            'country': CountrySelectWidget(attrs={
                'class': 'form-select',
            }),
            'interesting': forms.Select(attrs={
                'class': 'form-select',
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }


class PasswordResetForm(forms.Form):
    """
    Form to request password reset.
    User enters their username or email.
    """
    username_or_email = forms.CharField(
        label='Username or Email',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username or email',
            'autofocus': True,
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username_or_email = cleaned_data.get('username_or_email')

        if username_or_email:
            try:
                user = User.objects.get(username=username_or_email)
                self.user = user
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=username_or_email)
                    self.user = user
                except User.DoesNotExist:
                    raise forms.ValidationError('No account found with this username or email.')
        else:
            raise forms.ValidationError('Please enter your username or email.')
        
        return cleaned_data


class PasswordResetConfirmForm(forms.Form):
    """
    Form to reset password with new password and confirmation.
    """
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
        })
    )
    confirm_password = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError('Passwords do not match.')
            
            if len(new_password) < 8:
                raise forms.ValidationError('Password must be at least 8 characters long.')
        
        return cleaned_data


class LoginVerificationForm(forms.Form):
    """
    Form for verifying email code before completing login.
    """
    verification_code = forms.CharField(
        label='Verification Code',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit code',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': r'[0-9]{6}',
        })
    )

    def clean_verification_code(self):
        code = (self.cleaned_data.get('verification_code') or '').strip()
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError('Enter a valid 6-digit code.')
        return code
