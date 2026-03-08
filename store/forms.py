from django import forms
from django.core.exceptions import ValidationError
from .models import Product, Order, OrderItem, SiteSettings, ProductImage
from dashboard.models import Message
import json

MAX_GALLERY_IMAGES = 5


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    widget = MultipleImageInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        return single_file_clean(data, initial)


class ProductForm(forms.ModelForm):
    """
    Advanced product creation/editing form with custom widgets.
    """
    payment_mode = forms.ChoiceField(
        choices=Product.PAYMENT_MODE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Choose COD for payment on delivery, or Pay Online for Stripe/PayPal.'
    )
    accepts_stripe = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    accepts_paypal = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    gallery_uploads = MultipleImageField(
        widget=MultipleImageInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'multiple': True,
        }),
        required=False,
        help_text=f"Upload up to {MAX_GALLERY_IMAGES} gallery images"
    )

    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'description', 'short_description',
            'price', 'discount_price', 'discount_note', 'stock_quantity', 'sku',
            'category', 'brand', 'tags', 'weight',
            'featured', 'featured_order', 'is_active', 'is_digital', 'status',
            'payment_mode', 'accepts_stripe', 'accepts_paypal',
            'main_image', 'product_video', 'meta_title', 'meta_description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Product name',
                'required': True
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Auto-generated slug'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Product description (supports HTML)'
            }),
            'short_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Short description for listings'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'discount_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank for no discount',
                'step': '0.01',
                'min': '0'
            }),
            'discount_note': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: Limited-time offer'
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Stock Keeping Unit'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'brand': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brand name'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'comma, separated, tags'
            }),
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Weight in kg',
                'step': '0.001'
            }),
            'featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'featured_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Priority (lower = higher)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_digital': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'main_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'product_video': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*'
            }),
            'meta_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SEO title'
            }),
            'meta_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SEO description'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        discount_price = cleaned_data.get('discount_price')
        payment_mode = cleaned_data.get('payment_mode')
        accepts_stripe = cleaned_data.get('accepts_stripe')
        accepts_paypal = cleaned_data.get('accepts_paypal')
        effective_price = discount_price if discount_price is not None else price
        is_free_product = effective_price is not None and effective_price <= 0
        
        if price is not None and discount_price is not None:
            if price > 0 and discount_price >= price:
                raise ValidationError(
                    "Discount price must be less than regular price."
                )
            if price == 0 and discount_price > 0:
                raise ValidationError(
                    "Discount price cannot be greater than 0 when regular price is 0."
                )

        if payment_mode == 'online' and not (accepts_stripe or accepts_paypal) and not is_free_product:
            raise ValidationError(
                "Select at least one online payment method: Stripe or PayPal."
            )

        if payment_mode == 'cash_on_delivery':
            cleaned_data['accepts_stripe'] = False
            cleaned_data['accepts_paypal'] = False
        
        return cleaned_data

    def clean_gallery_uploads(self):
        files = self.cleaned_data.get('gallery_uploads')
        if not files:
            return []

        if not isinstance(files, list):
            files = [files]

        existing_count = 0
        if self.instance and self.instance.pk:
            existing_count = self.instance.images.count()

        if existing_count + len(files) > MAX_GALLERY_IMAGES:
            remaining = max(MAX_GALLERY_IMAGES - existing_count, 0)
            raise ValidationError(
                f"Maximum {MAX_GALLERY_IMAGES} gallery images allowed. "
                f"You can upload {remaining} more image(s)."
            )

        for uploaded in files:
            content_type = getattr(uploaded, 'content_type', '') or ''
            if not content_type.startswith('image/'):
                raise ValidationError("Only image files are allowed for gallery uploads.")

        return files


class DiscountSetupForm(forms.Form):
    """
    Lightweight admin form for applying a discount configuration to an existing product.
    """
    product = forms.ModelChoiceField(
        queryset=Product.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='Select a product'
    )
    new_discount_price = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'placeholder': 'Leave empty to keep/remove current discount price',
        })
    )
    discount_note = forms.CharField(
        required=False,
        max_length=140,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Example: Limited-time offer',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        new_discount_price = cleaned_data.get('new_discount_price')
        discount_note = (cleaned_data.get('discount_note') or '').strip()

        if new_discount_price is None and not discount_note:
            raise ValidationError(
                "Enter a new discount price or a discount text."
            )

        if product and new_discount_price is not None and product.price > 0 and new_discount_price >= product.price:
            raise ValidationError(
                "Discount price must be less than product price."
            )

        cleaned_data['discount_note'] = discount_note
        return cleaned_data


class OrderForm(forms.ModelForm):
    """
    Order management form for admin.
    """
    class Meta:
        model = Order
        fields = [
            'full_name', 'email', 'phone', 'address', 'city', 'country',
            'shipping_latitude', 'shipping_longitude',
            'status', 'payment_method', 'payment_status', 'notes'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'readonly': True
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'shipping_latitude': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'shipping_longitude': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
                'readonly': True
            }),
            'payment_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Internal notes (not visible to customer)'
            }),
        }


class CustomerOrderForm(forms.ModelForm):
    """
    Order form for customers on the frontend.
    """
    class Meta:
        model = Order
        fields = [
            'full_name', 'email', 'phone', 'address', 'city', 'country',
            'postal_code', 'shipping_latitude', 'shipping_longitude', 'payment_method', 'customer_notes'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 000-0000'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ZIP/Postal code'
            }),
            'shipping_latitude': forms.HiddenInput(),
            'shipping_longitude': forms.HiddenInput(),
            'payment_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'customer_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any special notes or requests...'
            }),
        }


class SiteSettingsForm(forms.ModelForm):
    """
    Site settings management form.
    """
    social_links_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': '{"facebook": "url", "instagram": "url", "twitter": "url"}'
        }),
        required=False,
        help_text="Enter social links as JSON format"
    )

    class Meta:
        model = SiteSettings
        fields = [
            'site_name', 'site_description', 'logo', 'favicon',
            'support_email', 'support_phone', 'whatsapp_number',
            'address', 'city', 'country', 'currency', 'tax_rate',
            'shipping_cost', 'free_shipping_threshold', 'maintenance_mode',
            'maintenance_message', 'homepage_banner', 'homepage_title',
            'homepage_subtitle', 'meta_title', 'meta_description'
        ]
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-control'}),
            'site_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'favicon': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'support_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'support_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'free_shipping_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'maintenance_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'maintenance_message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'homepage_banner': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'homepage_title': forms.TextInput(attrs={'class': 'form-control'}),
            'homepage_subtitle': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_description': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_social_links_json(self):
        """Validate JSON format for social links"""
        json_str = self.cleaned_data.get('social_links_json')
        if json_str:
            try:
                json.loads(json_str)
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON format for social links")
        return json_str


class BulkProductActionForm(forms.Form):
    """
    Form for bulk product actions.
    """
    ACTION_CHOICES = [
        ('', '--- Select Action ---'),
        ('activate', 'Activate Products'),
        ('deactivate', 'Deactivate Products'),
        ('delete', 'Delete Products'),
        ('mark_featured', 'Mark as Featured'),
        ('remove_featured', 'Remove from Featured'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    product_ids = forms.CharField(widget=forms.HiddenInput())


class ProductFilterForm(forms.Form):
    """
    Form for filtering products in admin.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search products...'
        })
    )
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'All Categories')] + Product.CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status')] + Product.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    featured = forms.NullBooleanField(
        required=False,
        widget=forms.Select(
            choices=[('', 'All'), ('true', 'Featured'), ('false', 'Not Featured')],
            attrs={'class': 'form-select'}
        )
    )
    in_stock = forms.NullBooleanField(
        required=False,
        widget=forms.Select(
            choices=[('', 'All'), ('true', 'In Stock'), ('false', 'Out of Stock')],
            attrs={'class': 'form-select'}
        )
    )


class OrderFilterForm(forms.Form):
    """
    Form for filtering orders in admin.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by order ID, customer name, email...'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status')] + Order.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Payment Status')] + [('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class MessageReplyForm(forms.ModelForm):
    """
    Form for replying to customer messages.
    """
    class Meta:
        model = Message
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Type your reply...'
            })
        }
