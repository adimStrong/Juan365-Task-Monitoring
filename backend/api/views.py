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

from .models import Ticket, TicketComment, TicketAttachment, Notification, ActivityLog
from notifications.telegram import notify_user

logger = logging.getLogger(__name__)
from .serializers import (
    UserSerializer, UserCreateSerializer, UserMinimalSerializer, UserManagementSerializer,
    TicketListSerializer, TicketDetailSerializer, TicketCreateSerializer,
    TicketUpdateSerializer, TicketAssignSerializer, TicketRejectSerializer,
    TicketCommentSerializer, TicketAttachmentSerializer,
    NotificationSerializer, DashboardStatsSerializer, ActivityLogSerializer
)


def log_activity(user, ticket, action, details=''):
    """Helper function to log activity"""
    ActivityLog.objects.create(
        user=user,
        ticket=ticket,
        action=action,
        details=details
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

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    """List all users (for assignment dropdown)"""
    serializer_class = UserMinimalSerializer
    permission_classes = [IsAuthenticated]

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

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
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

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
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

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
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

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reactivate(self, request, pk=None):
        """Reactivate a deactivated user"""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response(UserSerializer(user).data)


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

    def get_queryset(self):
        user = self.request.user
        queryset = Ticket.objects.select_related('requester', 'assigned_to', 'approver')

        # Admins and managers see all tickets
        if user.is_manager:
            pass
        else:
            # Regular users see their own requests and assigned tickets
            queryset = queryset.filter(
                Q(requester=user) | Q(assigned_to=user)
            )

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

    # =====================
    # TICKET ACTIONS
    # =====================

    @action(detail=True, methods=['post'], permission_classes=[CanApproveTicket])
    def approve(self, request, pk=None):
        """Approve a ticket request"""
        ticket = self.get_object()

        if ticket.status != Ticket.Status.REQUESTED:
            return Response(
                {'error': 'Only requested tickets can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.status = Ticket.Status.APPROVED
        ticket.approver = request.user
        ticket.save()

        # Log activity
        log_activity(request.user, ticket, ActivityLog.ActionType.APPROVED)

        # Create notification for requester
        Notification.objects.create(
            user=ticket.requester,
            ticket=ticket,
            message=f'Your ticket "#{ticket.id} - {ticket.title}" has been approved',
            notification_type=Notification.NotificationType.APPROVED
        )
        # Send Telegram notification
        notify_user(ticket.requester, 'approved', ticket)

        # Notify assigned user if exists
        if ticket.assigned_to and ticket.assigned_to != ticket.requester:
            Notification.objects.create(
                user=ticket.assigned_to,
                ticket=ticket,
                message=f'Ticket "#{ticket.id} - {ticket.title}" has been approved and assigned to you',
                notification_type=Notification.NotificationType.ASSIGNED
            )
            # Send Telegram notification
            notify_user(ticket.assigned_to, 'assigned', ticket)

        return Response(TicketDetailSerializer(ticket).data)

    @action(detail=True, methods=['post'], permission_classes=[CanApproveTicket])
    def reject(self, request, pk=None):
        """Reject a ticket request"""
        ticket = self.get_object()
        serializer = TicketRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if ticket.status != Ticket.Status.REQUESTED:
            return Response(
                {'error': 'Only requested tickets can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ticket.status = Ticket.Status.REJECTED
        ticket.approver = request.user
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
        if not ticket.assigned_to:
            ticket.assigned_to = request.user
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
        ticket.save()

        # Log activity
        log_activity(request.user, ticket, ActivityLog.ActionType.COMPLETED)

        # Notify requester
        if ticket.requester != request.user:
            Notification.objects.create(
                user=ticket.requester,
                ticket=ticket,
                message=f'Ticket "#{ticket.id} - {ticket.title}" has been completed',
                notification_type=Notification.NotificationType.APPROVED
            )
            # Send Telegram notification
            notify_user(ticket.requester, 'completed', ticket)

        return Response(TicketDetailSerializer(ticket).data)

    # =====================
    # COMMENTS
    # =====================

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get or add comments on a ticket"""
        ticket = self.get_object()

        if request.method == 'GET':
            comments = ticket.comments.all()
            serializer = TicketCommentSerializer(comments, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = TicketCommentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            comment = serializer.save(ticket=ticket, user=request.user)

            # Notify ticket participants
            participants = set()
            if ticket.requester:
                participants.add(ticket.requester)
            if ticket.assigned_to:
                participants.add(ticket.assigned_to)
            participants.discard(request.user)  # Don't notify commenter

            for user in participants:
                Notification.objects.create(
                    user=user,
                    ticket=ticket,
                    message=f'New comment on ticket "#{ticket.id} - {ticket.title}"',
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
            serializer = TicketAttachmentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            attachment = serializer.save(
                ticket=ticket,
                user=request.user,
                file_name=request.FILES['file'].name if 'file' in request.FILES else ''
            )
            return Response(
                TicketAttachmentSerializer(attachment).data,
                status=status.HTTP_201_CREATED
            )


class AttachmentDeleteView(generics.DestroyAPIView):
    """Delete an attachment"""
    queryset = TicketAttachment.objects.all()
    permission_classes = [IsAuthenticated]

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
