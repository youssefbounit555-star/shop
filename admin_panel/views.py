from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from decimal import Decimal
import csv
import json
from django.contrib.auth.models import User

from user.models import UserProfile
from store.models import Product, Order, OrderItem, SiteSettings, ProductImage
from chat.models import Conversation as SupportConversation, Message as SupportMessage
from store.forms import (
    ProductForm, OrderForm, SiteSettingsForm, BulkProductActionForm,
    ProductFilterForm, OrderFilterForm, DiscountSetupForm, MAX_GALLERY_IMAGES
)
from analytics.models import Insight
from analytics.insights import ensure_recent_insights
from analytics.utils import get_live_counts, LIVE_WINDOW_MINUTES



def get_user_display_name(user, fallback=''):
    if user:
        full_name = user.get_full_name().strip()
        if full_name:
            return full_name
        if user.username:
            return user.username
    return fallback


def get_customer_user_and_orders(email):
    user = User.objects.filter(email=email, is_staff=False, is_superuser=False).first()
    profile = UserProfile.objects.filter(user=user).first() if user else None
    orders = Order.objects.filter(
        Q(email=email) | Q(user__email=email)
    ).prefetch_related('items__product').order_by('-created_at')
    return user, profile, orders


def build_customer_context(email):
    user, profile, orders = get_customer_user_and_orders(email)

    order_customer_info = orders.values(
        'full_name', 'email', 'phone', 'address', 'city', 'country'
    ).first()

    full_name = get_user_display_name(user=user, fallback='')
    if not full_name and order_customer_info:
        full_name = order_customer_info.get('full_name') or ''
    if not full_name:
        full_name = email or 'Customer'

    customer_info = {
        'full_name': full_name,
        'email': email,
        'phone': (order_customer_info.get('phone') if order_customer_info else '') or '',
        'address': (
            profile.address
            if profile and profile.address
            else (order_customer_info.get('address') if order_customer_info else '') or ''
        ),
        'city': (
            profile.city
            if profile and profile.city
            else (order_customer_info.get('city') if order_customer_info else '') or ''
        ),
        'country': (
            profile.country.name
            if profile and profile.country
            else (order_customer_info.get('country') if order_customer_info else '') or ''
        ),
        'username': user.username if user else '',
        'has_account': bool(user),
        'last_login': user.last_login if user else None,
        'date_joined': user.date_joined if user else None,
    }

    stats = orders.aggregate(
        total_orders=Count('id'),
        total_spent=Sum('total_price'),
        avg_order_value=Avg('total_price')
    )
    stats['total_orders'] = stats['total_orders'] or 0
    stats['total_spent'] = stats['total_spent'] or Decimal('0.00')
    stats['avg_order_value'] = stats['avg_order_value'] or Decimal('0.00')

    return user, orders, customer_info, stats


# ==================== ADMIN MIXINS ====================

class AdminOnlyMixin(UserPassesTestMixin):
    """
    Mixin to ensure only superusers/staff can access admin views.
    """
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, 'Access Denied. Admin privileges required.')
        return redirect('dashboard:index')


# ==================== ADMIN DASHBOARD ====================

class AdminDashboardView(AdminOnlyMixin, TemplateView):
    """
    Main admin dashboard with analytics and KPIs.
    """
    template_name = 'admin/dashboard/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Time period calculations
        today = timezone.now().date()
        last_30_days = timezone.now() - timedelta(days=30)
        
        # Product Statistics
        context['total_products'] = Product.objects.filter(is_active=True).count()
        context['featured_products'] = Product.objects.filter(featured=True, is_active=True).count()
        context['low_stock_products'] = Product.objects.filter(stock_quantity__lt=10, stock_quantity__gt=0).count()
        context['out_of_stock'] = Product.objects.filter(stock_quantity=0).count()
        
        # Order Statistics
        context['total_orders'] = Order.objects.count()
        context['pending_orders'] = Order.objects.filter(status='pending').count()
        context['processing_orders'] = Order.objects.filter(status='processing').count()
        context['shipped_today'] = Order.objects.filter(
            status='shipped',
            shipped_at__date=today
        ).count()
        
        # Revenue Statistics
        all_orders = Order.objects.filter(status__in=['completed', 'shipped'])
        context['total_revenue'] = all_orders.aggregate(
            total=Sum('total_price')
        )['total'] or 0
        context['today_revenue'] = all_orders.filter(
            created_at__date=today
        ).aggregate(total=Sum('total_price'))['total'] or 0
        context['monthly_revenue'] = all_orders.filter(
            created_at__gte=last_30_days
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        # Top Products
        context['top_products'] = OrderItem.objects.values(
            'product__name', 'product__id'
        ).annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum('subtotal')
        ).order_by('-total_sold')[:5]
        
        # Recent Orders
        context['recent_orders'] = Order.objects.all()[:10]
        
        # Customer Statistics
        context['total_customers'] = Order.objects.filter(
            email__isnull=False
        ).exclude(
            email__exact=''
        ).values('email').distinct().count()
        
        # Messages
        context['unread_messages'] = SupportMessage.objects.filter(
            conversation__admin=self.request.user,
            is_read=False
        ).exclude(sender=self.request.user).count()
        
        # Site Settings
        context['settings'] = SiteSettings.get_settings()
        
        return context


# ==================== PRODUCT MANAGEMENT ====================

class ProductListView(AdminOnlyMixin, ListView):
    """
    Admin product list with filtering and search.
    """
    model = Product
    template_name = 'admin/products/list.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        queryset = Product.objects.all()
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(short_description__icontains=search)
            )
        
        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by featured
        featured = self.request.GET.get('featured')
        if featured == 'true':
            queryset = queryset.filter(featured=True)
        elif featured == 'false':
            queryset = queryset.filter(featured=False)
        
        # Filter by stock
        in_stock = self.request.GET.get('in_stock')
        if in_stock == 'true':
            queryset = queryset.filter(stock_quantity__gt=0)
        elif in_stock == 'false':
            queryset = queryset.filter(stock_quantity=0)
        
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ProductFilterForm(self.request.GET)
        context['total_products'] = Product.objects.count()
        return context


class ProductCreateView(AdminOnlyMixin, CreateView):
    """
    Create new product.
    """
    model = Product
    form_class = ProductForm
    template_name = 'admin/products/form.html'
    success_url = reverse_lazy('admin_panel:products_list')

    def _sync_gallery_images_json(self, product):
        gallery_urls = [image.image.url for image in product.images.all() if image.image]
        product.gallery_images = gallery_urls
        product.save(update_fields=['gallery_images'])

    def _save_gallery_uploads(self, product, uploads):
        if not uploads:
            return

        existing_count = product.images.count()
        remaining_slots = max(MAX_GALLERY_IMAGES - existing_count, 0)
        for offset, image_file in enumerate(uploads[:remaining_slots]):
            ProductImage.objects.create(
                product=product,
                image=image_file,
                order=existing_count + offset
            )

        self._sync_gallery_images_json(product)

    def form_valid(self, form):
        response = super().form_valid(form)
        uploads = form.cleaned_data.get('gallery_uploads', [])
        self._save_gallery_uploads(self.object, uploads)
        messages.success(self.request, f"Product '{self.object.name}' created successfully!")
        return response


class ProductUpdateView(AdminOnlyMixin, UpdateView):
    """
    Edit existing product.
    """
    model = Product
    form_class = ProductForm
    template_name = 'admin/products/form.html'
    success_url = reverse_lazy('admin_panel:products_list')

    def _sync_gallery_images_json(self, product):
        gallery_urls = [image.image.url for image in product.images.all() if image.image]
        product.gallery_images = gallery_urls
        product.save(update_fields=['gallery_images'])

    def _save_gallery_uploads(self, product, uploads):
        if not uploads:
            return

        existing_count = product.images.count()
        remaining_slots = max(MAX_GALLERY_IMAGES - existing_count, 0)
        for offset, image_file in enumerate(uploads[:remaining_slots]):
            ProductImage.objects.create(
                product=product,
                image=image_file,
                order=existing_count + offset
            )

        self._sync_gallery_images_json(product)

    def form_valid(self, form):
        response = super().form_valid(form)
        uploads = form.cleaned_data.get('gallery_uploads', [])
        self._save_gallery_uploads(self.object, uploads)
        messages.success(self.request, f"Product '{self.object.name}' updated successfully!")
        return response


class ProductDeleteView(AdminOnlyMixin, DeleteView):
    """
    Delete product.
    """
    model = Product
    template_name = 'admin/products/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:products_list')

    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        product_name = product.name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"Product '{product_name}' deleted successfully!")
        return response


class ProductDetailView(AdminOnlyMixin, DetailView):
    """
    Product detail view for admin.
    """
    model = Product
    template_name = 'admin/products/detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order_items'] = OrderItem.objects.filter(product=self.object)
        context['total_sold'] = OrderItem.objects.filter(
            product=self.object
        ).aggregate(total=Sum('quantity'))['total'] or 0
        return context


class BulkProductActionView(AdminOnlyMixin, View):
    """
    Handle bulk product actions.
    """
    def post(self, request):
        action = request.POST.get('action')
        product_ids = request.POST.getlist('product_ids')
        
        if not product_ids:
            messages.error(request, 'No products selected!')
            return redirect('admin_panel:products_list')
        
        products = Product.objects.filter(id__in=product_ids)
        
        if action == 'activate':
            products.update(is_active=True)
            messages.success(request, f'{len(product_ids)} products activated!')
        elif action == 'deactivate':
            products.update(is_active=False)
            messages.success(request, f'{len(product_ids)} products deactivated!')
        elif action == 'delete':
            products.delete()
            messages.success(request, f'{len(product_ids)} products deleted!')
        elif action == 'mark_featured':
            products.update(featured=True)
            messages.success(request, f'{len(product_ids)} products marked as featured!')
        elif action == 'remove_featured':
            products.update(featured=False)
            messages.success(request, f'{len(product_ids)} products removed from featured!')
        
        return redirect('admin_panel:products_list')


class ProductExportView(AdminOnlyMixin, View):
    """
    Export products to CSV.
    """
    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="products.csv"'
        
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'Product ID', 'Name', 'SKU', 'Category', 'Price', 'Stock', 
            'Status', 'Featured', 'Created', 'Description'
        ])
        
        products = Product.objects.all()
        for product in products:
            writer.writerow([
                product.id,
                product.name,
                product.sku,
                product.category,
                product.price,
                product.stock_quantity,
                product.get_status_display(),
                'Yes' if product.featured else 'No',
                product.created_at.strftime('%Y-%m-%d %H:%M'),
                product.short_description or ''
            ])
        
        return response


class DiscountsManagementView(AdminOnlyMixin, View):
    """
    Dedicated admin page for discount configuration.
    """
    template_name = 'admin/discounts/index.html'

    def get_discounted_products(self):
        return Product.objects.filter(
            Q(discount_price__isnull=False) | ~Q(discount_note='')
        ).order_by('-updated_at', '-created_at')

    def get(self, request):
        settings_obj = SiteSettings.get_settings()
        context = {
            'discount_form': DiscountSetupForm(),
            'discounted_products': self.get_discounted_products(),
            'currency_label': settings_obj.currency or 'USD',
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = (request.POST.get('action') or 'apply').strip().lower()

        if action == 'remove':
            product_id = request.POST.get('product_id')
            product = get_object_or_404(Product, pk=product_id)
            product.discount_price = None
            product.discount_note = ''
            product.save(update_fields=['discount_price', 'discount_note', 'updated_at'])
            messages.success(request, f"Discount removed from '{product.name}'.")
            return redirect('admin_panel:discounts')

        discount_form = DiscountSetupForm(request.POST)
        if discount_form.is_valid():
            product = discount_form.cleaned_data['product']
            product.discount_price = discount_form.cleaned_data.get('new_discount_price')
            product.discount_note = discount_form.cleaned_data.get('discount_note', '')
            product.save(update_fields=['discount_price', 'discount_note', 'updated_at'])
            messages.success(request, f"Discount updated for '{product.name}'.")
            return redirect('admin_panel:discounts')

        settings_obj = SiteSettings.get_settings()
        context = {
            'discount_form': discount_form,
            'discounted_products': self.get_discounted_products(),
            'currency_label': settings_obj.currency or 'USD',
        }
        return render(request, self.template_name, context)


# ==================== ORDER MANAGEMENT ====================

class OrderListView(AdminOnlyMixin, ListView):
    """
    Admin order list with filtering.
    """
    model = Order
    template_name = 'admin/orders/list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        queryset = Order.objects.prefetch_related('items__product')
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_id__icontains=search) |
                Q(full_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by payment status
        payment_status = self.request.GET.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = OrderFilterForm(self.request.GET)
        context['total_orders'] = Order.objects.count()
        context['pending_orders'] = Order.objects.filter(status='pending').count()
        return context


class OrderDetailView(AdminOnlyMixin, DetailView):
    """
    Order detail page for admin.
    """
    model = Order
    template_name = 'admin/orders/detail.html'
    context_object_name = 'order'
    slug_field = 'order_id'
    slug_url_kwarg = 'order_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order_items'] = self.object.items.all()
        context['status_choices'] = Order.STATUS_CHOICES
        return context


class OrderUpdateView(AdminOnlyMixin, UpdateView):
    """
    Update order details (status, notes, etc).
    """
    model = Order
    form_class = OrderForm
    template_name = 'admin/orders/edit.html'
    
    def get_object(self):
        return get_object_or_404(Order, order_id=self.kwargs['order_id'])

    def get_success_url(self):
        messages.success(self.request, 'Order updated successfully!')
        return reverse_lazy('admin_panel:orders_detail', kwargs={'order_id': self.object.order_id})


class OrderExportView(AdminOnlyMixin, View):
    """
    Export orders to CSV.
    """
    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'Order ID', 'Customer', 'Email', 'Phone', 'Total', 'Status',
            'Payment Status', 'Created', 'Items'
        ])
        
        orders = Order.objects.prefetch_related('items__product')
        for order in orders:
            items = ', '.join([
                f"{item.product.name}({item.quantity})" for item in order.items.all()
            ])
            writer.writerow([
                order.order_id,
                order.full_name,
                order.email,
                order.phone,
                order.total_price,
                order.get_status_display(),
                order.get_payment_status_display(),
                order.created_at.strftime('%Y-%m-%d %H:%M'),
                items
            ])
        
        return response


# ==================== CUSTOMER MANAGEMENT ====================

class CustomerListView(AdminOnlyMixin, ListView):
    """
    List customers across registered accounts and order records.
    """
    template_name = 'admin/customers/list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def _get_customer_key(self, user=None, order=None):
        if user and user.email:
            return user.email.strip().lower()

        if order:
            if order.user and order.user.email:
                return order.user.email.strip().lower()
            if order.email:
                return order.email.strip().lower()
            if order.user_id:
                return f'user:{order.user_id}'

        if user:
            return f'user:{user.id}'

        return None

    def _build_customer_record(self, *, user=None, email='', full_name='', username='', phone='',
                               is_registered=False, has_logged_in=False, last_login=None,
                               date_joined=None, has_orders=False, total_orders=0,
                               total_spent=None, latest_order_at=None):
        return {
            'email': email,
            'full_name': full_name or username or email or 'Guest customer',
            'username': username,
            'phone': phone,
            'is_registered': is_registered,
            'has_logged_in': has_logged_in,
            'last_login': last_login,
            'date_joined': date_joined,
            'has_orders': has_orders,
            'total_orders': total_orders,
            'total_spent': total_spent if total_spent is not None else Decimal('0.00'),
            'latest_order_at': latest_order_at,
            'user_id': user.id if user else None,
        }

    def get_queryset(self):
        """Build a unified customer list with account and order visibility."""
        customers_map = {}
        profiles = {
            profile.user_id: profile
            for profile in UserProfile.objects.select_related('user')
        }

        for user in User.objects.filter(is_staff=False, is_superuser=False).order_by('-date_joined'):
            key = self._get_customer_key(user=user)
            email = (user.email or '').strip()
            profile = profiles.get(user.id)
            customers_map[key] = self._build_customer_record(
                user=user,
                email=email,
                full_name=get_user_display_name(user=user, fallback=email),
                username=user.username,
                phone='',
                is_registered=True,
                has_logged_in=bool(user.last_login),
                last_login=user.last_login,
                date_joined=user.date_joined,
            )

            if profile and not customers_map[key]['full_name']:
                customers_map[key]['full_name'] = email or user.username

        for order in Order.objects.select_related('user').order_by('-created_at'):
            key = self._get_customer_key(order=order)
            if not key:
                continue

            customer = customers_map.get(key)
            if customer is None:
                guest_email = (order.email or '').strip()
                guest_name = (order.full_name or '').strip() or guest_email or 'Guest customer'
                customer = self._build_customer_record(
                    user=order.user,
                    email=guest_email or (order.user.email if order.user else ''),
                    full_name=guest_name,
                    username=order.user.username if order.user else '',
                    phone=(order.phone or '').strip(),
                    is_registered=bool(order.user_id),
                    has_logged_in=bool(order.user and order.user.last_login),
                    last_login=order.user.last_login if order.user else None,
                    date_joined=order.user.date_joined if order.user else None,
                )
                customers_map[key] = customer

            customer['has_orders'] = True
            customer['total_orders'] += 1
            customer['total_spent'] += order.total_price or Decimal('0.00')

            if not customer['latest_order_at'] or order.created_at > customer['latest_order_at']:
                customer['latest_order_at'] = order.created_at

            if order.user_id:
                customer['is_registered'] = True
                customer['user_id'] = customer['user_id'] or order.user_id
                customer['username'] = customer['username'] or order.user.username
                customer['date_joined'] = customer['date_joined'] or order.user.date_joined
                if order.user.last_login and (
                    not customer['last_login'] or order.user.last_login > customer['last_login']
                ):
                    customer['last_login'] = order.user.last_login
                customer['has_logged_in'] = customer['has_logged_in'] or bool(order.user.last_login)

            if order.email and not customer['email']:
                customer['email'] = order.email.strip()

            order_name = (order.full_name or '').strip()
            if order_name and (
                not customer['full_name']
                or customer['full_name'] == customer['username']
                or customer['full_name'] == customer['email']
                or customer['full_name'] == 'Guest customer'
            ):
                customer['full_name'] = order_name

            if order.phone and not customer['phone']:
                customer['phone'] = order.phone.strip()

        customers = list(customers_map.values())

        search = self.request.GET.get('search', '').strip().lower()
        login_status = self.request.GET.get('login_status', '').strip().lower()
        order_status = self.request.GET.get('order_status', '').strip().lower()
        account_type = self.request.GET.get('account_type', '').strip().lower()

        if search:
            customers = [
                customer for customer in customers
                if search in customer['full_name'].lower()
                or search in customer['email'].lower()
                or search in customer['username'].lower()
                or search in customer['phone'].lower()
            ]

        if login_status == 'yes':
            customers = [customer for customer in customers if customer['has_logged_in']]
        elif login_status == 'no':
            customers = [customer for customer in customers if not customer['has_logged_in']]

        if order_status == 'yes':
            customers = [customer for customer in customers if customer['has_orders']]
        elif order_status == 'no':
            customers = [customer for customer in customers if not customer['has_orders']]

        if account_type == 'registered':
            customers = [customer for customer in customers if customer['is_registered']]
        elif account_type == 'guest':
            customers = [customer for customer in customers if not customer['is_registered']]

        customers.sort(
            key=lambda customer: (
                1 if customer['has_orders'] else 0,
                customer['total_orders'],
                float(customer['total_spent'] or 0),
                1 if customer['has_logged_in'] else 0,
                customer['latest_order_at'].timestamp() if customer['latest_order_at'] else 0,
                customer['last_login'].timestamp() if customer['last_login'] else 0,
                customer['date_joined'].timestamp() if customer['date_joined'] else 0,
            ),
            reverse=True,
        )

        self.total_customers_count = len(customers)
        self.logged_in_customers_count = sum(1 for customer in customers if customer['has_logged_in'])
        self.customers_with_orders_count = sum(1 for customer in customers if customer['has_orders'])
        self.registered_customers_count = sum(1 for customer in customers if customer['is_registered'])
        self.guest_customers_count = self.total_customers_count - self.registered_customers_count

        return customers

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_customers'] = getattr(self, 'total_customers_count', 0)
        context['logged_in_customers'] = getattr(self, 'logged_in_customers_count', 0)
        context['customers_with_orders'] = getattr(self, 'customers_with_orders_count', 0)
        context['registered_customers'] = getattr(self, 'registered_customers_count', 0)
        context['guest_customers'] = getattr(self, 'guest_customers_count', 0)
        return context


class CustomerDetailView(AdminOnlyMixin, View):
    """
    Customer detail view with order history.
    """
    def get(self, request, email):
        user, orders, customer_info, stats = build_customer_context(email)

        if not user and not orders.exists():
            messages.error(request, 'Customer not found.')
            return redirect('admin_panel:customers_list')
        
        context = {
            'email': email,
            'customer_info': customer_info,
            'orders': orders,
            'stats': stats,
            'has_orders': orders.exists(),
        }
        
        return render(request, 'admin/customers/detail.html', context)


class CustomerDeleteView(AdminOnlyMixin, View):
    """
    Delete a customer account and related customer orders.
    """
    template_name = 'admin/customers/confirm_delete.html'

    def get(self, request, email):
        user, orders, customer_info, stats = build_customer_context(email)

        if not user and not orders.exists():
            messages.error(request, 'Customer not found.')
            return redirect('admin_panel:customers_list')

        context = {
            'email': email,
            'customer_info': customer_info,
            'stats': stats,
            'has_orders': orders.exists(),
        }
        return render(request, self.template_name, context)

    def post(self, request, email):
        user, orders, customer_info, stats = build_customer_context(email)
        orders_to_delete = Order.objects.filter(Q(email=email) | Q(user__email=email))

        if not user and not orders.exists():
            messages.error(request, 'Customer not found.')
            return redirect('admin_panel:customers_list')

        customer_name = customer_info['full_name']
        total_orders = stats['total_orders']

        with transaction.atomic():
            if total_orders:
                orders_to_delete.delete()
            if user:
                user.delete()

        if total_orders and user:
            messages.success(
                request,
                f"Customer '{customer_name}' and {total_orders} related order(s) deleted successfully."
            )
        elif total_orders:
            messages.success(
                request,
                f"Guest customer '{customer_name}' and {total_orders} related order(s) deleted successfully."
            )
        else:
            messages.success(request, f"Customer account '{customer_name}' deleted successfully.")

        return redirect('admin_panel:customers_list')


# ==================== MESSAGING ====================

class ChatListView(AdminOnlyMixin, ListView):
    """
    List of conversations for admin.
    """
    template_name = 'admin/chat/list.html'
    context_object_name = 'conversations'
    paginate_by = 20

    def get_queryset(self):
        """Get support conversations with unread counters."""
        qs = SupportConversation.objects.select_related('user', 'admin').annotate(
            unread_count=Count('message', filter=Q(message__is_read=False) & ~Q(message__sender=self.request.user)),
            total_messages=Count('message')
        ).order_by('-updated_at')

        if self.request.user.is_superuser:
            return qs
        return qs.filter(Q(admin=self.request.user) | Q(admin__isnull=True))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_unread'] = sum((conv.unread_count or 0) for conv in context['conversations'])
        return context


class ChatDetailView(AdminOnlyMixin, View):
    """
    Chat detail view for conversation with a user.
    """
    def get(self, request, user_id):
        conversation = get_object_or_404(SupportConversation.objects.select_related('user', 'admin'), user_id=user_id)

        if not request.user.is_superuser and conversation.admin_id not in (None, request.user.id):
            messages.error(request, 'This conversation is assigned to another manager.')
            return redirect('admin_panel:chat_list')

        if conversation.admin is None:
            conversation.admin = request.user
            conversation.save(update_fields=['admin'])

        conversation.mark_as_read_for(request.user)
        chat_messages = conversation.message_set.select_related('sender').order_by('created_at')
        initial_messages = [{
            'id': msg.id,
            'sender': msg.sender.username,
            'sender_id': msg.sender.id,
            'text': msg.text,
            'file_url': msg.file.url if msg.file else None,
            'file_type': msg.get_file_type() if msg.file else None,
            'file_name': msg.file.name.split('/')[-1] if msg.file else None,
            'audio_url': msg.audio.url if msg.audio else None,
            'created_at': msg.created_at.isoformat(),
            'created_label': msg.created_at.strftime('%H:%M'),
            'is_read': msg.is_read,
            'sender_is_admin': msg.sender.is_staff,
        } for msg in chat_messages]

        context = {
            'other_user': conversation.user,
            'conversation': conversation,
            'messages': chat_messages,
            'initial_messages': initial_messages,
            'is_admin': True,
        }
        
        return render(request, 'admin/chat/detail.html', context)

    def post(self, request, user_id):
        conversation = get_object_or_404(SupportConversation, user_id=user_id)
        if not request.user.is_superuser and conversation.admin_id not in (None, request.user.id):
            messages.error(request, 'Not authorized for this conversation.')
            return redirect('admin_panel:chat_list')

        if conversation.admin is None:
            conversation.admin = request.user
            conversation.save(update_fields=['admin'])

        text = request.POST.get('text', '').strip()
        file = request.FILES.get('file')
        audio = request.FILES.get('audio')

        if text or file or audio:
            SupportMessage.objects.create(
                conversation=conversation,
                sender=request.user,
                text=text,
                file=file,
                audio=audio,
            )
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])
            messages.success(request, 'Message sent!')
        else:
            messages.error(request, 'Cannot send an empty message.')

        return redirect('admin_panel:chat_detail', user_id=user_id)


# ==================== SITE SETTINGS ====================

class SiteSettingsView(AdminOnlyMixin, UpdateView):
    """
    Site settings management.
    """
    model = SiteSettings
    form_class = SiteSettingsForm
    template_name = 'admin/settings/index.html'
    success_url = reverse_lazy('admin_panel:settings')

    def get_object(self):
        return SiteSettings.get_settings()

    def form_valid(self, form):
        # Handle social links JSON
        social_links_json = form.cleaned_data.get('social_links_json')
        if social_links_json:
            try:
                self.object.social_links = json.loads(social_links_json)
            except json.JSONDecodeError:
                self.object.social_links = {}
        
        response = super().form_valid(form)
        messages.success(self.request, 'Settings updated successfully!')
        return response


# ==================== ANALYTICS ====================

class AnalyticsDashboardView(AdminOnlyMixin, TemplateView):
    """
    Main analytics dashboard with charts.
    """
    template_name = 'admin/analytics/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ensure_recent_insights(days=7, max_age_hours=24)
        
        # Revenue by month (last 12 months)
        today = timezone.now()
        months = []
        revenues = []
        
        for i in range(11, -1, -1):
            month_start = today - timedelta(days=i*30)
            month_end = today - timedelta(days=(i-1)*30)
            
            month_revenue = Order.objects.filter(
                created_at__gte=month_start,
                created_at__lt=month_end,
                status__in=['completed', 'shipped']
            ).aggregate(total=Sum('total_price'))['total'] or 0
            
            months.append(month_start.strftime('%b %Y'))
            revenues.append(float(month_revenue))
        
        context['revenue_labels'] = json.dumps(months)
        context['revenue_data'] = json.dumps(revenues)
        
        # Top selling products
        context['top_products'] = OrderItem.objects.values(
            'product__name'
        ).annotate(
            total_sold=Sum('quantity')
        ).order_by('-total_sold')[:5]
        
        # Order status distribution
        status_dist = Order.objects.values('status').annotate(
            count=Count('id')
        )
        context['order_statuses'] = [s['status'] for s in status_dist]
        context['order_counts'] = [s['count'] for s in status_dist]
        
        # Add insights
        context['insights'] = Insight.objects.filter(is_archived=False).order_by('-generated_at')

        live_products = list(
            Product.objects.filter(is_active=True, status='active').order_by('name')
        )
        live_counts = get_live_counts([product.id for product in live_products])
        context['live_products'] = [
            {
                'product': product,
                'count': live_counts.get(product.id, 0),
            }
            for product in live_products
        ]
        context['live_window_minutes'] = LIVE_WINDOW_MINUTES
        
        return context
