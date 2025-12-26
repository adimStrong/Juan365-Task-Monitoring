from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from datetime import timedelta
from django.utils import timezone
import logging

from .models import Ticket, TicketComment, TicketAttachment, TicketCollaborator, Notification, ActivityLog, Department, Product
from notifications import notify_user  # Unified notification (Telegram + Email)

logger = logging.getLogger(__name__)
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
    """
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Return all as list for dropdowns

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
            'product_items', 'product_items__product'  # For Ads/Telegram multi-product support
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

        # Get Creative department info
        try:
            creative_dept = Department.objects.get(is_creative=True)
            creative_manager = creative_dept.manager
        except Department.DoesNotExist:
            creative_dept = None
            creative_manager = None

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
                    message=f'New ticket from Creative team member {requester.username}: "#{ticket.id} - {ticket.title}" needs your approval',
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
                    message=f'New ticket from {requester.username}: "#{ticket.id} - {ticket.title}" needs your approval',
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

        # Get Creative department info
        try:
            creative_dept = Department.objects.get(is_creative=True)
            creative_manager = creative_dept.manager
        except Department.DoesNotExist:
            creative_dept = None
            creative_manager = None

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
                message=f'Your ticket "#{ticket.id} - {ticket.title}" has been fully approved by Creative',
                notification_type=Notification.NotificationType.APPROVED
            )
            notify_user(ticket.requester, 'approved', ticket, actor=user)

            # Notify department approver if exists
            if ticket.dept_approver and ticket.dept_approver != user:
                Notification.objects.create(
                    user=ticket.dept_approver,
                    ticket=ticket,
                    message=f'Ticket "#{ticket.id} - {ticket.title}" has been approved by Creative',
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
            message=f'Your ticket "#{ticket.id} - {ticket.title}" has been approved by department, pending Creative approval',
            notification_type=Notification.NotificationType.PENDING_CREATIVE
        )
        notify_user(ticket.requester, 'pending_creative', ticket, actor=user)

        # Notify Creative Manager for second approval
        if ticket.pending_approver:
            Notification.objects.create(
                user=ticket.pending_approver,
                ticket=ticket,
                message=f'Ticket "#{ticket.id} - {ticket.title}" needs your approval (approved by {user.username})',
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
        message = f'Your ticket "#{ticket.id} - {ticket.title}" has been rejected'
        if reason:
            message += f'. Reason: {reason}'

        Notification.objects.create(
            user=ticket.requester,
            ticket=ticket,
            message=message,
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

        # Log activity with deadline info
        deadline_info = ticket.deadline.strftime('%Y-%m-%d %H:%M') if ticket.deadline else 'N/A'
        log_activity(request.user, ticket, ActivityLog.ActionType.ASSIGNED,
                    f'Assigned to {ticket.assigned_to.username}. Deadline: {deadline_info}')

        Notification.objects.create(
            user=ticket.assigned_to,
            ticket=ticket,
            message=f'Ticket "#{ticket.id} - {ticket.title}" has been assigned to you. Deadline: {deadline_info}',
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

        # Only the assigned person can start (not even managers)
        if ticket.assigned_to != request.user:
            return Response(
                {'error': 'Only the assigned user can start this ticket'},
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
                message=f'Work has started on your ticket "#{ticket.id} - {ticket.title}"',
                notification_type=Notification.NotificationType.APPROVED
            )
            notify_user(ticket.requester, 'started', ticket, actor=request.user)

        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark ticket as completed"""
        ticket = self.get_object()

        if ticket.assigned_to != request.user and not request.user.is_manager:
            return Response(
                {'error': 'Only assigned user can complete this ticket'},
                status=status.HTTP_403_FORBIDDEN
            )

        if ticket.status != Ticket.Status.IN_PROGRESS:
            return Response(
                {'error': 'Only in-progress tickets can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.status = Ticket.Status.COMPLETED
        ticket.completed_at = timezone.now()
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
                message=f'Ticket "#{ticket.id} - {ticket.title}" has been completed. Please confirm completion.',
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
                message=f'Requester has confirmed completion of ticket "#{ticket.id} - {ticket.title}"',
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
                message=f'Revision requested for ticket "#{ticket.id} - {ticket.title}": {revision_comments[:100]}',
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
                message=f'You have been added as a collaborator on ticket "#{ticket.id} - {ticket.title}"',
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
                message=f'Ticket "#{ticket.id} - {ticket.title}" has been rolled back to a previous state by {request.user.username}',
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
                message=f'Your ticket "#{ticket.id} - {ticket.title}" has been restored from trash',
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
            {'name': 'Approved', 'value': stats['approved'], 'color': '#10B981'},
            {'name': 'In Progress', 'value': stats['in_progress'], 'color': '#F59E0B'},
            {'name': 'Completed', 'value': stats['completed'], 'color': '#6B7280'},
            {'name': 'Rejected', 'value': stats['rejected'], 'color': '#EF4444'},
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
        from .models import TicketProductItem

        # Get available date range (min/max dates with data)
        all_tickets = Ticket.objects.all()
        date_range = all_tickets.aggregate(
            min_date=Min('created_at'),
            max_date=Max('created_at')
        )
        min_date = date_range['min_date'].date().isoformat() if date_range['min_date'] else None
        max_date = date_range['max_date'].date().isoformat() if date_range['max_date'] else None

        # Get date range filters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        tickets = Ticket.objects.all()
        if date_from:
            tickets = tickets.filter(created_at__date__gte=date_from)
        if date_to:
            tickets = tickets.filter(created_at__date__lte=date_to)

        # User performance metrics
        user_stats = []
        users_with_tickets = User.objects.select_related('user_department').filter(
            Q(assigned_tickets__isnull=False) | Q(requested_tickets__isnull=False)
        ).distinct()

        for user in users_with_tickets:
            user_tickets = tickets.filter(assigned_to=user)
            completed_tickets = user_tickets.filter(status=Ticket.Status.COMPLETED)

            # Calculate average processing time (started_at to completed_at)
            processing_times = []
            for t in completed_tickets.filter(started_at__isnull=False, completed_at__isnull=False):
                if t.started_at and t.completed_at:
                    delta = (t.completed_at - t.started_at).total_seconds()
                    processing_times.append(delta)

            avg_processing_seconds = sum(processing_times) / len(processing_times) if processing_times else None
            avg_processing_hours = round(avg_processing_seconds / 3600, 1) if avg_processing_seconds else None

            # Calculate average approval to completion time
            approval_times = []
            for t in completed_tickets.filter(approved_at__isnull=False, completed_at__isnull=False):
                if t.approved_at and t.completed_at:
                    delta = (t.completed_at - t.approved_at).total_seconds()
                    approval_times.append(delta)

            avg_approval_to_complete_seconds = sum(approval_times) / len(approval_times) if approval_times else 0
            avg_approval_to_complete_hours = round(avg_approval_to_complete_seconds / 3600, 1)

            # Calculate total quantity output for user (from regular tickets + product items)
            user_quantity = completed_tickets.aggregate(total=Sum('quantity'))['total'] or 0
            # Add quantities from product_items for Ads/Telegram tickets
            user_product_items_qty = TicketProductItem.objects.filter(
                ticket__in=completed_tickets
            ).aggregate(total=Sum('quantity'))['total'] or 0
            total_user_output = user_quantity + user_product_items_qty

            # Calculate average acknowledge time for user (time from assignment to start) - now in seconds
            user_ack_times = []
            for t in user_tickets.filter(status__in=[Ticket.Status.IN_PROGRESS, Ticket.Status.COMPLETED]):
                if hasattr(t, 'analytics') and t.analytics.time_to_acknowledge is not None:
                    user_ack_times.append(t.analytics.time_to_acknowledge)
            avg_ack_seconds = round(sum(user_ack_times) / len(user_ack_times), 0) if user_ack_times else None

            # Calculate assigned output (total quantity from all assigned tickets)
            assigned_quantity = user_tickets.aggregate(total=Sum('quantity'))['total'] or 0
            # Add quantities from product_items for assigned Ads/Telegram tickets
            assigned_product_items_qty = TicketProductItem.objects.filter(
                ticket__in=user_tickets
            ).aggregate(total=Sum('quantity'))['total'] or 0
            total_assigned_output = assigned_quantity + assigned_product_items_qty

            user_stats.append({
                'user_id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'role': user.role,
                'department': user.user_department.name if user.user_department else user.department,
                'total_assigned': user_tickets.count(),
                'assigned_output': total_assigned_output,  # NEW: assigned quantity output
                'completed': completed_tickets.count(),
                'in_progress': user_tickets.filter(status=Ticket.Status.IN_PROGRESS).count(),
                'pending': user_tickets.filter(status__in=[Ticket.Status.REQUESTED, Ticket.Status.APPROVED]).count(),
                'avg_processing_hours': avg_processing_hours,
                'avg_approval_to_complete_hours': avg_approval_to_complete_hours,
                'completion_rate': round(completed_tickets.count() / user_tickets.count() * 100, 1) if user_tickets.count() > 0 else 0,
                'total_output': total_user_output,  # Completed quantity output
                'avg_acknowledge_seconds': avg_ack_seconds,  # NOW in seconds
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
            in_progress=Count('id', filter=Q(status=Ticket.Status.IN_PROGRESS))
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
            in_progress=Count('id', filter=Q(status=Ticket.Status.IN_PROGRESS))
        ).filter(dept_name__isnull=False).exclude(dept_name='').order_by('-count')
        # Rename for frontend compatibility
        department_stats = [{'department': s['dept_name'], **{k: v for k, v in s.items() if k != 'dept_name'}} for s in department_stats]

        # Overall stats
        total_completed = tickets.filter(status=Ticket.Status.COMPLETED).count()
        total_tickets = tickets.count()

        # Overall average processing time
        all_processing_times = []
        for t in tickets.filter(started_at__isnull=False, completed_at__isnull=False, status=Ticket.Status.COMPLETED):
            if t.started_at and t.completed_at:
                delta = (t.completed_at - t.started_at).total_seconds()
                all_processing_times.append(delta)

        overall_avg_processing_hours = round(
            (sum(all_processing_times) / len(all_processing_times) / 3600), 1
        ) if all_processing_times else None

        # Revision statistics
        tickets_with_revisions = tickets.filter(revision_count__gt=0).count()
        revision_rate = round(tickets_with_revisions / total_tickets * 100, 1) if total_tickets > 0 else 0

        # Request type breakdown with quantity metrics
        request_type_stats = tickets.exclude(request_type='').values('request_type').annotate(
            count=Count('id'),
            completed=Count('id', filter=Q(status=Ticket.Status.COMPLETED)),
            avg_revisions=Avg('revision_count'),
            total_quantity=Sum('quantity'),  # NEW: total quantity
            completed_quantity=Sum('quantity', filter=Q(status=Ticket.Status.COMPLETED)),  # NEW
        ).order_by('-count')

        # Map request_type values to display names (including new types)
        request_type_display = {
            'socmed_posting': 'Socmed Posting',
            'website_banner': 'Website Banner (H5 & WEB)',
            'photoshoot': 'Photoshoot',
            'videoshoot': 'Videoshoot',
            'live_production': 'Live Production',
            'ads': 'Ads',  # NEW
            'telegram_channel': 'Telegram Official Channel',  # NEW
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

        # Time to acknowledge metrics (now in seconds)
        acknowledge_times = []
        for t in tickets.filter(status__in=[Ticket.Status.IN_PROGRESS, Ticket.Status.COMPLETED]):
            # Check if analytics exists and time_to_acknowledge is set (including 0)
            if hasattr(t, 'analytics') and t.analytics.time_to_acknowledge is not None:
                acknowledge_times.append(t.analytics.time_to_acknowledge)

        avg_acknowledge_seconds = round(sum(acknowledge_times) / len(acknowledge_times), 0) if acknowledge_times else None

        # Priority breakdown with processing times
        priority_stats = []
        for priority in ['urgent', 'high', 'medium', 'low']:
            priority_tickets = tickets.filter(priority=priority)
            priority_completed = priority_tickets.filter(status=Ticket.Status.COMPLETED)

            # Calculate avg processing time for this priority
            priority_processing_times = []
            for t in priority_completed.filter(started_at__isnull=False, completed_at__isnull=False):
                if t.started_at and t.completed_at:
                    delta = (t.completed_at - t.started_at).total_seconds()
                    priority_processing_times.append(delta)

            avg_hours = round(sum(priority_processing_times) / len(priority_processing_times) / 3600, 1) if priority_processing_times else 0

            priority_stats.append({
                'priority': priority,
                'display_name': priority.title(),
                'total': priority_tickets.count(),
                'completed': priority_completed.count(),
                'avg_processing_hours': avg_hours
            })

        # =====================
        # NEW: Quantity Metrics
        # =====================
        # Total quantity from regular tickets (completed)
        completed_tickets = tickets.filter(status=Ticket.Status.COMPLETED)
        regular_quantity = completed_tickets.aggregate(total=Sum('quantity'))['total'] or 0
        # Add quantities from product_items for Ads/Telegram tickets
        product_items_quantity = TicketProductItem.objects.filter(
            ticket__in=completed_tickets
        ).aggregate(total=Sum('quantity'))['total'] or 0
        total_quantity_produced = regular_quantity + product_items_quantity
        avg_quantity_per_ticket = round(total_quantity_produced / total_completed, 1) if total_completed > 0 else 0

        # =====================
        # NEW: Criteria Breakdown
        # =====================
        # Get criteria stats (for tickets with criteria set)
        criteria_stats = list(tickets.exclude(criteria='').values('criteria').annotate(
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
        old_tickets_count = tickets.filter(criteria='').count()
        old_tickets_completed = tickets.filter(criteria='', status=Ticket.Status.COMPLETED).count()
        old_tickets_quantity = tickets.filter(criteria='').aggregate(total=Sum('quantity'))['total'] or 0
        old_tickets_completed_qty = tickets.filter(criteria='', status=Ticket.Status.COMPLETED).aggregate(total=Sum('quantity'))['total'] or 0

        if old_tickets_count > 0:
            # Check if video already exists in criteria_stats
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
        # Ads products: VID = video, STATIC = image
        product_items_for_criteria = TicketProductItem.objects.filter(ticket__in=tickets)

        # Video from Ads (product name contains VID)
        ads_video_qty = product_items_for_criteria.filter(
            product__name__icontains='VID'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        ads_video_completed_qty = product_items_for_criteria.filter(
            product__name__icontains='VID',
            ticket__status=Ticket.Status.COMPLETED
        ).aggregate(total=Sum('quantity'))['total'] or 0

        # Image from Ads (product name contains STATIC)
        ads_image_qty = product_items_for_criteria.filter(
            product__name__icontains='STATIC'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        ads_image_completed_qty = product_items_for_criteria.filter(
            product__name__icontains='STATIC',
            ticket__status=Ticket.Status.COMPLETED
        ).aggregate(total=Sum('quantity'))['total'] or 0

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

        # =====================
        # NEW: Product Items Breakdown (for Ads/Telegram)
        # =====================
        product_items_stats = list(TicketProductItem.objects.filter(
            ticket__in=tickets
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

        return Response({
            'date_range': {
                'min_date': min_date,
                'max_date': max_date,
            },
            'summary': {
                'total_tickets': total_tickets,
                'completed_tickets': total_completed,
                'completion_rate': round(total_completed / total_tickets * 100, 1) if total_tickets > 0 else 0,
                'avg_processing_hours': overall_avg_processing_hours,
                'avg_acknowledge_seconds': avg_acknowledge_seconds,  # Now in seconds for precision
                'tickets_with_revisions': tickets_with_revisions,
                'revision_rate': revision_rate,
                # NEW: Quantity metrics
                'total_quantity_produced': total_quantity_produced,
                'avg_quantity_per_ticket': avg_quantity_per_ticket,
            },
            'user_performance': user_stats,
            'by_product': list(product_stats),
            'by_department': list(department_stats),
            'by_request_type': list(request_type_stats),
            'by_priority': priority_stats,
            # NEW: Additional breakdowns
            'by_criteria': criteria_stats,
            'ads_product_output': ads_product_stats,
            'telegram_product_output': telegram_product_stats,
        })
