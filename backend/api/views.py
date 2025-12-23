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
from notifications.telegram import notify_user

logger = logging.getLogger(__name__)
from .serializers import (
    UserSerializer, UserCreateSerializer, UserMinimalSerializer, UserManagementSerializer,
    TicketListSerializer, TicketDetailSerializer, TicketCreateSerializer,
    TicketUpdateSerializer, TicketAssignSerializer, TicketRejectSerializer,
    TicketCommentSerializer, TicketAttachmentSerializer, TicketCollaboratorSerializer,
    NotificationSerializer, DashboardStatsSerializer, ActivityLogSerializer,
    DepartmentSerializer, ProductSerializer, ChangePasswordSerializer, UpdateUserProfileSerializer
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
    }
    ActivityLog.objects.create(
        user=user,
        ticket=ticket,
        action=action,
        details=details,
        snapshot=snapshot
    )
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
    """Custom login view that checks if user is approved"""
    permission_classes = [AllowAny]

    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        from django.contrib.auth import authenticate

        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'detail': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if user is None:
            return Response(
                {'detail': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'detail': 'Account is deactivated. Contact administrator.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_approved:
            return Response(
                {'detail': 'Account pending approval. Please wait for admin to approve your registration.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

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


# =====================
# DEPARTMENT & PRODUCT VIEWS
# =====================

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
        queryset = Ticket.objects.select_related('requester', 'assigned_to', 'approver')

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
        """Create ticket with smart approval routing"""
        from .models import Department

        requester = self.request.user
        ticket = serializer.save(requester=requester)

        # Determine the approver based on requester's role
        pending_approver = None

        # Check if requester is the Creative Manager
        try:
            creative_dept = Department.objects.get(is_creative=True)
            is_creative_manager = (creative_dept.manager == requester)
        except Department.DoesNotExist:
            creative_dept = None
            is_creative_manager = False

        if is_creative_manager:
            # Creative Manager creates ticket → Auto-approve
            ticket.status = Ticket.Status.APPROVED
            ticket.approver = requester
            ticket.approved_at = timezone.now()
            ticket.pending_approver = None
            log_activity(requester, ticket, ActivityLog.ActionType.APPROVED, 'Auto-approved (Creative Manager)')
        elif requester.is_manager:
            # Department Manager creates ticket → Creative Manager approves
            if creative_dept and creative_dept.manager:
                pending_approver = creative_dept.manager
                ticket.pending_approver = pending_approver
                # Notify Creative Manager
                Notification.objects.create(
                    user=pending_approver,
                    ticket=ticket,
                    message=f'New ticket from manager {requester.username}: "#{ticket.id} - {ticket.title}" needs your approval',
                    notification_type=Notification.NotificationType.NEW_REQUEST
                )
                notify_user(pending_approver, 'new_request', ticket)
        else:
            # Regular user → Their department manager approves
            if requester.user_department and requester.user_department.manager:
                pending_approver = requester.user_department.manager
                ticket.pending_approver = pending_approver
                # Notify Department Manager
                Notification.objects.create(
                    user=pending_approver,
                    ticket=ticket,
                    message=f'New ticket from {requester.username}: "#{ticket.id} - {ticket.title}" needs your approval',
                    notification_type=Notification.NotificationType.NEW_REQUEST
                )
                notify_user(pending_approver, 'new_request', ticket)

        ticket.save()

        # Log creation
        log_activity(requester, ticket, ActivityLog.ActionType.CREATED)

    # =====================
    # TICKET ACTIONS
    # =====================

    @action(detail=True, methods=['post'], permission_classes=[CanApproveTicket])
    def approve(self, request, pk=None):
        """
        Two-step approval workflow:
        1. Department Manager approves → PENDING_CREATIVE (goes to Creative Manager)
        2. Creative Manager approves → APPROVED (can assign)
        """
        ticket = self.get_object()
        user = request.user

        # Check if user is Creative Manager or Admin
        try:
            creative_dept = Department.objects.get(is_creative=True)
            is_creative_manager = (creative_dept.manager == user) or user.is_admin
        except Department.DoesNotExist:
            is_creative_manager = user.is_admin

        # Handle PENDING_CREATIVE status - only Creative Manager/Admin can approve
        if ticket.status == Ticket.Status.PENDING_CREATIVE:
            if not is_creative_manager:
                return Response(
                    {'error': 'Only Creative Manager or Admin can give final approval'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Final approval by Creative Manager
            ticket.status = Ticket.Status.APPROVED
            ticket.approver = user
            ticket.approved_at = timezone.now()
            ticket.pending_approver = None
            ticket.save()

            # Log activity
            log_activity(user, ticket, ActivityLog.ActionType.APPROVED, 'Final approval by Creative Manager')

            # Notify requester
            Notification.objects.create(
                user=ticket.requester,
                ticket=ticket,
                message=f'Your ticket "#{ticket.id} - {ticket.title}" has been fully approved by Creative',
                notification_type=Notification.NotificationType.APPROVED
            )
            notify_user(ticket.requester, 'approved', ticket)

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

        # If Creative Manager or Admin approves directly → APPROVED
        if is_creative_manager:
            ticket.status = Ticket.Status.APPROVED
            ticket.approver = user
            ticket.approved_at = timezone.now()
            ticket.pending_approver = None
            ticket.save()

            # Log activity
            log_activity(user, ticket, ActivityLog.ActionType.APPROVED)

            # Notify requester
            Notification.objects.create(
                user=ticket.requester,
                ticket=ticket,
                message=f'Your ticket "#{ticket.id} - {ticket.title}" has been approved',
                notification_type=Notification.NotificationType.APPROVED
            )
            notify_user(ticket.requester, 'approved', ticket)

            # Notify assigned user if exists
            if ticket.assigned_to and ticket.assigned_to != ticket.requester:
                Notification.objects.create(
                    user=ticket.assigned_to,
                    ticket=ticket,
                    message=f'Ticket "#{ticket.id} - {ticket.title}" has been approved and assigned to you',
                    notification_type=Notification.NotificationType.ASSIGNED
                )
                notify_user(ticket.assigned_to, 'assigned', ticket)

            return Response(TicketDetailSerializer(ticket).data)

        # Department Manager approves → PENDING_CREATIVE (first approval)
        ticket.status = Ticket.Status.PENDING_CREATIVE
        ticket.dept_approver = user
        ticket.dept_approved_at = timezone.now()

        # Set pending approver to Creative Manager
        try:
            creative_dept = Department.objects.get(is_creative=True)
            if creative_dept.manager:
                ticket.pending_approver = creative_dept.manager
        except Department.DoesNotExist:
            pass

        ticket.save()

        # Log activity
        log_activity(user, ticket, ActivityLog.ActionType.DEPT_APPROVED, 'Department manager first approval')

        # Notify requester of first approval
        Notification.objects.create(
            user=ticket.requester,
            ticket=ticket,
            message=f'Your ticket "#{ticket.id} - {ticket.title}" has been approved by department, pending Creative approval',
            notification_type=Notification.NotificationType.PENDING_CREATIVE
        )
        notify_user(ticket.requester, 'pending_creative', ticket)

        # Notify Creative Manager for second approval
        if ticket.pending_approver:
            Notification.objects.create(
                user=ticket.pending_approver,
                ticket=ticket,
                message=f'Ticket "#{ticket.id} - {ticket.title}" needs your approval (approved by {user.username})',
                notification_type=Notification.NotificationType.PENDING_CREATIVE
            )
            notify_user(ticket.pending_approver, 'pending_creative', ticket)

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
        notify_user(ticket.requester, 'rejected', ticket, reason)

        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=['post'], permission_classes=[CanApproveTicket])
    def assign(self, request, pk=None):
        """Assign ticket to a user"""
        ticket = self.get_object()
        serializer = TicketAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket.assigned_to = serializer.validated_data['assigned_to']
        ticket.assigned_at = timezone.now()
        ticket.save()

        # Log activity
        log_activity(request.user, ticket, ActivityLog.ActionType.ASSIGNED,
                    f'Assigned to {ticket.assigned_to.username}')

        Notification.objects.create(
            user=ticket.assigned_to,
            ticket=ticket,
            message=f'Ticket "#{ticket.id} - {ticket.title}" has been assigned to you',
            notification_type=Notification.NotificationType.ASSIGNED
        )
        # Send Telegram notification
        notify_user(ticket.assigned_to, 'assigned', ticket)

        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start working on a ticket"""
        ticket = self.get_object()

        if ticket.assigned_to != request.user and not request.user.is_manager:
            return Response(
                {'error': 'Only assigned user can start this ticket'},
                status=status.HTTP_403_FORBIDDEN
            )

        if ticket.status not in [Ticket.Status.APPROVED, Ticket.Status.REQUESTED]:
            return Response(
                {'error': 'Ticket must be approved or requested to start'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.status = Ticket.Status.IN_PROGRESS
        ticket.started_at = timezone.now()
        if not ticket.assigned_to:
            ticket.assigned_to = request.user
            ticket.assigned_at = timezone.now()
        ticket.save()

        # Log activity
        log_activity(request.user, ticket, ActivityLog.ActionType.STARTED)

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
            notify_user(ticket.requester, 'completed', ticket)

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
            notify_user(ticket.assigned_to, 'confirmed', ticket)

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
                notify_user(user, 'comment', ticket, comment.comment[:100])

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
            notify_user(collaborator_user, 'assigned', ticket)

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

        ticket.save()

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
        from django.db.models import Avg, Count, F, ExpressionWrapper, DurationField
        from django.db.models.functions import Coalesce

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
        users_with_tickets = User.objects.filter(
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

            avg_processing_seconds = sum(processing_times) / len(processing_times) if processing_times else 0
            avg_processing_hours = round(avg_processing_seconds / 3600, 1)

            # Calculate average approval to completion time
            approval_times = []
            for t in completed_tickets.filter(approved_at__isnull=False, completed_at__isnull=False):
                if t.approved_at and t.completed_at:
                    delta = (t.completed_at - t.approved_at).total_seconds()
                    approval_times.append(delta)

            avg_approval_to_complete_seconds = sum(approval_times) / len(approval_times) if approval_times else 0
            avg_approval_to_complete_hours = round(avg_approval_to_complete_seconds / 3600, 1)

            user_stats.append({
                'user_id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'role': user.role,
                'department': user.department,
                'total_assigned': user_tickets.count(),
                'completed': completed_tickets.count(),
                'in_progress': user_tickets.filter(status=Ticket.Status.IN_PROGRESS).count(),
                'pending': user_tickets.filter(status__in=[Ticket.Status.REQUESTED, Ticket.Status.APPROVED]).count(),
                'avg_processing_hours': avg_processing_hours,
                'avg_approval_to_complete_hours': avg_approval_to_complete_hours,
                'completion_rate': round(completed_tickets.count() / user_tickets.count() * 100, 1) if user_tickets.count() > 0 else 0
            })

        # Sort by total assigned descending
        user_stats.sort(key=lambda x: x['total_assigned'], reverse=True)

        # Product breakdown
        product_stats = tickets.exclude(product='').values('product').annotate(
            count=Count('id'),
            completed=Count('id', filter=Q(status=Ticket.Status.COMPLETED)),
            in_progress=Count('id', filter=Q(status=Ticket.Status.IN_PROGRESS))
        ).order_by('-count')

        # Department breakdown
        department_stats = tickets.exclude(department='').values('department').annotate(
            count=Count('id'),
            completed=Count('id', filter=Q(status=Ticket.Status.COMPLETED)),
            in_progress=Count('id', filter=Q(status=Ticket.Status.IN_PROGRESS))
        ).order_by('-count')

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
        ) if all_processing_times else 0

        return Response({
            'summary': {
                'total_tickets': total_tickets,
                'completed_tickets': total_completed,
                'completion_rate': round(total_completed / total_tickets * 100, 1) if total_tickets > 0 else 0,
                'avg_processing_hours': overall_avg_processing_hours
            },
            'user_performance': user_stats,
            'by_product': list(product_stats),
            'by_department': list(department_stats)
        })
