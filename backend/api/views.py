from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
import logging

from .models import Ticket, TicketComment, TicketAttachment, TicketCollaborator, Notification, ActivityLog, Department, Product
from notifications import notify_user  # Unified notification (Telegram + Email)

logger = logging.getLogger(__name__)


class TicketPagination(PageNumberPagination):
    """
    Custom pagination for tickets with configurable page size.
    Supports ?page_size=10|25|50|100 query parameter.
    """
    page_size = 20  # Default
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


from .serializers import (
    UserSerializer, UserCreateSerializer, UserMinimalSerializer, UserManagementSerializer,
    TicketListSerializer, TicketDetailSerializer, TicketCreateSerializer,
    TicketUpdateSerializer, TicketAssignSerializer, TicketRejectSerializer,
    TicketCommentSerializer, TicketAttachmentSerializer, TicketCollaboratorSerializer,
    NotificationSerializer, DashboardStatsSerializer, ActivityLogSerializer,
    DepartmentSerializer, ProductSerializer, ChangePasswordSerializer, UpdateUserProfileSerializer,
    RevisionRequestSerializer
)


def log_activity(user, ticket, action, details=''):
    """Helper function to log activity with ticket state snapshot for rollback"""
    # Capture ticket state snapshot
    snapshot = {
        'status': ticket.status,
        'assigned_to_id': ticket.assigned_to_id,
        'approver_id': ticket.approver_id,
        'pending_approver_id': ticket.pending_approver_id,
        'dept_approver_id': ticket.dept_approver_id,
        'priority': ticket.priority,
        'deadline': ticket.deadline.isoformat() if ticket.deadline else None,
        'target_department_id': ticket.target_department_id,
        'ticket_product_id': ticket.ticket_product_id,
        'complexity': ticket.complexity,
        'estimated_hours': str(ticket.estimated_hours) if ticket.estimated_hours else None,
        'actual_hours': str(ticket.actual_hours) if ticket.actual_hours else None,
        'request_type': ticket.request_type,
        'file_format': ticket.file_format,
        'revision_count': ticket.revision_count,
    }
    ActivityLog.objects.create(
        user=user,
        ticket=ticket,
        action=action,
        details=details,
        snapshot=snapshot
    )


def calculate_deadline_from_priority(priority, file_format=None, criteria=None):
    """
    Calculate deadline based on priority and media type (video vs image/still).
    - Urgent: 3hrs for video, 2hrs for still/image
    - High: 24hrs
    - Medium: 72hrs
    - Low: 168hrs (7 days)

    Video detection:
    1. First checks criteria field ('video' = video)
    2. Falls back to file_format ('video_landscape', 'video_portrait' = video)
    3. Defaults to still/image (2 hours for urgent)
    """
    # Check criteria first (new field), then fall back to file_format
    is_video = False
    if criteria:
        is_video = criteria == 'video'
    elif file_format:
        is_video = file_format in ['video_landscape', 'video_portrait']

    hours_map = {
        'urgent': 3 if is_video else 2,
        'high': 24,
        'medium': 72,
        'low': 168,
    }

    hours = hours_map.get(priority, 72)  # Default to medium (72 hours)
    return timezone.now() + timedelta(hours=hours)


def format_notification_message(ticket, action, extra_info=None):
    """
    Format notification message with ticket context.
    Format: #{id} - {title} ({priority}) - {action}
    """
    base = f'#{ticket.id} - {ticket.title} ({ticket.get_priority_display()})'

    messages = {
        'needs_dept_approval': f'{base} - needs your department approval',
        'needs_creative_approval': f'{base} - needs your Creative approval',
        'dept_approved': f'{base} - approved by department, pending Creative',
        'approved': f'{base} - has been fully approved',
        'rejected': f'{base} - has been rejected' + (f': {extra_info}' if extra_info else ''),
        'assigned': f'{base} - has been assigned to you',
        'started': f'{base} - work has started',
        'completed': f'{base} - has been completed, please confirm',
        'confirmed': f'{base} - completion confirmed by requester',
        'revision': f'{base} - revision requested' + (f': {extra_info[:100]}' if extra_info else ''),
        'comment': f'{base} - new comment added',
        'collaborator': f'{base} - you have been added as collaborator',
        'rollback': f'{base} - has been rolled back',
        'restored': f'{base} - has been restored from trash',
        'reminder': f'{base} - awaiting your approval (reminder)',
    }
    return messages.get(action, f'{base} - {action}')


from .permissions import IsAdminUser, IsManagerUser, IsTicketOwnerOrManager, CanApproveTicket

User = get_user_model()


# =====================
# AUTH VIEWS
# =====================

class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data['message'] = 'Registration successful. Please wait for admin approval before logging in.'
        return response


class CustomTokenObtainPairView(APIView):
    """Custom login view that checks if user is approved and handles account lockout"""
    permission_classes = [AllowAny]

    MAX_LOGIN_ATTEMPTS = 3
    LOCKOUT_DURATION_MINUTES = 30

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def log_attempt(self, username, success, failure_reason='', request=None):
        from .models import LoginAttempt
        LoginAttempt.objects.create(
            username=username,
            ip_address=self.get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
            success=success,
            failure_reason=failure_reason
        )

    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        from django.contrib.auth import authenticate
        from datetime import timedelta

        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'detail': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user exists and is locked
        try:
            user_check = User.objects.get(username=username)

            # Check if account is locked
            if user_check.is_locked:
                # Check if lockout period has passed
                if user_check.locked_at:
                    unlock_time = user_check.locked_at + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                    if timezone.now() >= unlock_time:
                        # Unlock account
                        user_check.is_locked = False
                        user_check.locked_at = None
                        user_check.failed_login_attempts = 0
                        user_check.save()
                    else:
                        minutes_left = int((unlock_time - timezone.now()).total_seconds() / 60)
                        self.log_attempt(username, False, 'Account locked', request)
                        return Response(
                            {'detail': f'Account is locked due to multiple failed login attempts. Try again in {minutes_left + 1} minutes, or contact admin to unlock.'},
                            status=status.HTTP_423_LOCKED
                        )
        except User.DoesNotExist:
            pass

        user = authenticate(username=username, password=password)

        if user is None:
            # Track failed attempt
            try:
                user_obj = User.objects.get(username=username)
                user_obj.failed_login_attempts += 1
                user_obj.last_failed_login = timezone.now()

                if user_obj.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
                    user_obj.is_locked = True
                    user_obj.locked_at = timezone.now()
                    user_obj.save()
                    self.log_attempt(username, False, 'Account locked after max attempts', request)
                    return Response(
                        {'detail': f'Account locked due to {self.MAX_LOGIN_ATTEMPTS} failed login attempts. Contact admin to unlock or wait {self.LOCKOUT_DURATION_MINUTES} minutes.'},
                        status=status.HTTP_423_LOCKED
                    )

                user_obj.save()
                remaining = self.MAX_LOGIN_ATTEMPTS - user_obj.failed_login_attempts
                self.log_attempt(username, False, 'Invalid password', request)
                return Response(
                    {'detail': f'Invalid credentials. {remaining} attempt(s) remaining before account lockout.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            except User.DoesNotExist:
                self.log_attempt(username, False, 'User not found', request)

            return Response(
                {'detail': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            self.log_attempt(username, False, 'Account deactivated', request)
            return Response(
                {'detail': 'Account is deactivated. Contact administrator.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_approved:
            self.log_attempt(username, False, 'Account not approved', request)
            return Response(
                {'detail': 'Account pending approval. Please wait for admin to approve your registration.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.last_failed_login = None
        user.save()

        self.log_attempt(username, True, '', request)

        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class MeView(generics.RetrieveUpdateAPIView):
    """Get/update current user profile"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all as list for dropdowns

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    """List all users (for assignment dropdown)"""
    serializer_class = UserMinimalSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all as list for dropdowns

    def get_queryset(self):
        # Only return approved and active users for assignment
        return User.objects.filter(is_active=True, is_approved=True)


# =====================
# USER MANAGEMENT VIEWS
# =====================

class UserManagementViewSet(viewsets.ModelViewSet):
    """Admin user management - list, approve, change roles"""
    pagination_class = None  # Show all users without pagination
    serializer_class = UserSerializer
    permission_classes = [IsManagerUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAdminUser()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Create a new user (admin only) - auto-approved"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Auto-approve users created by admin
        user.is_approved = True
        user.approved_by = request.user
        user.approved_at = timezone.now()

        # Set role if provided
        role = request.data.get('role', 'member')
        if role in [User.Role.ADMIN, User.Role.MANAGER, User.Role.MEMBER]:
            user.role = role

        user.save()

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')

        # Filter by approval status
        approval_filter = self.request.query_params.get('is_approved')
        if approval_filter is not None:
            queryset = queryset.filter(is_approved=approval_filter.lower() == 'true')

        # Filter by role
        role_filter = self.request.query_params.get('role')
        if role_filter:
            queryset = queryset.filter(role=role_filter)

        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsManagerUser])
    def approve(self, request, pk=None):
        """Approve a user registration"""
        user = self.get_object()

        if user.is_approved:
            return Response(
                {'error': 'User is already approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_approved = True
        user.approved_by = request.user
        user.approved_at = timezone.now()
        user.save()

        # Send Telegram notification if user has telegram_id
        if user.telegram_id:
            from notifications.telegram import send_telegram_message
            send_telegram_message(
                user.telegram_id,
                f"🎉 Your account has been approved! You can now login to Juan365 Ticketing System."
            )

        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'], permission_classes=[IsManagerUser])
    def reject_user(self, request, pk=None):
        """Reject/deactivate a user"""
        user = self.get_object()

        if user == request.user:
            return Response(
                {'error': 'Cannot deactivate yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = False
        user.is_approved = False
        user.save()

        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'], permission_classes=[IsManagerUser])
    def change_role(self, request, pk=None):
        """Change user role"""
        user = self.get_object()
        new_role = request.data.get('role')

        if new_role not in [User.Role.ADMIN, User.Role.MANAGER, User.Role.MEMBER]:
            return Response(
                {'error': 'Invalid role. Must be admin, manager, or member'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user == request.user and new_role != User.Role.ADMIN:
            return Response(
                {'error': 'Cannot demote yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.role = new_role
        user.save()

        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'], permission_classes=[IsManagerUser])
    def reactivate(self, request, pk=None):
        """Reactivate a deactivated user"""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'], permission_classes=[IsManagerUser])
    def reset_password(self, request, pk=None):
        """Reset user password (admin only)"""
        user = self.get_object()
        new_password = request.data.get('password')

        if not new_password:
            return Response(
                {'error': 'Password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return Response(
                {'error': 'Password must be at least 6 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response({
            'message': f'Password reset successfully for {user.username}',
            'user': UserSerializer(user).data
        })

    @action(detail=True, methods=['patch'], permission_classes=[IsManagerUser])
    def update_profile(self, request, pk=None):
        """Update user profile (name, email, telegram, department)"""
        user = self.get_object()
        serializer = UpdateUserProfileSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': UserSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], permission_classes=[IsManagerUser])
    def delete_user(self, request, pk=None):
        """Permanently delete a user (admin only)"""
        user = self.get_object()
        
        # Prevent deleting yourself
        if user == request.user:
            return Response(
                {'error': 'Cannot delete your own account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        username = user.username
        user.delete()

        return Response({
            'message': f'User {username} deleted successfully'
        })

    @action(detail=True, methods=['post'], permission_classes=[IsManagerUser])
    def unlock_account(self, request, pk=None):
        """Unlock a locked user account (admin/manager only)"""
        user = self.get_object()

        if not user.is_locked:
            return Response(
                {'error': 'Account is not locked'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_locked = False
        user.locked_at = None
        user.failed_login_attempts = 0
        user.last_failed_login = None
        user.save()

        return Response({
            'message': f'Account unlocked successfully for {user.username}',
            'user': UserSerializer(user).data
        })


class ForgotPasswordView(APIView):
    """Request password reset token"""
    permission_classes = [AllowAny]

    def post(self, request):
        import secrets
        from datetime import timedelta
        from .models import PasswordResetToken

        username = request.data.get('username')
        email = request.data.get('email')

        if not username and not email:
            return Response(
                {'error': 'Username or email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if username:
                user = User.objects.get(username=username)
            else:
                user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if user exists
            return Response({
                'message': 'If the account exists, a password reset token has been generated. Contact admin to get the token.'
            })

        # Generate reset token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)

        # Invalidate previous tokens
        PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

        # Create new token
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

        # In production, this would send an email
        # For now, admin can view tokens in admin panel
        return Response({
            'message': 'Password reset token generated. Contact admin to get the token.',
            # Only show token if request is from admin
            'token': token if request.user.is_authenticated and request.user.is_admin else None
        })


class ResetPasswordView(APIView):
    """Reset password using token"""
    permission_classes = [AllowAny]

    def post(self, request):
        from .models import PasswordResetToken

        token = request.data.get('token')
        new_password = request.data.get('password')

        if not token or not new_password:
            return Response(
                {'error': 'Token and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return Response(
                {'error': 'Password must be at least 6 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            reset_token = PasswordResetToken.objects.get(token=token)
        except PasswordResetToken.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not reset_token.is_valid:
            return Response(
                {'error': 'Token has expired or already been used'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset password
        user = reset_token.user
        user.set_password(new_password)
        user.is_locked = False
        user.failed_login_attempts = 0
        user.save()

        # Mark token as used
        reset_token.is_used = True
        reset_token.used_at = timezone.now()
        reset_token.save()

        return Response({
            'message': 'Password reset successfully. You can now login with your new password.'
        })


# =====================
# DEPARTMENT & PRODUCT VIEWS
# =====================

class PublicDepartmentListView(generics.ListAPIView):
    """Public endpoint to list active departments (for registration)"""
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Department.objects.filter(is_active=True).order_by('name')


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    Department CRUD operations

    - list: Get all departments (any authenticated user)
    - create: Create department (admin only)
    - update: Update department (admin only)
    - destroy: Delete department (admin only)
    """
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all as list for dropdowns

    # Cache list for 1 hour (departments rarely change)
    @method_decorator(cache_page(3600))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Department.objects.all()

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Filter by is_creative flag
        is_creative = self.request.query_params.get('is_creative')
        if is_creative is not None:
            queryset = queryset.filter(is_creative=is_creative.lower() == 'true')

        return queryset.order_by('name')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()

    @action(detail=True, methods=['post'], permission_classes=[IsManagerUser])
    def set_manager(self, request, pk=None):
        """Set the department manager"""
        department = self.get_object()
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            manager = User.objects.get(id=user_id, is_active=True, is_approved=True)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found or not active'},
                status=status.HTTP_404_NOT_FOUND
            )

        department.manager = manager
        department.save()

        return Response(DepartmentSerializer(department).data)


class ProductViewSet(viewsets.ModelViewSet):
    """
    Product CRUD operations

    - list: Get all products (any authenticated user)
    - create: Create product (admin only)
    - update: Update product (admin only)
    - destroy: Delete product (admin only)
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all as list for dropdowns

    # Cache list for 1 hour (products rarely change)
    @method_decorator(cache_page(3600))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Product.objects.all()

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Filter by category (general, ads, telegram)
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        return queryset.order_by('name')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()


# =====================
# TICKET VIEWS
# =====================

class TicketViewSet(viewsets.ModelViewSet):
    """
    Ticket CRUD operations

    list: Get all tickets (filtered by user role)
    create: Create a new ticket request
    retrieve: Get ticket details
    update: Update ticket (owner or manager only)
    destroy: Delete ticket (owner or manager only)

    Pagination: Use ?page=1&page_size=20 (max 100)
    """
    permission_classes = [IsAuthenticated]
    pagination_class = TicketPagination

    def get_queryset(self):
        user = self.request.user
        # Optimize queries with select_related for foreign keys and annotate counts
        queryset = Ticket.objects.select_related(
            'requester', 'requester__user_department',
            'assigned_to', 'assigned_to__user_department',
            'approver', 'approver__user_department',
            'pending_approver', 'pending_approver__user_department',
            'dept_approver',
            'target_department',
            'ticket_product',
            'deleted_by'
        ).prefetch_related(
            'product_items', 'product_items__product',  # For Ads/Telegram multi-product support
            'collaborators', 'collaborators__user'  # For user count display
        ).annotate(
            # Annotate counts to avoid N+1 queries in serializers
            comment_count_annotated=Count('comments', distinct=True),
            attachment_count_annotated=Count('attachments', distinct=True)
        )

        # Filter out deleted tickets by default (unless viewing trash)
        include_deleted = self.request.query_params.get('include_deleted', 'false').lower() == 'true'
        if not include_deleted:
            queryset = queryset.filter(is_deleted=False)

        # Admins and managers see all tickets
        if user.is_manager:
            pass
        else:
            # Regular users see their own requests, assigned tickets, and tickets they collaborate on
            queryset = queryset.filter(
                Q(requester=user) | Q(assigned_to=user) | Q(collaborators__user=user)
            ).distinct()

        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)

        assigned_filter = self.request.query_params.get('assigned_to')
        if assigned_filter:
            queryset = queryset.filter(assigned_to_id=assigned_filter)

        overdue_filter = self.request.query_params.get('overdue')
        if overdue_filter == 'true':
            queryset = queryset.filter(
                deadline__lt=timezone.now()
            ).exclude(status__in=[Ticket.Status.COMPLETED, Ticket.Status.REJECTED])

        # Search filter (title and description)
        search_query = self.request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(description__icontains=search_query)
            )

        # Date range filters
        created_after = self.request.query_params.get('created_after')
        if created_after:
            queryset = queryset.filter(created_at__date__gte=created_after)

        created_before = self.request.query_params.get('created_before')
        if created_before:
            queryset = queryset.filter(created_at__date__lte=created_before)

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return TicketListSerializer
        elif self.action == 'create':
            return TicketCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TicketUpdateSerializer
        return TicketDetailSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsTicketOwnerOrManager()]
        return super().get_permissions()

    def perform_create(self, serializer):
        """
        Create ticket with smart approval routing based on requester's department.

        Flow:
        1. Creative Manager creates → Auto-approve (status=APPROVED)
        2. Creative member (non-manager) creates → Skip dept approval → PENDING_CREATIVE
        3. Non-Creative user creates → REQUESTED → needs dept manager approval first
        """
        from .models import Department, TicketAnalytics

        requester = self.request.user

        # Validate department restriction: only admins can submit to any department
        target_department_id = serializer.validated_data.get('target_department')
        if target_department_id and not requester.is_admin:
            user_dept = requester.user_department
            if user_dept and target_department_id.id != user_dept.id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You can only submit tickets to your own department.")

        ticket = serializer.save(requester=requester)

        # Auto-set criteria based on request_type for scheduled tasks
        if ticket.request_type == 'videoshoot':
            ticket.criteria = 'video'
        elif ticket.request_type == 'photoshoot':
            ticket.criteria = 'image'
        elif ticket.request_type == 'live_production':
            ticket.criteria = 'video'  # Live production is typically video

        # Get Creative department info (use filter().first() to handle multiple or none)
        creative_dept = Department.objects.filter(is_creative=True).first()
        creative_manager = creative_dept.manager if creative_dept else None

        # Check requester's department relationship
        requester_dept = requester.user_department
        is_in_creative_dept = requester_dept and requester_dept.is_creative
        is_creative_manager = creative_manager and (creative_manager == requester)

        if is_creative_manager:
            # Creative Manager creates ticket → Auto-approve
            ticket.status = Ticket.Status.APPROVED
            ticket.approver = requester
            ticket.approved_at = timezone.now()
            ticket.pending_approver = None
            log_activity(requester, ticket, ActivityLog.ActionType.APPROVED, 'Auto-approved (Creative Manager)')

        elif is_in_creative_dept:
            # Creative member (non-manager) creates ticket → Skip dept approval
            # Go directly to PENDING_CREATIVE for Creative Manager approval
            ticket.status = Ticket.Status.PENDING_CREATIVE
            if creative_manager:
                ticket.pending_approver = creative_manager
                # Notify Creative Manager
                Notification.objects.create(
                    user=creative_manager,
                    ticket=ticket,
                    message=format_notification_message(ticket, 'needs_creative_approval'),
                    notification_type=Notification.NotificationType.NEW_REQUEST
                )
                notify_user(creative_manager, 'new_request', ticket, actor=requester)

        else:
            # Non-Creative user creates ticket → needs dept manager approval first
            ticket.status = Ticket.Status.REQUESTED
            if requester_dept and requester_dept.manager:
                ticket.pending_approver = requester_dept.manager
                # Notify Department Manager
                Notification.objects.create(
                    user=requester_dept.manager,
                    ticket=ticket,
                    message=format_notification_message(ticket, 'needs_dept_approval'),
                    notification_type=Notification.NotificationType.NEW_REQUEST
                )
                notify_user(requester_dept.manager, 'new_request', ticket, actor=requester)

        ticket.save()

        # Create analytics record
        TicketAnalytics.objects.create(
            ticket=ticket,
            created_at=ticket.created_at
        )

        # Log creation
        log_activity(requester, ticket, ActivityLog.ActionType.CREATED)

    # =====================
    # TICKET ACTIONS
    # =====================

    @action(detail=True, methods=['post'], permission_classes=[CanApproveTicket])
    def approve(self, request, pk=None):
        """
        Two-step approval workflow with strict department checks:

        Step 1 (REQUESTED → PENDING_CREATIVE):
        - ONLY allows same-department manager as the ticket creator
        - Creative dept users CANNOT approve at this step

        Step 2 (PENDING_CREATIVE → APPROVED):
        - ONLY allows Creative department users (manager or admin)
        - Non-Creative users CANNOT approve at this step
        """
        ticket = self.get_object()
        user = request.user

        # Get Creative department info (use filter().first() to handle multiple or none)
        creative_dept = Department.objects.filter(is_creative=True).first()
        creative_manager = creative_dept.manager if creative_dept else None

        # Check if user is in Creative department
        user_dept = user.user_department
        is_in_creative_dept = user_dept and user_dept.is_creative
        is_creative_manager = creative_manager and (creative_manager == user)

        # Handle PENDING_CREATIVE status - ONLY Creative dept users can approve
        if ticket.status == Ticket.Status.PENDING_CREATIVE:
            if not is_in_creative_dept and not user.is_admin:
                return Response(
                    {'error': 'Only Creative department users can give final approval'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Final approval by Creative
            ticket.status = Ticket.Status.APPROVED
            ticket.approver = user
            ticket.approved_at = timezone.now()
            ticket.pending_approver = None
            ticket.save()

            # Update analytics
            if hasattr(ticket, 'analytics'):
                ticket.analytics.creative_approved_at = timezone.now()
                ticket.analytics.save()

            # Log activity
            log_activity(user, ticket, ActivityLog.ActionType.APPROVED, 'Final approval by Creative')

            # Notify requester
            Notification.objects.create(
                user=ticket.requester,
                ticket=ticket,
                message=format_notification_message(ticket, 'approved'),
                notification_type=Notification.NotificationType.APPROVED
            )
            notify_user(ticket.requester, 'approved', ticket, actor=user)

            # Notify department approver if exists
            if ticket.dept_approver and ticket.dept_approver != user:
                Notification.objects.create(
                    user=ticket.dept_approver,
                    ticket=ticket,
                    message=format_notification_message(ticket, 'approved'),
                    notification_type=Notification.NotificationType.APPROVED
                )

            return Response(TicketDetailSerializer(ticket).data)

        # Handle REQUESTED status
        if ticket.status != Ticket.Status.REQUESTED:
            return Response(
                {'error': 'Only requested or pending creative tickets can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # For REQUESTED status: Check if approver is from same department as creator
        requester_dept = ticket.requester.user_department

        # Creative dept users should NOT approve REQUESTED tickets (that's for dept managers)
        if is_in_creative_dept and not user.is_admin:
            return Response(
                {'error': 'Creative department users cannot approve at this step. Only the creator\'s department manager can approve first.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if user is manager of creator's department
        is_same_dept_manager = (
            user_dept and requester_dept and
            user_dept.id == requester_dept.id and
            (requester_dept.manager == user or user.is_manager)
        )

        # Admin can also approve
        if not is_same_dept_manager and not user.is_admin:
            return Response(
                {'error': f'Only the creator\'s department manager ({requester_dept.name if requester_dept else "unknown"}) can approve this ticket'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Department Manager approves → PENDING_CREATIVE (first approval)
        ticket.status = Ticket.Status.PENDING_CREATIVE
        ticket.dept_approver = user
        ticket.dept_approved_at = timezone.now()

        # Set pending approver to Creative Manager
        if creative_manager:
            ticket.pending_approver = creative_manager

        ticket.save()

        # Update analytics
        if hasattr(ticket, 'analytics'):
            ticket.analytics.dept_approved_at = timezone.now()
            ticket.analytics.save()

        # Log activity
        log_activity(user, ticket, ActivityLog.ActionType.DEPT_APPROVED, f'Department approval by {user_dept.name if user_dept else "Admin"}')

        # Notify requester of first approval
        Notification.objects.create(
            user=ticket.requester,
            ticket=ticket,
            message=format_notification_message(ticket, 'dept_approved'),
            notification_type=Notification.NotificationType.PENDING_CREATIVE
        )
        notify_user(ticket.requester, 'pending_creative', ticket, actor=user)

        # Notify Creative Manager for second approval
        if ticket.pending_approver:
            Notification.objects.create(
                user=ticket.pending_approver,
                ticket=ticket,
                message=format_notification_message(ticket, 'needs_creative_approval'),
                notification_type=Notification.NotificationType.PENDING_CREATIVE
            )
            notify_user(ticket.pending_approver, 'pending_creative', ticket, actor=user)

        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=['post'], permission_classes=[CanApproveTicket])
    def reject(self, request, pk=None):
        """Reject a ticket request (can reject REQUESTED or PENDING_CREATIVE)"""
        ticket = self.get_object()
        serializer = TicketRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if ticket.status not in [Ticket.Status.REQUESTED, Ticket.Status.PENDING_CREATIVE]:
            return Response(
                {'error': 'Only requested or pending creative tickets can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.status = Ticket.Status.REJECTED
        ticket.approver = request.user
        ticket.rejected_at = timezone.now()
        ticket.save()

        reason = serializer.validated_data.get('reason', '')

        # Log activity
        log_activity(request.user, ticket, ActivityLog.ActionType.REJECTED, reason)

        Notification.objects.create(
            user=ticket.requester,
            ticket=ticket,
            message=format_notification_message(ticket, 'rejected', reason),
            notification_type=Notification.NotificationType.REJECTED
        )
        # Send Telegram notification
        notify_user(ticket.requester, 'rejected', ticket, reason, actor=request.user)

        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=['post'], permission_classes=[CanApproveTicket])
    def assign(self, request, pk=None):
        """
        Assign ticket to a user.
        RESTRICTION: Can ONLY assign to Creative department members.
        Auto-calculates deadline based on priority when assigned.
        """
        ticket = self.get_object()
        serializer = TicketAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assigned_user = serializer.validated_data['assigned_to']

        # RESTRICTION: Only allow assignment to Creative department members
        if not assigned_user.user_department or not assigned_user.user_department.is_creative:
            return Response(
                {'error': f'Can only assign tickets to Creative department members. {assigned_user.username} is not in Creative department.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.assigned_to = assigned_user
        ticket.assigned_at = timezone.now()

        # Check if this is a scheduled task (videoshoot, photoshoot, live_production)
        scheduled_request_types = ['videoshoot', 'photoshoot', 'live_production']
        if ticket.request_type in scheduled_request_types:
            # For scheduled tasks, only set scheduled_start
            # scheduled_end and actual_end are auto-set when marked complete
            scheduled_start = serializer.validated_data.get('scheduled_start')
            if scheduled_start:
                ticket.scheduled_start = scheduled_start
            # No auto-deadline for scheduled tasks - end time determined on completion
        else:
            # Auto-calculate deadline based on priority and media type (video vs image)
            # Uses criteria field first, falls back to file_format
            # Deadline timer starts when ticket is assigned
            ticket.deadline = calculate_deadline_from_priority(
                ticket.priority,
                file_format=ticket.file_format,
                criteria=ticket.criteria
            )

        ticket.save()

        # Update analytics
        if hasattr(ticket, 'analytics'):
            ticket.analytics.assigned_at = timezone.now()
            ticket.analytics.save()

        # Log activity with deadline/schedule info
        if ticket.request_type in scheduled_request_types:
            schedule_info = ticket.scheduled_start.strftime('%Y-%m-%d %H:%M') if ticket.scheduled_start else 'N/A'
            log_activity(request.user, ticket, ActivityLog.ActionType.ASSIGNED,
                        f'Assigned to {ticket.assigned_to.username}. Scheduled: {schedule_info}')
            message = f'Ticket "#{ticket.id} - {ticket.title}" has been assigned to you. Scheduled: {schedule_info}'
        else:
            deadline_info = ticket.deadline.strftime('%Y-%m-%d %H:%M') if ticket.deadline else 'N/A'
            log_activity(request.user, ticket, ActivityLog.ActionType.ASSIGNED,
                        f'Assigned to {ticket.assigned_to.username}. Deadline: {deadline_info}')
            message = f'Ticket "#{ticket.id} - {ticket.title}" has been assigned to you. Deadline: {deadline_info}'

        Notification.objects.create(
            user=ticket.assigned_to,
            ticket=ticket,
            message=message,
            notification_type=Notification.NotificationType.ASSIGNED
        )
        # Send Telegram notification
        notify_user(ticket.assigned_to, 'assigned', ticket, actor=request.user)

        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Start working on a ticket (Designer acknowledges/starts editing).
        This action:
        1. Changes status to IN_PROGRESS
        2. Records acknowledgment time for analytics
        3. Triggers the deadline countdown (already set on assignment)
        """
        ticket = self.get_object()

        # Ticket must be assigned first
        if not ticket.assigned_to:
            return Response(
                {'error': 'Ticket must be assigned before starting work'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user is assigned or a collaborator
        is_collaborator = ticket.collaborators.filter(user=request.user).exists()
        if ticket.assigned_to != request.user and not is_collaborator:
            return Response(
                {'error': 'Only assigned users or collaborators can start this ticket'},
                status=status.HTTP_403_FORBIDDEN
            )

        if ticket.status != Ticket.Status.APPROVED:
            return Response(
                {'error': 'Ticket must be approved before starting work'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.status = Ticket.Status.IN_PROGRESS
        ticket.started_at = timezone.now()
        ticket.save()

        # Update analytics - record acknowledgment time
        if hasattr(ticket, 'analytics'):
            ticket.analytics.acknowledged_at = timezone.now()
            ticket.analytics.started_at = timezone.now()
            # Calculate time from assignment to acknowledgment (in seconds for precision)
            if ticket.analytics.assigned_at:
                ticket.analytics.time_to_acknowledge = int(
                    (timezone.now() - ticket.analytics.assigned_at).total_seconds()
                )
            ticket.analytics.save()

        # Log activity
        log_activity(request.user, ticket, ActivityLog.ActionType.STARTED, 'Designer acknowledged and started editing')

        # Notify requester that work has started
        if ticket.requester != request.user:
            Notification.objects.create(
                user=ticket.requester,
                ticket=ticket,
                message=format_notification_message(ticket, 'started'),
                notification_type=Notification.NotificationType.APPROVED
            )
            notify_user(ticket.requester, 'started', ticket, actor=request.user)

        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark ticket as completed"""
        ticket = self.get_object()

        # Check if user is assigned, collaborator, or manager
        is_collaborator = ticket.collaborators.filter(user=request.user).exists()
        if ticket.assigned_to != request.user and not is_collaborator and not request.user.is_manager:
            return Response(
                {'error': 'Only assigned users or collaborators can complete this ticket'},
                status=status.HTTP_403_FORBIDDEN
            )

        if ticket.status != Ticket.Status.IN_PROGRESS:
            return Response(
                {'error': 'Only in-progress tickets can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.status = Ticket.Status.COMPLETED
        ticket.completed_at = timezone.now()

        # For scheduled tasks (videoshoot, photoshoot, live_production),
        # use provided actual_end or default to current time
        scheduled_types = ['videoshoot', 'photoshoot', 'live_production']
        if ticket.request_type in scheduled_types:
            # Check if actual_end was provided in request
            actual_end_str = request.data.get('actual_end')
            if actual_end_str:
                from django.utils.dateparse import parse_datetime
                parsed_end = parse_datetime(actual_end_str)
                if parsed_end:
                    # Make timezone aware if naive
                    if parsed_end.tzinfo is None:
                        from django.utils import timezone as tz
                        parsed_end = tz.make_aware(parsed_end)
                    ticket.actual_end = parsed_end
                    ticket.scheduled_end = parsed_end
                else:
                    ticket.actual_end = timezone.now()
                    ticket.scheduled_end = timezone.now()
            else:
                ticket.actual_end = timezone.now()
                ticket.scheduled_end = timezone.now()

        ticket.save()

        # Update analytics
        if hasattr(ticket, 'analytics'):
            ticket.analytics.completed_at = timezone.now()
            ticket.analytics.calculate_durations()
            ticket.analytics.save()

        # Log activity
        log_activity(request.user, ticket, ActivityLog.ActionType.COMPLETED)

        # Notify requester
        if ticket.requester != request.user:
            Notification.objects.create(
                user=ticket.requester,
                ticket=ticket,
                message=format_notification_message(ticket, 'completed'),
                notification_type=Notification.NotificationType.APPROVED
            )
            # Send Telegram notification
            notify_user(ticket.requester, 'completed', ticket, actor=request.user)

        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Requester confirms task completion"""
        ticket = self.get_object()

        if ticket.requester != request.user:
            return Response(
                {'error': 'Only the requester can confirm completion'},
                status=status.HTTP_403_FORBIDDEN
            )

        if ticket.status != Ticket.Status.COMPLETED:
            return Response(
                {'error': 'Only completed tickets can be confirmed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if ticket.confirmed_by_requester:
            return Response(
                {'error': 'This ticket has already been confirmed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.confirmed_by_requester = True
        ticket.confirmed_at = timezone.now()
        ticket.save()

        # Update analytics
        if hasattr(ticket, 'analytics'):
            ticket.analytics.confirmed_at = timezone.now()
            ticket.analytics.calculate_durations()
            ticket.analytics.save()

        # Log activity
        log_activity(request.user, ticket, ActivityLog.ActionType.CONFIRMED)

        # Notify assigned user
        if ticket.assigned_to and ticket.assigned_to != request.user:
            Notification.objects.create(
                user=ticket.assigned_to,
                ticket=ticket,
                message=format_notification_message(ticket, 'confirmed'),
                notification_type=Notification.NotificationType.APPROVED
            )
            # Send Telegram notification
            notify_user(ticket.assigned_to, 'confirmed', ticket, actor=request.user)

        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=['post'])
    def request_revision(self, request, pk=None):
        """
        Requester requests revision on a completed ticket.
        This sends the ticket back to IN_PROGRESS status with revision comments.
        Tracks revision count and history.
        """
        ticket = self.get_object()
        serializer = RevisionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Only requester or collaborators can request revision
        is_requester = ticket.requester == request.user
        is_collaborator = ticket.collaborators.filter(user=request.user).exists()

        if not is_requester and not is_collaborator and not request.user.is_manager:
            return Response(
                {'error': 'Only the requester or collaborators can request revision'},
                status=status.HTTP_403_FORBIDDEN
            )

        if ticket.status != Ticket.Status.COMPLETED:
            return Response(
                {'error': 'Only completed tickets can have revision requested'},
                status=status.HTTP_400_BAD_REQUEST
            )

        revision_comments = serializer.validated_data['revision_comments']

        # Update ticket status back to IN_PROGRESS
        ticket.status = Ticket.Status.IN_PROGRESS
        ticket.revision_count += 1
        ticket.confirmed_by_requester = False  # Reset confirmation
        ticket.confirmed_at = None
        ticket.completed_at = None  # Reset completion
        ticket.save()

        # Create revision comment
        TicketComment.objects.create(
            ticket=ticket,
            user=request.user,
            comment=f"[REVISION REQUEST #{ticket.revision_count}] {revision_comments}"
        )

        # Log activity
        log_activity(
            request.user,
            ticket,
            ActivityLog.ActionType.REVISION_REQUESTED,
            f'Revision #{ticket.revision_count}: {revision_comments}'
        )

        # Notify assigned designer
        if ticket.assigned_to and ticket.assigned_to != request.user:
            Notification.objects.create(
                user=ticket.assigned_to,
                ticket=ticket,
                message=format_notification_message(ticket, 'revision', revision_comments),
                notification_type=Notification.NotificationType.COMMENT
            )
            notify_user(ticket.assigned_to, 'revision_requested', ticket, revision_comments, actor=request.user)

        return Response(TicketDetailSerializer(ticket).data)

    # =====================
    # COMMENTS
    # =====================

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get or add comments on a ticket"""
        ticket = self.get_object()

        if request.method == 'GET':
            # Only return top-level comments (replies are nested)
            comments = ticket.comments.filter(parent__isnull=True)
            serializer = TicketCommentSerializer(comments, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = TicketCommentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Handle reply to existing comment
            parent_id = request.data.get('parent')
            parent_comment = None
            if parent_id:
                try:
                    parent_comment = TicketComment.objects.get(id=parent_id, ticket=ticket)
                except TicketComment.DoesNotExist:
                    return Response(
                        {'error': 'Parent comment not found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            comment = serializer.save(ticket=ticket, user=request.user, parent=parent_comment)

            # Notify ticket participants
            participants = set()
            if ticket.requester:
                participants.add(ticket.requester)
            if ticket.assigned_to:
                participants.add(ticket.assigned_to)
            # Also notify the parent comment author if this is a reply
            if parent_comment and parent_comment.user:
                participants.add(parent_comment.user)
            participants.discard(request.user)  # Don't notify commenter

            for user in participants:
                message = f'New reply on ticket "#{ticket.id} - {ticket.title}"' if parent_comment else f'New comment on ticket "#{ticket.id} - {ticket.title}"'
                Notification.objects.create(
                    user=user,
                    ticket=ticket,
                    message=message,
                    notification_type=Notification.NotificationType.COMMENT
                )
                # Send Telegram notification
                notify_user(user, 'comment', ticket, comment.comment[:100], actor=request.user)

            return Response(
                TicketCommentSerializer(comment).data,
                status=status.HTTP_201_CREATED
            )

    # =====================
    # ATTACHMENTS
    # =====================

    @action(detail=True, methods=['get', 'post'])
    def attachments(self, request, pk=None):
        """Get or add attachments to a ticket"""
        ticket = self.get_object()

        if request.method == 'GET':
            attachments = ticket.attachments.all()
            serializer = TicketAttachmentSerializer(attachments, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            # Check if file is in request
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided. Please upload a file.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            uploaded_file = request.FILES['file']

            # Create attachment directly
            attachment = TicketAttachment.objects.create(
                ticket=ticket,
                user=request.user,
                file=uploaded_file,
                file_name=uploaded_file.name
            )

            return Response(
                TicketAttachmentSerializer(attachment).data,
                status=status.HTTP_201_CREATED
            )

    # =====================
    # COLLABORATORS
    # =====================

    @action(detail=True, methods=['get', 'post', 'delete'])
    def collaborators(self, request, pk=None):
        """Get, add, or remove collaborators from a ticket"""
        ticket = self.get_object()

        if request.method == 'GET':
            collaborators = ticket.collaborators.all()
            serializer = TicketCollaboratorSerializer(collaborators, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            user_id = request.data.get('user_id')
            if not user_id:
                return Response(
                    {'error': 'user_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                collaborator_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if already a collaborator
            if TicketCollaborator.objects.filter(ticket=ticket, user=collaborator_user).exists():
                return Response(
                    {'error': 'User is already a collaborator'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            collaborator = TicketCollaborator.objects.create(
                ticket=ticket,
                user=collaborator_user,
                added_by=request.user
            )

            # Notify the new collaborator
            Notification.objects.create(
                user=collaborator_user,
                ticket=ticket,
                message=format_notification_message(ticket, 'collaborator'),
                notification_type=Notification.NotificationType.ASSIGNED
            )
            notify_user(collaborator_user, 'assigned', ticket, actor=request.user)

            return Response(
                TicketCollaboratorSerializer(collaborator).data,
                status=status.HTTP_201_CREATED
            )

        elif request.method == 'DELETE':
            user_id = request.data.get('user_id')
            if not user_id:
                return Response(
                    {'error': 'user_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                collaborator = TicketCollaborator.objects.get(ticket=ticket, user_id=user_id)
                collaborator.delete()
                return Response({'status': 'Collaborator removed'})
            except TicketCollaborator.DoesNotExist:
                return Response(
                    {'error': 'Collaborator not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

    # =====================
    # HISTORY & ROLLBACK
    # =====================

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get ticket activity history with snapshots for rollback"""
        ticket = self.get_object()
        activities = ActivityLog.objects.filter(ticket=ticket).order_by('-created_at')
        return Response(ActivityLogSerializer(activities, many=True).data)

    @action(detail=True, methods=['post'], permission_classes=[IsManagerUser])
    def rollback(self, request, pk=None):
        """Rollback ticket to a previous state (managers and admins only)"""
        from decimal import Decimal
        from django.utils.dateparse import parse_datetime
        
        ticket = self.get_object()
        activity_id = request.data.get('activity_id')

        if not activity_id:
            return Response(
                {'error': 'activity_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            activity = ActivityLog.objects.get(id=activity_id, ticket=ticket)
        except ActivityLog.DoesNotExist:
            return Response(
                {'error': 'Activity not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not activity.snapshot:
            return Response(
                {'error': 'No snapshot available for this activity. Only new activities have snapshots.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Restore ticket state from snapshot
        snapshot = activity.snapshot
        old_status = ticket.status
        
        ticket.status = snapshot.get('status', ticket.status)
        ticket.assigned_to_id = snapshot.get('assigned_to_id')
        ticket.approver_id = snapshot.get('approver_id')
        ticket.pending_approver_id = snapshot.get('pending_approver_id')
        ticket.dept_approver_id = snapshot.get('dept_approver_id')
        ticket.priority = snapshot.get('priority', ticket.priority)
        ticket.target_department_id = snapshot.get('target_department_id')
        ticket.ticket_product_id = snapshot.get('ticket_product_id')
        ticket.complexity = snapshot.get('complexity', ticket.complexity)

        if snapshot.get('deadline'):
            ticket.deadline = parse_datetime(snapshot['deadline'])
        else:
            ticket.deadline = None

        if snapshot.get('estimated_hours'):
            ticket.estimated_hours = Decimal(snapshot['estimated_hours'])
        else:
            ticket.estimated_hours = None

        if snapshot.get('actual_hours'):
            ticket.actual_hours = Decimal(snapshot['actual_hours'])
        else:
            ticket.actual_hours = None

        # Update rollback tracking on ticket
        ticket.last_rollback_at = timezone.now()
        ticket.rollback_count = (ticket.rollback_count or 0) + 1
        ticket.save()

        # Update analytics rollback tracking
        if hasattr(ticket, 'analytics'):
            ticket.analytics.last_rollback_at = timezone.now()
            ticket.analytics.rollback_count = (ticket.analytics.rollback_count or 0) + 1
            ticket.analytics.save()

        # Log the rollback action
        log_activity(
            request.user,
            ticket,
            ActivityLog.ActionType.ROLLBACK,
            f'Rolled back from {old_status} to {ticket.status} (activity #{activity.id} from {activity.created_at.strftime("%Y-%m-%d %H:%M")})'
        )

        # Notify requester about rollback
        if ticket.requester != request.user:
            Notification.objects.create(
                user=ticket.requester,
                ticket=ticket,
                message=format_notification_message(ticket, 'rollback'),
                notification_type=Notification.NotificationType.APPROVED
            )
            notify_user(ticket.requester, 'rollback', ticket, actor=request.user)

        return Response(TicketDetailSerializer(ticket).data)

    # =====================
    # SOFT DELETE & TRASH
    # =====================

    @action(detail=True, methods=['post'], permission_classes=[IsTicketOwnerOrManager])
    def soft_delete(self, request, pk=None):
        """Soft delete a ticket (move to trash)"""
        ticket = self.get_object()
        
        if ticket.is_deleted:
            return Response(
                {'error': 'Ticket is already in trash'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ticket.is_deleted = True
        ticket.deleted_at = timezone.now()
        ticket.deleted_by = request.user
        ticket.save()
        
        # Log activity
        log_activity(request.user, ticket, ActivityLog.ActionType.DELETED, 'Moved to trash')
        
        return Response({
            'message': f'Ticket #{ticket.id} moved to trash',
            'ticket': TicketDetailSerializer(ticket).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsManagerUser])
    def restore(self, request, pk=None):
        """Restore a deleted ticket from trash"""
        # Get ticket including deleted ones
        ticket = Ticket.objects.get(pk=pk)
        
        if not ticket.is_deleted:
            return Response(
                {'error': 'Ticket is not in trash'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ticket.is_deleted = False
        ticket.deleted_at = None
        ticket.deleted_by = None
        ticket.save()
        
        # Log activity
        log_activity(request.user, ticket, ActivityLog.ActionType.UPDATED, 'Restored from trash')
        
        # Notify requester
        if ticket.requester != request.user:
            Notification.objects.create(
                user=ticket.requester,
                ticket=ticket,
                message=format_notification_message(ticket, 'restored'),
                notification_type=Notification.NotificationType.APPROVED
            )
        
        return Response({
            'message': f'Ticket #{ticket.id} restored from trash',
            'ticket': TicketDetailSerializer(ticket).data
        })

    @action(detail=False, methods=['get'], permission_classes=[IsManagerUser])
    def trash(self, request):
        """List all deleted tickets (trash bin)"""
        queryset = Ticket.objects.filter(is_deleted=True).select_related(
            'requester', 'assigned_to', 'deleted_by'
        ).order_by('-deleted_at')
        
        serializer = TicketListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], permission_classes=[IsAdminUser])
    def permanent_delete(self, request, pk=None):
        """Permanently delete a ticket (admin only, cannot be undone)"""
        try:
            ticket = Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return Response(
                {'error': 'Ticket not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not ticket.is_deleted:
            return Response(
                {'error': 'Ticket must be in trash before permanent deletion'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ticket_id = ticket.id
        ticket_title = ticket.title
        ticket.delete()
        
        return Response({
            'message': f'Ticket #{ticket_id} - {ticket_title} permanently deleted'
        })


class AttachmentDeleteView(generics.DestroyAPIView):
    """Delete an attachment"""
    queryset = TicketAttachment.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all as list for dropdowns

    def get_queryset(self):
        user = self.request.user
        if user.is_manager:
            return TicketAttachment.objects.all()
        return TicketAttachment.objects.filter(user=user)


# =====================
# NOTIFICATION VIEWS
# =====================

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Notification endpoints

    list: Get all notifications for current user
    retrieve: Get notification detail
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all as list for dropdowns

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'])
    def read_all(self, request):
        """Mark all notifications as read"""
        self.get_queryset().update(is_read=True)
        return Response({'status': 'All notifications marked as read'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})


# =====================
# DASHBOARD VIEWS
# =====================

class DashboardView(APIView):
    """Dashboard statistics and overview"""
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all as list for dropdowns

    def get(self, request):
        user = request.user

        # Base queryset
        if user.is_manager:
            tickets = Ticket.objects.all()
        else:
            tickets = Ticket.objects.filter(
                Q(requester=user) | Q(assigned_to=user)
            )

        now = timezone.now()

        # Basic stats
        stats = {
            'total_tickets': tickets.count(),
            'pending_approval': tickets.filter(status=Ticket.Status.REQUESTED).count(),
            'pending_creative': tickets.filter(status=Ticket.Status.PENDING_CREATIVE).count(),
            'in_progress': tickets.filter(status=Ticket.Status.IN_PROGRESS).count(),
            'completed': tickets.filter(status=Ticket.Status.COMPLETED).count(),
            'approved': tickets.filter(status=Ticket.Status.APPROVED).count(),
            'rejected': tickets.filter(status=Ticket.Status.REJECTED).count(),
            'overdue': tickets.filter(
                deadline__lt=now
            ).exclude(
                status__in=[Ticket.Status.COMPLETED, Ticket.Status.REJECTED]
            ).count(),
            'my_assigned': Ticket.objects.filter(assigned_to=user).exclude(
                status__in=[Ticket.Status.COMPLETED, Ticket.Status.REJECTED]
            ).count()
        }

        # Status breakdown for pie chart
        status_data = [
            {'name': 'Requested', 'value': stats['pending_approval'], 'color': '#3B82F6'},
            {'name': 'Pending Creative', 'value': stats['pending_creative'], 'color': '#8B5CF6'},
            {'name': 'Not Yet Started', 'value': stats['approved'], 'color': '#06B6D4'},
            {'name': 'In Progress', 'value': stats['in_progress'], 'color': '#F59E0B'},
            {'name': 'Completed', 'value': stats['completed'], 'color': '#10B981'},
            {'name': 'Rejected', 'value': stats['rejected'], 'color': '#6B7280'},
        ]

        # Priority breakdown for bar chart
        priority_data = [
            {'name': 'Urgent', 'count': tickets.filter(priority='urgent').count(), 'color': '#EF4444'},
            {'name': 'High', 'count': tickets.filter(priority='high').count(), 'color': '#F97316'},
            {'name': 'Medium', 'count': tickets.filter(priority='medium').count(), 'color': '#EAB308'},
            {'name': 'Low', 'count': tickets.filter(priority='low').count(), 'color': '#22C55E'},
        ]

        # Weekly trends (last 7 days)
        weekly_data = []
        for i in range(6, -1, -1):
            day = now.date() - timedelta(days=i)
            day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
            day_end = day_start + timedelta(days=1)

            created = tickets.filter(created_at__gte=day_start, created_at__lt=day_end).count()
            completed = tickets.filter(
                status=Ticket.Status.COMPLETED,
                updated_at__gte=day_start,
                updated_at__lt=day_end
            ).count()

            weekly_data.append({
                'day': day.strftime('%a'),
                'date': day.strftime('%m/%d'),
                'created': created,
                'completed': completed
            })

        stats['status_chart'] = status_data
        stats['priority_chart'] = priority_data
        stats['weekly_chart'] = weekly_data

        return Response(stats)


class MyTasksView(generics.ListAPIView):
    """Get tickets assigned to current user"""
    serializer_class = TicketListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all as list for dropdowns

    def get_queryset(self):
        return Ticket.objects.filter(
            assigned_to=self.request.user
        ).exclude(
            status__in=[Ticket.Status.COMPLETED, Ticket.Status.REJECTED]
        ).select_related('requester', 'assigned_to')


class TeamOverviewView(generics.ListAPIView):
    """Get team workload overview (managers only)"""
    permission_classes = [IsManagerUser]

    def get(self, request):
        users = User.objects.filter(is_active=True).annotate(
            assigned_count=Count('assigned_tickets', filter=~Q(
                assigned_tickets__status__in=[Ticket.Status.COMPLETED, Ticket.Status.REJECTED]
            ))
        ).values('id', 'username', 'first_name', 'last_name', 'assigned_count')

        return Response(list(users))


class OverdueTicketsView(generics.ListAPIView):
    """Get overdue tickets"""
    serializer_class = TicketListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all as list for dropdowns

    def get_queryset(self):
        user = self.request.user
        queryset = Ticket.objects.filter(
            deadline__lt=timezone.now()
        ).exclude(
            status__in=[Ticket.Status.COMPLETED, Ticket.Status.REJECTED]
        ).select_related('requester', 'assigned_to')

        if not user.is_manager:
            queryset = queryset.filter(
                Q(requester=user) | Q(assigned_to=user)
            )

        return queryset


# =====================
# ACTIVITY LOG VIEWS
# =====================

class ActivityLogListView(generics.ListAPIView):
    """Get activity logs for tickets"""
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all as list for dropdowns

    def get_queryset(self):
        user = self.request.user
        queryset = ActivityLog.objects.select_related('user', 'ticket')

        # Managers see all activity, others see only their tickets
        if not user.is_manager:
            queryset = queryset.filter(
                Q(ticket__requester=user) | Q(ticket__assigned_to=user)
            )

        # Filter by ticket if specified
        ticket_id = self.request.query_params.get('ticket')
        if ticket_id:
            queryset = queryset.filter(ticket_id=ticket_id)

        return queryset[:100]  # Limit to last 100 activities


# =====================
# ANALYTICS VIEWS
# =====================

class AnalyticsView(APIView):
    """Analytics endpoint for ticket processing metrics"""
    permission_classes = [IsManagerUser]

    def get(self, request):
        from django.db.models import Avg, Count, F, ExpressionWrapper, DurationField, Min, Max, Sum
        from django.db.models.functions import Coalesce
        from .models import TicketProductItem, TicketAnalytics

        try:
            # Get available date range (min/max dates with data) - exclude deleted
            all_tickets = Ticket.objects.filter(is_deleted=False)
            date_range = all_tickets.aggregate(
                min_date=Min('created_at'),
                max_date=Max('created_at')
            )
            min_date = date_range['min_date'].date().isoformat() if date_range['min_date'] else None
            max_date = date_range['max_date'].date().isoformat() if date_range['max_date'] else None

            # Get date range filters
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')

            # Prefetch analytics to avoid N+1 queries - exclude deleted tickets
            tickets = Ticket.objects.select_related('analytics', 'assigned_to', 'target_department', 'ticket_product').filter(is_deleted=False)
            if date_from:
                tickets = tickets.filter(created_at__date__gte=date_from)
            if date_to:
                tickets = tickets.filter(created_at__date__lte=date_to)

            # Cache tickets list to avoid re-querying
            tickets_list = list(tickets)
            tickets_by_user = {}

            # Create a dict mapping ticket_id to ticket for quick lookup
            tickets_dict = {t.id: t for t in tickets_list}

            # Add assigned_to tickets
            for t in tickets_list:
                if t.assigned_to_id:
                    if t.assigned_to_id not in tickets_by_user:
                        tickets_by_user[t.assigned_to_id] = set()
                    tickets_by_user[t.assigned_to_id].add(t.id)

            # Add collaborator tickets (collaborators get same credit as assigned_to)
            from api.models import TicketCollaborator
            collaborators = TicketCollaborator.objects.filter(
                ticket_id__in=[t.id for t in tickets_list]
            ).values('user_id', 'ticket_id')
            for collab in collaborators:
                user_id = collab['user_id']
                if user_id not in tickets_by_user:
                    tickets_by_user[user_id] = set()
                tickets_by_user[user_id].add(collab['ticket_id'])

            # User performance metrics - optimized with pre-grouped data
            user_stats = []
            users_with_tickets = User.objects.select_related('user_department').filter(
                id__in=tickets_by_user.keys()
            )

            for user in users_with_tickets:
                # Convert ticket IDs to ticket objects
                user_ticket_ids = tickets_by_user.get(user.id, set())
                user_tickets_list = [tickets_dict[tid] for tid in user_ticket_ids if tid in tickets_dict]
                completed_list = [t for t in user_tickets_list if t.status == Ticket.Status.COMPLETED]

                # Calculate average processing time (started_at to completed_at)
                processing_times = [
                    (t.completed_at - t.started_at).total_seconds()
                    for t in completed_list
                    if t.started_at and t.completed_at
                ]
                avg_processing_seconds = round(sum(processing_times) / len(processing_times)) if processing_times else None

                # Calculate average approval to completion time
                approval_times = [
                    (t.completed_at - t.approved_at).total_seconds()
                    for t in completed_list
                    if t.approved_at and t.completed_at
                ]
                avg_approval_to_complete_seconds = sum(approval_times) / len(approval_times) if approval_times else 0
                avg_approval_to_complete_hours = round(avg_approval_to_complete_seconds / 3600, 1)

                # Calculate total quantity output for user (from regular tickets + product items)
                user_regular_qty = sum(
                    t.quantity or 0 for t in completed_list
                    if t.request_type not in ['ads', 'telegram_channel']
                )
                # Add quantities from product_items for Ads/Telegram tickets
                completed_ids = [t.id for t in completed_list]
                user_product_items_qty = TicketProductItem.objects.filter(
                    ticket_id__in=completed_ids
                ).aggregate(total=Sum('quantity'))['total'] or 0
                total_user_output = user_regular_qty + user_product_items_qty

                # Calculate average acknowledge time for user
                user_ack_times = []
                for t in user_tickets_list:
                    if t.status in [Ticket.Status.IN_PROGRESS, Ticket.Status.COMPLETED]:
                        try:
                            if hasattr(t, 'analytics') and t.analytics and t.analytics.time_to_acknowledge is not None:
                                user_ack_times.append(t.analytics.time_to_acknowledge)
                        except TicketAnalytics.DoesNotExist:
                            pass
                avg_ack_seconds = round(sum(user_ack_times) / len(user_ack_times), 0) if user_ack_times else None

                # Calculate assigned output (total quantity from all assigned tickets)
                regular_assigned_qty = sum(
                    t.quantity or 0 for t in user_tickets_list
                    if t.request_type not in ['ads', 'telegram_channel']
                )
                user_ticket_ids = [t.id for t in user_tickets_list]
                assigned_product_items_qty = TicketProductItem.objects.filter(
                    ticket_id__in=user_ticket_ids
                ).aggregate(total=Sum('quantity'))['total'] or 0
                total_assigned_output = regular_assigned_qty + assigned_product_items_qty

                in_progress_count = sum(1 for t in user_tickets_list if t.status == Ticket.Status.IN_PROGRESS)
                pending_count = sum(1 for t in user_tickets_list if t.status in [Ticket.Status.REQUESTED, Ticket.Status.APPROVED])

                # Calculate per-user video creation time
                user_video_tickets = [
                    t for t in completed_list
                    if t.criteria == 'video' or (not t.criteria and t.request_type not in ['ads', 'telegram_channel'])
                ]
                user_video_processing = [
                    (t.completed_at - t.started_at).total_seconds()
                    for t in user_video_tickets
                    if t.started_at and t.completed_at
                ]
                user_video_qty = sum(t.quantity or 0 for t in user_video_tickets)
                # Add Ads VID quantities
                user_ads_vid_qty = TicketProductItem.objects.filter(
                    ticket_id__in=completed_ids,
                    product__name__icontains='VID'
                ).aggregate(total=Sum('quantity'))['total'] or 0
                user_video_qty += user_ads_vid_qty
                user_avg_video_seconds = round(
                    sum(user_video_processing) / user_video_qty
                ) if user_video_qty > 0 and user_video_processing else None

                # Calculate per-user image creation time
                user_image_tickets = [
                    t for t in completed_list
                    if t.criteria == 'image'
                ]
                user_image_processing = [
                    (t.completed_at - t.started_at).total_seconds()
                    for t in user_image_tickets
                    if t.started_at and t.completed_at
                ]
                user_image_qty = sum(t.quantity or 0 for t in user_image_tickets)
                # Add Ads STATIC quantities
                user_ads_static_qty = TicketProductItem.objects.filter(
                    ticket_id__in=completed_ids,
                    product__name__icontains='STATIC'
                ).aggregate(total=Sum('quantity'))['total'] or 0
                user_image_qty += user_ads_static_qty
                user_avg_image_seconds = round(
                    sum(user_image_processing) / user_image_qty
                ) if user_image_qty > 0 and user_image_processing else None

                user_stats.append({
                    'user_id': user.id,
                    'username': user.username,
                    'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'role': user.role,
                    'department': user.user_department.name if user.user_department else getattr(user, 'department', ''),
                    'total_assigned': len(user_tickets_list),
                    'assigned_output': total_assigned_output,
                    'completed': len(completed_list),
                    'in_progress': in_progress_count,
                    'pending': pending_count,
                    'avg_processing_seconds': avg_processing_seconds,
                    'avg_approval_to_complete_hours': avg_approval_to_complete_hours,
                    'completion_rate': round(len(completed_list) / len(user_tickets_list) * 100, 1) if len(user_tickets_list) > 0 else 0,
                    'total_output': total_user_output,
                    'avg_acknowledge_seconds': avg_ack_seconds,
                    'avg_video_creation_seconds': user_avg_video_seconds,
                    'avg_image_creation_seconds': user_avg_image_seconds,
                })

            # Sort by total assigned descending
            user_stats.sort(key=lambda x: x['total_assigned'], reverse=True)

            # Product breakdown (using ticket_product FK, fallback to old text field)
            product_stats = tickets.filter(
                Q(ticket_product__isnull=False) | ~Q(product='')
            ).annotate(
                product_name=Coalesce(F('ticket_product__name'), F('product'))
            ).values('product_name').annotate(
                count=Count('id'),
                completed=Count('id', filter=Q(status=Ticket.Status.COMPLETED)),
                in_progress=Count('id', filter=Q(status=Ticket.Status.IN_PROGRESS)),
                total_quantity=Coalesce(Sum('quantity'), 0),
                completed_quantity=Coalesce(Sum('quantity', filter=Q(status=Ticket.Status.COMPLETED)), 0)
            ).filter(product_name__isnull=False).exclude(product_name='').order_by('-count')
            # Rename for frontend compatibility
            product_stats = [{'product': s['product_name'], **{k: v for k, v in s.items() if k != 'product_name'}} for s in product_stats]

            # Department breakdown (using target_department FK, fallback to old text field)
            department_stats = tickets.filter(
                Q(target_department__isnull=False) | ~Q(department='')
            ).annotate(
                dept_name=Coalesce(F('target_department__name'), F('department'))
            ).values('dept_name').annotate(
                count=Count('id'),
                completed=Count('id', filter=Q(status=Ticket.Status.COMPLETED)),
                in_progress=Count('id', filter=Q(status=Ticket.Status.IN_PROGRESS)),
                total_quantity=Coalesce(Sum('quantity'), 0),
                completed_quantity=Coalesce(Sum('quantity', filter=Q(status=Ticket.Status.COMPLETED)), 0)
            ).filter(dept_name__isnull=False).exclude(dept_name='').order_by('-count')

            # Enhance department_stats with product_items quantities
            dept_stats_enhanced = []
            for stat in department_stats:
                dept_name = stat['dept_name']
                # Get ticket IDs for this department
                dept_ticket_ids = [
                    t.id for t in tickets_list
                    if (t.target_department and t.target_department.name == dept_name) or
                       (not t.target_department and t.department == dept_name)
                ]
                # Add product_items quantities for Ads/Telegram
                from api.models import TicketProductItem
                product_items_qty = TicketProductItem.objects.filter(
                    ticket_id__in=dept_ticket_ids
                ).aggregate(total=Sum('quantity'))['total'] or 0

                completed_ticket_ids = [
                    t.id for t in tickets_list
                    if t.id in dept_ticket_ids and t.status == Ticket.Status.COMPLETED
                ]
                completed_product_items_qty = TicketProductItem.objects.filter(
                    ticket_id__in=completed_ticket_ids
                ).aggregate(total=Sum('quantity'))['total'] or 0

                # Exclude Ads/Telegram ticket.quantity to avoid double counting
                ads_telegram_ticket_qty = sum(
                    t.quantity or 0 for t in tickets_list
                    if t.id in dept_ticket_ids and t.request_type in ['ads', 'telegram_channel']
                )
                completed_ads_telegram_qty = sum(
                    t.quantity or 0 for t in tickets_list
                    if t.id in completed_ticket_ids and t.request_type in ['ads', 'telegram_channel']
                )

                total_qty = (stat['total_quantity'] or 0) - ads_telegram_ticket_qty + product_items_qty
                completed_qty = (stat['completed_quantity'] or 0) - completed_ads_telegram_qty + completed_product_items_qty

                dept_stats_enhanced.append({
                    'department': dept_name,
                    'count': stat['count'],
                    'completed': stat['completed'],
                    'in_progress': stat['in_progress'],
                    'total_quantity': total_qty,
                    'completed_quantity': completed_qty
                })
            department_stats = dept_stats_enhanced

            # Use cached tickets_list for overall stats
            total_completed = sum(1 for t in tickets_list if t.status == Ticket.Status.COMPLETED)
            total_tickets = len(tickets_list)
            # Assigned tickets = tickets that have assigned_to set
            assigned_tickets = sum(1 for t in tickets_list if t.assigned_to_id is not None)

            # Overall average processing time using cached list
            all_processing_times = [
                (t.completed_at - t.started_at).total_seconds()
                for t in tickets_list
                if t.status == Ticket.Status.COMPLETED and t.started_at and t.completed_at
            ]

            overall_avg_processing_seconds = round(
                sum(all_processing_times) / len(all_processing_times)
            ) if all_processing_times else None

            # Revision statistics using cached list
            tickets_with_revisions = sum(1 for t in tickets_list if t.revision_count and t.revision_count > 0)
            revision_rate = round(tickets_with_revisions / total_tickets * 100, 1) if total_tickets > 0 else 0

            # Request type breakdown with quantity metrics
            request_type_stats = list(tickets.exclude(request_type='').values('request_type').annotate(
                count=Count('id'),
                completed=Count('id', filter=Q(status=Ticket.Status.COMPLETED)),
                avg_revisions=Avg('revision_count'),
                total_quantity=Sum('quantity'),
                completed_quantity=Sum('quantity', filter=Q(status=Ticket.Status.COMPLETED)),
            ).order_by('-count'))

            # Map request_type values to display names
            request_type_display = {
                'socmed_posting': 'Socmed Posting',
                'website_banner': 'Website Banner (H5 & WEB)',
                'photoshoot': 'Photoshoot',
                'videoshoot': 'Videoshoot',
                'live_production': 'Live Production',
                'ads': 'Ads',
                'telegram_channel': 'Telegram Official Channel',
            }
            for stat in request_type_stats:
                stat['display_name'] = request_type_display.get(stat['request_type'], stat['request_type'])
                # For Ads/Telegram, add product_items quantity
                if stat['request_type'] in ['ads', 'telegram_channel']:
                    items_qty = TicketProductItem.objects.filter(
                        ticket__in=tickets.filter(request_type=stat['request_type'])
                    ).aggregate(total=Sum('quantity'))['total'] or 0
                    completed_items_qty = TicketProductItem.objects.filter(
                        ticket__in=tickets.filter(request_type=stat['request_type'], status=Ticket.Status.COMPLETED)
                    ).aggregate(total=Sum('quantity'))['total'] or 0
                    stat['total_quantity'] = items_qty
                    stat['completed_quantity'] = completed_items_qty

            # Time to acknowledge metrics using cached list
            acknowledge_times = []
            for t in tickets_list:
                if t.status in [Ticket.Status.IN_PROGRESS, Ticket.Status.COMPLETED]:
                    try:
                        if hasattr(t, 'analytics') and t.analytics and t.analytics.time_to_acknowledge is not None:
                            acknowledge_times.append(t.analytics.time_to_acknowledge)
                    except:
                        pass

            avg_acknowledge_seconds = round(sum(acknowledge_times) / len(acknowledge_times), 0) if acknowledge_times else None

            # Priority breakdown using cached list
            priority_stats = []
            for priority in ['urgent', 'high', 'medium', 'low']:
                priority_list = [t for t in tickets_list if t.priority == priority]
                priority_completed_list = [t for t in priority_list if t.status == Ticket.Status.COMPLETED]

                # Calculate avg processing time for this priority
                priority_processing_times = [
                    (t.completed_at - t.started_at).total_seconds()
                    for t in priority_completed_list
                    if t.started_at and t.completed_at
                ]

                avg_seconds = round(sum(priority_processing_times) / len(priority_processing_times)) if priority_processing_times else None

                priority_stats.append({
                    'priority': priority,
                    'display_name': priority.title(),
                    'total': len(priority_list),
                    'completed': len(priority_completed_list),
                    'avg_processing_seconds': avg_seconds
                })

            # =====================
            # Quantity Metrics
            # =====================
            # Total quantity from regular tickets (completed) - exclude ads/telegram
            completed_list_all = [t for t in tickets_list if t.status == Ticket.Status.COMPLETED]
            regular_quantity = sum(
                t.quantity or 0 for t in completed_list_all
                if t.request_type not in ['ads', 'telegram_channel']
            )
            # Add quantities from product_items for Ads/Telegram tickets
            completed_ids_all = [t.id for t in completed_list_all]
            product_items_quantity = TicketProductItem.objects.filter(
                ticket_id__in=completed_ids_all
            ).aggregate(total=Sum('quantity'))['total'] or 0
            total_quantity_produced = regular_quantity + product_items_quantity
            avg_quantity_per_ticket = round(total_quantity_produced / total_completed, 1) if total_completed > 0 else 0

            # =====================
            # Criteria Breakdown
            # =====================
            criteria_stats = list(tickets.exclude(criteria='').exclude(
                request_type__in=['ads', 'telegram_channel']
            ).values('criteria').annotate(
                count=Count('id'),
                completed=Count('id', filter=Q(status=Ticket.Status.COMPLETED)),
                total_quantity=Sum('quantity'),
                completed_quantity=Sum('quantity', filter=Q(status=Ticket.Status.COMPLETED))
            ).order_by('-count'))

            # Add display names for criteria
            criteria_display_names = {'image': 'Image', 'video': 'Video'}
            for stat in criteria_stats:
                stat['display_name'] = criteria_display_names.get(stat['criteria'], stat['criteria'].title())

            # For old tickets without criteria, count them as "video" (default)
            old_tickets_list = [t for t in tickets_list if not t.criteria and t.request_type not in ['ads', 'telegram_channel']]
            old_tickets_count = len(old_tickets_list)
            old_tickets_completed = sum(1 for t in old_tickets_list if t.status == Ticket.Status.COMPLETED)
            old_tickets_quantity = sum(t.quantity or 0 for t in old_tickets_list)
            old_tickets_completed_qty = sum(t.quantity or 0 for t in old_tickets_list if t.status == Ticket.Status.COMPLETED)

            if old_tickets_count > 0:
                video_stat = next((s for s in criteria_stats if s['criteria'] == 'video'), None)
                if video_stat:
                    video_stat['count'] += old_tickets_count
                    video_stat['completed'] += old_tickets_completed
                    video_stat['total_quantity'] = (video_stat['total_quantity'] or 0) + old_tickets_quantity
                    video_stat['completed_quantity'] = (video_stat['completed_quantity'] or 0) + old_tickets_completed_qty
                else:
                    criteria_stats.append({
                        'criteria': 'video',
                        'display_name': 'Video',
                        'count': old_tickets_count,
                        'completed': old_tickets_completed,
                        'total_quantity': old_tickets_quantity,
                        'completed_quantity': old_tickets_completed_qty
                    })

            # Add quantities from TicketProductItem (Ads) to criteria breakdown
            ticket_ids = [t.id for t in tickets_list]
            product_items_for_criteria = TicketProductItem.objects.filter(ticket_id__in=ticket_ids).select_related('product', 'ticket')
            product_items_list = list(product_items_for_criteria)

            # Video from Ads (product name contains VID)
            ads_video_qty = sum(p.quantity or 0 for p in product_items_list if p.product and 'VID' in (p.product.name or '').upper())
            ads_video_completed_qty = sum(p.quantity or 0 for p in product_items_list if p.product and 'VID' in (p.product.name or '').upper() and p.ticket.status == Ticket.Status.COMPLETED)

            # Image from Ads (product name contains STATIC)
            ads_image_qty = sum(p.quantity or 0 for p in product_items_list if p.product and 'STATIC' in (p.product.name or '').upper())
            ads_image_completed_qty = sum(p.quantity or 0 for p in product_items_list if p.product and 'STATIC' in (p.product.name or '').upper() and p.ticket.status == Ticket.Status.COMPLETED)

            # Add Ads video quantities to video criteria
            if ads_video_qty > 0:
                video_stat = next((s for s in criteria_stats if s['criteria'] == 'video'), None)
                if video_stat:
                    video_stat['total_quantity'] = (video_stat['total_quantity'] or 0) + ads_video_qty
                    video_stat['completed_quantity'] = (video_stat['completed_quantity'] or 0) + ads_video_completed_qty
                else:
                    criteria_stats.append({
                        'criteria': 'video',
                        'display_name': 'Video',
                        'count': 0,
                        'completed': 0,
                        'total_quantity': ads_video_qty,
                        'completed_quantity': ads_video_completed_qty
                    })

            # Add Ads image quantities to image criteria
            if ads_image_qty > 0:
                image_stat = next((s for s in criteria_stats if s['criteria'] == 'image'), None)
                if image_stat:
                    image_stat['total_quantity'] = (image_stat['total_quantity'] or 0) + ads_image_qty
                    image_stat['completed_quantity'] = (image_stat['completed_quantity'] or 0) + ads_image_completed_qty
                else:
                    criteria_stats.append({
                        'criteria': 'image',
                        'display_name': 'Image',
                        'count': 0,
                        'completed': 0,
                        'total_quantity': ads_image_qty,
                        'completed_quantity': ads_image_completed_qty
                    })

            # Add Telegram product items to criteria
            telegram_items = [p for p in product_items_list if p.ticket.request_type == 'telegram_channel']

            for criteria_val in ['image', 'video']:
                telegram_qty = sum(
                    item.quantity or 0 for item in telegram_items
                    if (item.criteria == criteria_val) or (not item.criteria and item.ticket.criteria == criteria_val)
                )
                telegram_completed_qty = sum(
                    item.quantity or 0 for item in telegram_items
                    if ((item.criteria == criteria_val) or (not item.criteria and item.ticket.criteria == criteria_val))
                    and item.ticket.status == Ticket.Status.COMPLETED
                )

                if telegram_qty > 0:
                    existing_stat = next((s for s in criteria_stats if s['criteria'] == criteria_val), None)
                    if existing_stat:
                        existing_stat['total_quantity'] = (existing_stat['total_quantity'] or 0) + telegram_qty
                        existing_stat['completed_quantity'] = (existing_stat['completed_quantity'] or 0) + telegram_completed_qty
                    else:
                        criteria_stats.append({
                            'criteria': criteria_val,
                            'display_name': criteria_display_names.get(criteria_val, criteria_val.title()),
                            'count': 0,
                            'completed': 0,
                            'total_quantity': telegram_qty,
                            'completed_quantity': telegram_completed_qty
                        })

            # Product Items Breakdown (for Ads/Telegram)
            product_items_stats = list(TicketProductItem.objects.filter(
                ticket_id__in=ticket_ids
            ).values('product__name', 'product__category').annotate(
                ticket_count=Count('ticket', distinct=True),
                total_quantity=Sum('quantity'),
                completed_quantity=Sum(
                    'quantity',
                    filter=Q(ticket__status=Ticket.Status.COMPLETED)
                )
            ).order_by('-total_quantity'))

            # Separate by category
            ads_product_stats = [
                {
                    'product_name': s['product__name'],
                    'ticket_count': s['ticket_count'],
                    'total_quantity': s['total_quantity'] or 0,
                    'completed_quantity': s['completed_quantity'] or 0
                }
                for s in product_items_stats if s['product__category'] == 'ads'
            ]
            telegram_product_stats = [
                {
                    'product_name': s['product__name'],
                    'ticket_count': s['ticket_count'],
                    'total_quantity': s['total_quantity'] or 0,
                    'completed_quantity': s['completed_quantity'] or 0
                }
                for s in product_items_stats if s['product__category'] == 'telegram'
            ]

            # =====================
            # NEW TIME PER CREATIVE METRICS
            # =====================
            # Total processing time for all completed tickets
            total_processing_seconds = sum(all_processing_times) if all_processing_times else 0

            # Avg Time Per Creative = total processing time / total quantity produced
            avg_time_per_creative_seconds = round(
                total_processing_seconds / total_quantity_produced
            ) if total_quantity_produced > 0 else None

            # =====================
            # VIDEO CREATION TIME
            # =====================
            # Get video tickets (criteria='video' or legacy tickets without criteria)
            video_tickets = [
                t for t in completed_list_all
                if t.criteria == 'video' or (not t.criteria and t.request_type not in ['ads', 'telegram_channel'])
            ]
            video_processing_times = [
                (t.completed_at - t.started_at).total_seconds()
                for t in video_tickets
                if t.started_at and t.completed_at
            ]
            video_processing_total = sum(video_processing_times) if video_processing_times else 0

            # Calculate video quantity (from regular video tickets)
            regular_video_qty = sum(
                t.quantity or 0 for t in video_tickets
            )
            # Add Ads VID quantities from completed tickets
            ads_vid_qty_completed = sum(
                p.quantity or 0 for p in product_items_list
                if p.product and 'VID' in (p.product.name or '').upper()
                and p.ticket.status == Ticket.Status.COMPLETED
            )
            # Add Telegram video quantities from completed tickets
            telegram_video_qty_completed = sum(
                item.quantity or 0 for item in telegram_items
                if ((item.criteria == 'video') or (not item.criteria and item.ticket.criteria == 'video'))
                and item.ticket.status == Ticket.Status.COMPLETED
            )
            total_video_quantity = regular_video_qty + ads_vid_qty_completed + telegram_video_qty_completed

            avg_video_creation_seconds = round(
                video_processing_total / total_video_quantity
            ) if total_video_quantity > 0 else None

            # =====================
            # IMAGE CREATION TIME
            # =====================
            # Get image tickets (criteria='image')
            image_tickets = [
                t for t in completed_list_all
                if t.criteria == 'image'
            ]
            image_processing_times = [
                (t.completed_at - t.started_at).total_seconds()
                for t in image_tickets
                if t.started_at and t.completed_at
            ]
            image_processing_total = sum(image_processing_times) if image_processing_times else 0

            # Calculate image quantity (from regular image tickets)
            regular_image_qty = sum(
                t.quantity or 0 for t in image_tickets
            )
            # Add Ads STATIC quantities from completed tickets
            ads_static_qty_completed = sum(
                p.quantity or 0 for p in product_items_list
                if p.product and 'STATIC' in (p.product.name or '').upper()
                and p.ticket.status == Ticket.Status.COMPLETED
            )
            # Add Telegram image quantities from completed tickets
            telegram_image_qty_completed = sum(
                item.quantity or 0 for item in telegram_items
                if ((item.criteria == 'image') or (not item.criteria and item.ticket.criteria == 'image'))
                and item.ticket.status == Ticket.Status.COMPLETED
            )
            total_image_quantity = regular_image_qty + ads_static_qty_completed + telegram_image_qty_completed

            avg_image_creation_seconds = round(
                image_processing_total / total_image_quantity
            ) if total_image_quantity > 0 else None

            # =====================
            # USER TOTALS (for Summary Row)
            # =====================
            user_totals = {
                'total_assigned': sum(u['total_assigned'] for u in user_stats),
                'assigned_output': sum(u['assigned_output'] for u in user_stats),
                'completed': sum(u['completed'] for u in user_stats),
                'total_output': sum(u['total_output'] for u in user_stats),
                'in_progress': sum(u['in_progress'] for u in user_stats),
            }

            return Response({
                'date_range': {
                    'min_date': min_date,
                    'max_date': max_date,
                },
                'summary': {
                    'total_tickets': total_tickets,
                    'assigned_tickets': assigned_tickets,
                    'completed_tickets': total_completed,
                    'completion_rate': round(total_completed / assigned_tickets * 100, 1) if assigned_tickets > 0 else 0,
                    'avg_processing_seconds': overall_avg_processing_seconds,
                    'avg_acknowledge_seconds': avg_acknowledge_seconds,
                    'avg_time_per_creative_seconds': avg_time_per_creative_seconds,
                    'avg_video_creation_seconds': avg_video_creation_seconds,
                    'avg_image_creation_seconds': avg_image_creation_seconds,
                    'tickets_with_revisions': tickets_with_revisions,
                    'revision_rate': revision_rate,
                    'total_quantity_produced': total_quantity_produced,
                    'avg_quantity_per_ticket': avg_quantity_per_ticket,
                },
                'user_totals': user_totals,
                'user_performance': user_stats,
                'by_product': list(product_stats),
                'by_department': list(department_stats),
                'by_request_type': list(request_type_stats),
                'by_priority': priority_stats,
                'by_criteria': criteria_stats,
                'ads_product_output': ads_product_stats,
                'telegram_product_output': telegram_product_stats,
            })

        except Exception as e:
            logger.error(f"Analytics error: {str(e)}")
            return Response(
                {'error': f'Failed to load analytics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =====================
# HEALTH CHECK
# =====================

class HealthCheckView(APIView):
    """Health check endpoint for uptime monitoring (keeps Railway warm)"""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})
