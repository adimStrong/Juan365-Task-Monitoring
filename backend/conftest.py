"""
Pytest configuration and fixtures for Juan365 Ticketing System tests
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from api.models import Ticket, TicketComment, TicketAttachment, TicketCollaborator, Notification, ActivityLog

User = get_user_model()


# ============================================================
# USER FIXTURES
# ============================================================

@pytest.fixture
def api_client():
    """Return an unauthenticated API client"""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create and return an admin user"""
    user = User.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='adminpass123',
        first_name='Admin',
        last_name='User',
        role='admin',
        is_approved=True,
        is_staff=True,
        is_superuser=True
    )
    return user


@pytest.fixture
def manager_user(db):
    """Create and return a manager user"""
    user = User.objects.create_user(
        username='manager_test',
        email='manager@test.com',
        password='managerpass123',
        first_name='Manager',
        last_name='User',
        role='manager',
        is_approved=True
    )
    return user


@pytest.fixture
def member_user(db):
    """Create and return a regular member user"""
    user = User.objects.create_user(
        username='member_test',
        email='member@test.com',
        password='memberpass123',
        first_name='Member',
        last_name='User',
        role='member',
        is_approved=True
    )
    return user


@pytest.fixture
def unapproved_user(db):
    """Create and return an unapproved user"""
    user = User.objects.create_user(
        username='unapproved_test',
        email='unapproved@test.com',
        password='unapprovedpass123',
        first_name='Unapproved',
        last_name='User',
        role='member',
        is_approved=False
    )
    return user


@pytest.fixture
def inactive_user(db):
    """Create and return an inactive user"""
    user = User.objects.create_user(
        username='inactive_test',
        email='inactive@test.com',
        password='inactivepass123',
        first_name='Inactive',
        last_name='User',
        role='member',
        is_approved=True,
        is_active=False
    )
    return user


# ============================================================
# AUTHENTICATED CLIENT FIXTURES
# ============================================================

def get_tokens_for_user(user):
    """Generate JWT tokens for a user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an API client authenticated as admin"""
    tokens = get_tokens_for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
    api_client.user = admin_user
    return api_client


@pytest.fixture
def manager_client(api_client, manager_user):
    """Return an API client authenticated as manager"""
    tokens = get_tokens_for_user(manager_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
    api_client.user = manager_user
    return api_client


@pytest.fixture
def member_client(api_client, member_user):
    """Return an API client authenticated as member"""
    tokens = get_tokens_for_user(member_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
    api_client.user = member_user
    return api_client


# ============================================================
# TICKET FIXTURES
# ============================================================

@pytest.fixture
def ticket_requested(db, member_user):
    """Create a ticket in requested status"""
    return Ticket.objects.create(
        title='Test Ticket - Requested',
        description='This is a test ticket in requested status',
        requester=member_user,
        status='requested',
        priority='medium'
    )


@pytest.fixture
def ticket_approved(db, member_user, manager_user):
    """Create a ticket in approved status"""
    return Ticket.objects.create(
        title='Test Ticket - Approved',
        description='This is a test ticket in approved status',
        requester=member_user,
        approver=manager_user,
        status='approved',
        priority='high'
    )


@pytest.fixture
def ticket_assigned(db, member_user, manager_user, admin_user):
    """Create a ticket that is assigned"""
    return Ticket.objects.create(
        title='Test Ticket - Assigned',
        description='This is a test ticket that is assigned',
        requester=member_user,
        approver=manager_user,
        assigned_to=admin_user,
        status='approved',
        priority='high'
    )


@pytest.fixture
def ticket_in_progress(db, member_user, manager_user, admin_user):
    """Create a ticket in progress"""
    return Ticket.objects.create(
        title='Test Ticket - In Progress',
        description='This is a test ticket in progress',
        requester=member_user,
        approver=manager_user,
        assigned_to=admin_user,
        status='in_progress',
        priority='urgent'
    )


@pytest.fixture
def ticket_completed(db, member_user, manager_user, admin_user):
    """Create a completed ticket"""
    return Ticket.objects.create(
        title='Test Ticket - Completed',
        description='This is a test completed ticket',
        requester=member_user,
        approver=manager_user,
        assigned_to=admin_user,
        status='completed',
        priority='medium'
    )


@pytest.fixture
def ticket_with_deadline(db, member_user):
    """Create a ticket with a deadline"""
    from django.utils import timezone
    from datetime import timedelta
    return Ticket.objects.create(
        title='Test Ticket - With Deadline',
        description='This is a test ticket with deadline',
        requester=member_user,
        status='requested',
        priority='high',
        deadline=timezone.now() + timedelta(days=7)
    )


@pytest.fixture
def multiple_tickets(db, member_user, manager_user, admin_user):
    """Create multiple tickets for list testing"""
    tickets = []
    statuses = ['requested', 'approved', 'in_progress', 'completed', 'rejected']
    priorities = ['low', 'medium', 'high', 'urgent']

    for i in range(10):
        ticket = Ticket.objects.create(
            title=f'Test Ticket {i+1}',
            description=f'Description for ticket {i+1}',
            requester=member_user if i % 2 == 0 else admin_user,
            status=statuses[i % len(statuses)],
            priority=priorities[i % len(priorities)]
        )
        tickets.append(ticket)
    return tickets


# ============================================================
# COMMENT FIXTURES
# ============================================================

@pytest.fixture
def ticket_comment(db, ticket_requested, member_user):
    """Create a comment on a ticket"""
    return TicketComment.objects.create(
        ticket=ticket_requested,
        user=member_user,
        comment='This is a test comment'
    )


@pytest.fixture
def comment_with_reply(db, ticket_requested, member_user, manager_user):
    """Create a comment with a reply"""
    parent = TicketComment.objects.create(
        ticket=ticket_requested,
        user=member_user,
        comment='This is the parent comment'
    )
    reply = TicketComment.objects.create(
        ticket=ticket_requested,
        user=manager_user,
        parent=parent,
        comment='This is a reply to the parent comment'
    )
    return parent, reply


# ============================================================
# COLLABORATOR FIXTURES
# ============================================================

@pytest.fixture
def ticket_with_collaborator(db, ticket_approved, admin_user, manager_user):
    """Create a ticket with a collaborator"""
    collaborator = TicketCollaborator.objects.create(
        ticket=ticket_approved,
        user=admin_user,
        added_by=manager_user
    )
    return ticket_approved, collaborator


# ============================================================
# NOTIFICATION FIXTURES
# ============================================================

@pytest.fixture
def user_notification(db, member_user, ticket_requested):
    """Create a notification for a user"""
    return Notification.objects.create(
        user=member_user,
        ticket=ticket_requested,
        message='Test notification message',
        notification_type='new_request',
        is_read=False
    )


@pytest.fixture
def multiple_notifications(db, member_user, ticket_requested):
    """Create multiple notifications"""
    notifications = []
    types = ['new_request', 'approved', 'assigned', 'comment']
    for i, ntype in enumerate(types):
        notif = Notification.objects.create(
            user=member_user,
            ticket=ticket_requested,
            message=f'Notification {i+1}',
            notification_type=ntype,
            is_read=i % 2 == 0  # Alternate read/unread
        )
        notifications.append(notif)
    return notifications


# ============================================================
# ACTIVITY LOG FIXTURES
# ============================================================

@pytest.fixture
def activity_log(db, member_user, ticket_requested):
    """Create an activity log entry"""
    return ActivityLog.objects.create(
        user=member_user,
        ticket=ticket_requested,
        action='created',
        details='Ticket created'
    )


# ============================================================
# UTILITY FIXTURES
# ============================================================

@pytest.fixture
def valid_registration_data():
    """Return valid user registration data"""
    return {
        'username': 'newuser',
        'email': 'newuser@test.com',
        'password': 'NewPass123!',
        'password_confirm': 'NewPass123!',
        'first_name': 'New',
        'last_name': 'User'
    }


@pytest.fixture
def valid_ticket_data():
    """Return valid ticket creation data"""
    return {
        'title': 'New Test Ticket',
        'description': 'This is a new test ticket description',
        'priority': 'medium'
    }
