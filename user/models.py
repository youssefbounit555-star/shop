from django.db import models
from django.contrib.auth.models import User
from django_countries.fields import CountryField
# Create your models here.

class UserProfile(models.Model):
    CATEGORY_CHOICES = [
        ("Women's clothing", "Women's clothing"),
        ("Watch", "Watch"),
        ("Men's clothing", "Men's clothing"),
        ("Kids' clothing", "Kids' clothing"),
        ("Accessories", "Accessories"),
        ("Footwear", "Footwear"),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=50, blank=True)
    country = CountryField(blank_label="(select country)", blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    interesting = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username}'s Profile"