from django import forms
from django.contrib.auth.models import User
from django_countries.widgets import CountrySelectWidget
from dashboard.models import Goal, Message
from user.models import UserProfile


class GoalForm(forms.ModelForm):
    """
    Form for creating and updating goals.
    """
    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your goal...',
            'required': 'required'
        })
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Add details about your goal (optional)',
            'rows': 3
        })
    )

    class Meta:
        model = Goal
        fields = ['title', 'description']


class MessageForm(forms.ModelForm):
    """
    Form for sending messages.
    """
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control message-input',
            'placeholder': 'Type your message...',
            'rows': 2,
            'required': 'required'
        })
    )

    class Meta:
        model = Message
        fields = ['message']


class UserUpdateForm(forms.ModelForm):
    """
    Form for updating user basic information.
    """
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user profile extended information.
    """
    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Address'
        })
    )
    city = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City'
        })
    )
    country = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Country'
        })
    )
    interesting = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control form-control-lg'
        })
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )

    class Meta:
        model = UserProfile
        fields = ['address', 'city', 'country', 'interesting', 'avatar']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get the interesting choices from UserProfile model
        self.fields['interesting'].choices = [('', '-- Select a category --')] + UserProfile.CATEGORY_CHOICES
