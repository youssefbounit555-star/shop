from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from datetime import timedelta
from decimal import Decimal

from dashboard.models import Goal, Message
from dashboard.forms import GoalForm, MessageForm, ProfileUpdateForm, UserUpdateForm
from user.models import UserProfile
from store.models import Order, SiteSettings


class DashboardView(LoginRequiredMixin, View):
    """
    Main dashboard view showing all key information.
    """
    login_url = 'user:login'

    def get(self, request):
        user = request.user
        user_profile = UserProfile.objects.filter(user=user).first()

        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Goals
        goals_qs = Goal.objects.filter(user=user).order_by('-updated_at')
        total_goals = goals_qs.count()
        completed_goals = goals_qs.filter(completed=True).count()
        open_goals = max(total_goals - completed_goals, 0)
        goal_completion_percentage = (completed_goals / total_goals * 100) if total_goals else 0
        recent_goals = goals_qs[:6]

        # Orders
        orders_qs = (
            Order.objects.filter(user=user)
            .prefetch_related('items', 'items__product')
            .order_by('-created_at')
        )
        total_orders = orders_qs.count()
        pending_orders_count = orders_qs.filter(status='pending').count()
        processing_orders_count = orders_qs.filter(status='processing').count()
        completed_orders_count = orders_qs.filter(status='completed').count()
        cancelled_orders_count = orders_qs.filter(status='cancelled').count()
        paid_orders_count = orders_qs.filter(payment_status='completed').count()
        orders_last_7_days = orders_qs.filter(created_at__gte=week_ago).count()
        orders_last_30_days = orders_qs.filter(created_at__gte=month_ago).count()
        total_spent = orders_qs.filter(payment_status='completed').aggregate(total=Sum('total_price'))['total'] or Decimal('0')
        recent_orders = orders_qs[:6]

        pending_orders_pct = (pending_orders_count / total_orders * 100) if total_orders else 0
        processing_orders_pct = (processing_orders_count / total_orders * 100) if total_orders else 0
        completed_orders_pct = (completed_orders_count / total_orders * 100) if total_orders else 0
        cancelled_orders_pct = (cancelled_orders_count / total_orders * 100) if total_orders else 0

        # Messages / conversations
        messages_qs = (
            Message.objects.filter(Q(sender=user) | Q(receiver=user))
            .select_related('sender', 'receiver')
            .order_by('-timestamp')
        )
        total_messages = messages_qs.count()
        unread_messages = Message.objects.filter(receiver=user, is_read=False).count()

        partner_ids = []
        seen_partner_ids = set()
        for msg in messages_qs:
            other_user_id = msg.receiver_id if msg.sender_id == user.id else msg.sender_id
            if other_user_id == user.id or other_user_id in seen_partner_ids:
                continue
            seen_partner_ids.add(other_user_id)
            partner_ids.append(other_user_id)
            if len(partner_ids) >= 8:
                break

        users_by_id = {obj.id: obj for obj in User.objects.filter(id__in=partner_ids)}
        partner_profiles = {
            profile.user_id: profile
            for profile in UserProfile.objects.filter(user_id__in=partner_ids)
        }

        conversations = []
        for partner_id in partner_ids:
            partner = users_by_id.get(partner_id)
            if not partner:
                continue

            last_message = messages_qs.filter(
                Q(sender_id=user.id, receiver_id=partner_id) |
                Q(sender_id=partner_id, receiver_id=user.id)
            ).first()
            if not last_message:
                continue

            unread_count = Message.objects.filter(
                receiver=user,
                sender_id=partner_id,
                is_read=False
            ).count()
            partner_profile = partner_profiles.get(partner_id)
            display_name = partner.get_full_name() or partner.username

            conversations.append({
                'user': partner,
                'display_name': display_name,
                'avatar_url': partner_profile.avatar.url if partner_profile and partner_profile.avatar else '',
                'initials': (display_name[:1] or partner.username[:1]).upper(),
                'last_message': last_message,
                'unread': unread_count,
            })

        site_settings = SiteSettings.get_settings()

        context = {
            'user_profile': user_profile,
            'currency_label': site_settings.currency or 'USD',
            'customer_since': user.date_joined,

            # Goals
            'total_goals': total_goals,
            'completed_goals': completed_goals,
            'open_goals': open_goals,
            'goal_completion_percentage': goal_completion_percentage,

            # Messages
            'total_messages': total_messages,
            'unread_messages': unread_messages,

            # Orders
            'total_orders': total_orders,
            'pending_orders_count': pending_orders_count,
            'processing_orders_count': processing_orders_count,
            'completed_orders_count': completed_orders_count,
            'cancelled_orders_count': cancelled_orders_count,
            'paid_orders_count': paid_orders_count,
            'orders_last_7_days': orders_last_7_days,
            'orders_last_30_days': orders_last_30_days,
            'total_spent': total_spent,
            'pending_orders_pct': pending_orders_pct,
            'processing_orders_pct': processing_orders_pct,
            'completed_orders_pct': completed_orders_pct,
            'cancelled_orders_pct': cancelled_orders_pct,

            # Lists
            'goals': recent_goals,
            'recent_orders': recent_orders,
            'conversations': conversations[:6],
        }

        return render(request, 'dashboard/index.html', context)


class AddGoalView(LoginRequiredMixin, CreateView):
    """
    View for adding a new goal.
    """
    model = Goal
    form_class = GoalForm
    template_name = 'dashboard/add_goal.html'
    login_url = 'user:login'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('dashboard:index')


class ToggleGoalView(LoginRequiredMixin, View):
    """
    Toggle goal completion status (AJAX).
    """
    login_url = 'user:login'

    def post(self, request, goal_id):
        goal = get_object_or_404(Goal, id=goal_id, user=request.user)
        goal.completed = not goal.completed
        goal.save()
        
        # Calculate updated completion percentage
        total_goals = Goal.objects.filter(user=request.user).count()
        completed_goals = Goal.objects.filter(user=request.user, completed=True).count()
        completion_percentage = (completed_goals / total_goals * 100) if total_goals > 0 else 0
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'completed': goal.completed,
                'completion_percentage': completion_percentage,
                'completed_count': completed_goals,
                'total_count': total_goals
            })
        return redirect('dashboard:index')


class DeleteGoalView(LoginRequiredMixin, DeleteView):
    """
    View for deleting a goal.
    """
    model = Goal
    template_name = 'dashboard/delete_goal.html'
    login_url = 'user:login'
    success_url = reverse_lazy('dashboard:index')

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)


class ChatView(LoginRequiredMixin, View):
    """
    View for chat/messaging interface.
    """
    login_url = 'user:login'

    def get(self, request):
        user = request.user
        conversation_user_id = request.GET.get('user')
        
        # Get all conversations
        messages_sent = Message.objects.filter(sender=user).values('receiver_id').distinct()
        messages_received = Message.objects.filter(receiver=user).values('sender_id').distinct()
        
        conversation_users_ids = set()
        for msg in messages_sent:
            conversation_users_ids.add(msg['receiver_id'])
        for msg in messages_received:
            conversation_users_ids.add(msg['sender_id'])
        
        conversations = User.objects.filter(id__in=conversation_users_ids).exclude(id=user.id)
        
        # If specific user selected, get conversation with them
        messages = []
        selected_user = None
        if conversation_user_id:
            selected_user = get_object_or_404(User, id=conversation_user_id)
            messages = Message.objects.filter(
                Q(sender=user, receiver=selected_user) |
                Q(sender=selected_user, receiver=user)
            ).order_by('timestamp')
            
            # Mark messages as read
            Message.objects.filter(
                receiver=user,
                sender=selected_user,
                is_read=False
            ).update(is_read=True)
        
        context = {
            'conversations': conversations,
            'selected_user': selected_user,
            'messages': messages,
            'message_form': MessageForm(),
        }
        
        return render(request, 'dashboard/chat.html', context)


class SendMessageView(LoginRequiredMixin, View):
    """
    View for sending a message (AJAX POST).
    """
    login_url = 'user:login'

    def post(self, request):
        form = MessageForm(request.POST)
        receiver_id = request.POST.get('receiver_id')
        
        if form.is_valid() and receiver_id:
            receiver = get_object_or_404(User, id=receiver_id)
            message = form.save(commit=False)
            message.sender = request.user
            message.receiver = receiver
            message.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': message.message,
                    'timestamp': message.timestamp.isoformat(),
                })
        
        return redirect('dashboard:chat')


class GoalsView(LoginRequiredMixin, View):
    """
    View for goals/todos management.
    """
    login_url = 'user:login'

    def get(self, request):
        goals = Goal.objects.filter(user=request.user).order_by('-created_at')
        
        # Paginate goals
        paginator = Paginator(goals, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Calculate statistics
        total_goals = goals.count()
        completed_goals = goals.filter(completed=True).count()
        completion_percentage = (completed_goals / total_goals * 100) if total_goals > 0 else 0
        
        context = {
            'goals': page_obj,
            'total_goals': total_goals,
            'completed_goals': completed_goals,
            'completion_percentage': completion_percentage,
            'goal_form': GoalForm(),
        }
        
        return render(request, 'dashboard/goals.html', context)


class OrdersView(LoginRequiredMixin, View):
    """
    View for orders listing with search and pagination.
    """
    login_url = 'user:login'

    def get(self, request):
        site_settings = SiteSettings.get_settings()
        orders = (
            Order.objects.filter(user=request.user)
            .prefetch_related('items', 'items__product')
            .order_by('-created_at')
        )

        search_query = request.GET.get('search', '')
        if search_query:
            orders = orders.filter(
                Q(order_id__icontains=search_query) |
                Q(items__product__name__icontains=search_query)
            ).distinct()

        status_filter = request.GET.get('status', '')
        if status_filter:
            orders = orders.filter(status=status_filter)

        paginator = Paginator(orders, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'orders': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
            'status_choices': Order.STATUS_CHOICES,
            'currency_label': site_settings.currency or 'USD',
        }

        return render(request, 'dashboard/orders.html', context)


class ProfileWidgetView(LoginRequiredMixin, View):
    """
    Profile widget view in dashboard.
    """
    login_url = 'user:login'

    def get(self, request):
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            user_profile = None
        
        context = {
            'user': request.user,
            'user_profile': user_profile,
            'user_form': UserUpdateForm(instance=request.user),
            'profile_form': ProfileUpdateForm(instance=user_profile) if user_profile else None,
        }
        
        return render(request, 'dashboard/profile_widget.html', context)

    def post(self, request):
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            user_profile = None
        
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=user_profile) if user_profile else None
        
        if user_form.is_valid():
            user_form.save()
        
        if profile_form and profile_form.is_valid():
            profile_form.save()
        
        return redirect('dashboard:index')


class PendingOrdersView(LoginRequiredMixin, View):
    """
    View for showing pending orders that need user confirmation.
    User can review, confirm, or cancel orders here.
    """
    login_url = 'user:login'

    def get(self, request):
        user = request.user
        
        # Get pending orders (not yet confirmed/shipped)
        pending_orders = Order.objects.filter(
            user=user,
            status='pending'
        ).prefetch_related('items', 'items__product').order_by('-created_at')
        
        context = {
            'pending_orders': pending_orders,
            'pending_count': pending_orders.count(),
        }
        
        return render(request, 'dashboard/pending_orders.html', context)


class ConfirmOrderView(LoginRequiredMixin, View):
    """
    View to confirm a pending order and reduce stock.
    """
    login_url = 'user:login'

    def post(self, request, order_id):
        from django.contrib import messages as django_messages
        
        user = request.user
        order = get_object_or_404(Order, id=order_id, user=user, status='pending')
        
        # Reduce stock for all items in the order
        for item in order.items.all():
            product = item.product
            if product.stock_quantity >= item.quantity:
                product.stock_quantity -= item.quantity
                product.save()
            else:
                django_messages.error(
                    request,
                    f'Insufficient stock for {product.name}. Unable to confirm order.'
                )
                return redirect('dashboard:pending_orders')
        
        # Mark order as confirmed (processing)
        order.status = 'processing'
        order.save()
        
        django_messages.success(
            request,
            f'Order {order.order_id} confirmed successfully! We will contact you soon.'
        )
        return redirect('dashboard:pending_orders')


class CancelOrderView(LoginRequiredMixin, View):
    """
    View to cancel a pending order and remove it.
    """
    login_url = 'user:login'

    def post(self, request, order_id):
        from django.contrib import messages as django_messages
        
        user = request.user
        order = get_object_or_404(Order, id=order_id, user=user, status='pending')
        
        # Cancel the order
        order.status = 'cancelled'
        order.save()
        
        django_messages.info(
            request,
            f'Order {order.order_id} has been cancelled.'
        )
        return redirect('dashboard:pending_orders')
