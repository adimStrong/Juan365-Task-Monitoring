"""Database connection using Django ORM"""
import os
import sys
from pathlib import Path

# Add backend to Python path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / 'backend'
sys.path.insert(0, str(BACKEND_DIR))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticketing.settings')

import django
django.setup()

# Now we can import Django models
from api.models import User, Ticket, FileAsset

def get_all_files(file_type=None, search=None, limit=100):
    """Get all file assets with optional filtering"""
    queryset = FileAsset.objects.all()

    if file_type and file_type != 'all':
        queryset = queryset.filter(file_type=file_type)

    if search:
        queryset = queryset.filter(name__icontains=search)

    return queryset[:limit]

def get_file_by_id(file_id):
    """Get a single file by ID"""
    try:
        return FileAsset.objects.get(id=file_id)
    except FileAsset.DoesNotExist:
        return None

def create_file_asset(name, file_path, file_type, mime_type, file_size, description='', tags='', user_id=None, ticket_id=None):
    """Create a new file asset record"""
    asset = FileAsset(
        name=name,
        file=file_path,
        file_type=file_type,
        mime_type=mime_type,
        file_size=file_size,
        description=description,
        tags=tags,
    )

    if user_id:
        try:
            asset.uploaded_by = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass

    if ticket_id:
        try:
            asset.ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            pass

    asset.save()
    return asset

def delete_file_asset(file_id):
    """Delete a file asset"""
    try:
        asset = FileAsset.objects.get(id=file_id)
        # Delete the actual file
        if asset.file:
            file_path = asset.file.path
            if os.path.exists(file_path):
                os.remove(file_path)
        asset.delete()
        return True
    except FileAsset.DoesNotExist:
        return False

def get_file_stats():
    """Get file statistics"""
    from django.db.models import Sum, Count

    stats = FileAsset.objects.aggregate(
        total_files=Count('id'),
        total_size=Sum('file_size'),
        image_count=Count('id', filter=django.db.models.Q(file_type='image')),
        video_count=Count('id', filter=django.db.models.Q(file_type='video')),
        document_count=Count('id', filter=django.db.models.Q(file_type='document')),
        other_count=Count('id', filter=django.db.models.Q(file_type='other')),
    )

    return stats

def get_all_users():
    """Get all active users for dropdown"""
    return User.objects.filter(is_active=True, is_approved=True).values('id', 'username', 'first_name', 'last_name')

def get_all_tickets():
    """Get all tickets for linking with full details"""
    return Ticket.objects.select_related('requester', 'assigned_to').all()[:50]

def get_ticket_by_id(ticket_id):
    """Get a single ticket by ID with full details"""
    try:
        return Ticket.objects.select_related('requester', 'assigned_to').get(id=ticket_id)
    except Ticket.DoesNotExist:
        return None


# =====================
# AUTHENTICATION
# =====================

def authenticate_user(username, password):
    """Authenticate user and return user object if valid"""
    from django.contrib.auth import authenticate
    user = authenticate(username=username, password=password)
    if user and user.is_active and user.is_approved:
        return user
    return None

def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


# =====================
# TICKET MANAGEMENT
# =====================

def get_user_tickets(user_id, status=None):
    """Get tickets for a specific user (requested by or assigned to)"""
    from django.db.models import Q
    queryset = Ticket.objects.select_related('requester', 'assigned_to').filter(
        Q(requester_id=user_id) | Q(assigned_to_id=user_id)
    )
    if status and status != 'all':
        queryset = queryset.filter(status=status)
    return queryset.order_by('-created_at')

def create_ticket(title, description, priority, deadline, requester_id, assigned_to_id=None):
    """Create a new ticket"""
    from api.models import Notification, ActivityLog
    from notifications.telegram import notify_user

    ticket = Ticket(
        title=title,
        description=description,
        priority=priority,
        deadline=deadline,
        requester_id=requester_id,
        status='requested'
    )

    if assigned_to_id:
        ticket.assigned_to_id = assigned_to_id

    ticket.save()

    # Log activity
    ActivityLog.objects.create(
        user_id=requester_id,
        ticket=ticket,
        action='created',
        details=f'Created ticket: {title}'
    )

    # Notify managers about new request
    managers = User.objects.filter(role__in=['admin', 'manager'], is_active=True, is_approved=True)
    for manager in managers:
        Notification.objects.create(
            user=manager,
            ticket=ticket,
            message=f'New ticket request: #{ticket.id} - {title}',
            notification_type='new_request'
        )
        notify_user(manager, 'new_request', ticket)

    return ticket

def add_ticket_comment(ticket_id, user_id, comment_text, parent_id=None):
    """Add a comment to a ticket"""
    from api.models import TicketComment, Notification
    from notifications.telegram import notify_user

    ticket = Ticket.objects.get(id=ticket_id)

    comment = TicketComment(
        ticket=ticket,
        user_id=user_id,
        comment=comment_text,
        parent_id=parent_id
    )
    comment.save()

    # Notify ticket participants
    participants = set()
    if ticket.requester_id:
        participants.add(ticket.requester_id)
    if ticket.assigned_to_id:
        participants.add(ticket.assigned_to_id)
    participants.discard(user_id)

    for pid in participants:
        user = User.objects.get(id=pid)
        Notification.objects.create(
            user=user,
            ticket=ticket,
            message=f'New comment on ticket #{ticket.id}',
            notification_type='comment'
        )
        notify_user(user, 'comment', ticket, comment_text[:100])

    return comment

def get_ticket_comments(ticket_id):
    """Get comments for a ticket (top-level only, replies nested)"""
    from api.models import TicketComment
    return TicketComment.objects.filter(ticket_id=ticket_id, parent__isnull=True).select_related('user').order_by('created_at')

def get_ticket_attachments(ticket_id):
    """Get attachments for a ticket"""
    from api.models import TicketAttachment
    return TicketAttachment.objects.filter(ticket_id=ticket_id).select_related('user')

def add_ticket_attachment(ticket_id, user_id, file_path, file_name):
    """Add attachment to a ticket"""
    from api.models import TicketAttachment
    attachment = TicketAttachment(
        ticket_id=ticket_id,
        user_id=user_id,
        file=file_path,
        file_name=file_name
    )
    attachment.save()
    return attachment

def get_dashboard_stats(user_id=None):
    """Get dashboard statistics"""
    from django.db.models import Q, Count

    if user_id:
        base_query = Ticket.objects.filter(Q(requester_id=user_id) | Q(assigned_to_id=user_id))
    else:
        base_query = Ticket.objects.all()

    stats = {
        'total': base_query.count(),
        'requested': base_query.filter(status='requested').count(),
        'approved': base_query.filter(status='approved').count(),
        'in_progress': base_query.filter(status='in_progress').count(),
        'completed': base_query.filter(status='completed').count(),
        'rejected': base_query.filter(status='rejected').count(),
    }

    return stats
