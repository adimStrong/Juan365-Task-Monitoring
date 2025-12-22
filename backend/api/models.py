from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Custom user model with role and department"""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MANAGER = 'manager', 'Manager'
        MEMBER = 'member', 'Member'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )
    department = models.CharField(max_length=100, blank=True)
    telegram_id = models.CharField(max_length=50, blank=True, help_text='Telegram chat ID for notifications')
    is_approved = models.BooleanField(default=False, help_text='User must be approved by admin to access system')
    approved_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_users'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.role in [self.Role.ADMIN, self.Role.MANAGER]


class Ticket(models.Model):
    """Main ticket model for task management"""

    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    title = models.CharField(max_length=200)
    description = models.TextField()

    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='requested_tickets'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets'
    )
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_to_approve'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Status timestamps for analytics
    approved_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Tagging for categorization
    product = models.CharField(max_length=100, blank=True, help_text='Product this ticket relates to')
    department = models.CharField(max_length=100, blank=True, help_text='Department handling this ticket')

    # Requester confirmation when task is completed
    confirmed_by_requester = models.BooleanField(default=False, help_text='Requester confirms task completion')
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.id} - {self.title}"

    @property
    def is_overdue(self):
        if self.deadline and self.status not in [self.Status.COMPLETED, self.Status.REJECTED]:
            return timezone.now() > self.deadline
        return False

    @property
    def is_idle(self):
        """Check if ticket has been idle for more than 1 day"""
        if self.status == self.Status.IN_PROGRESS:
            return (timezone.now() - self.updated_at).days >= 1
        return False


class TicketCollaborator(models.Model):
    """Collaborators on tickets - multiple users can collaborate on a ticket"""

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='collaborators'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='collaborated_tickets'
    )
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='added_collaborators'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['ticket', 'user']
        ordering = ['added_at']

    def __str__(self):
        return f"{self.user.username} collaborating on #{self.ticket.id}"


class TicketComment(models.Model):
    """Comments on tickets with reply support"""

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ticket_comments'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on #{self.ticket.id}"


class TicketAttachment(models.Model):
    """File attachments for tickets"""

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ticket_attachments'
    )
    file = models.FileField(upload_to='attachments/%Y/%m/')
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name} on #{self.ticket.id}"


class Notification(models.Model):
    """In-app and Telegram notifications"""

    class NotificationType(models.TextChoices):
        NEW_REQUEST = 'new_request', 'New Request'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        ASSIGNED = 'assigned', 'Assigned'
        COMMENT = 'comment', 'Comment'
        DEADLINE = 'deadline', 'Deadline Approaching'
        IDLE = 'idle', 'Task Idle'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices
    )
    is_read = models.BooleanField(default=False)
    telegram_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.notification_type}"


class ActivityLog(models.Model):
    """Activity log for audit trail"""

    class ActionType(models.TextChoices):
        CREATED = 'created', 'Created'
        UPDATED = 'updated', 'Updated'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        ASSIGNED = 'assigned', 'Assigned'
        STARTED = 'started', 'Started'
        COMPLETED = 'completed', 'Completed'
        CONFIRMED = 'confirmed', 'Confirmed by Requester'
        COMMENTED = 'commented', 'Commented'
        DELETED = 'deleted', 'Deleted'

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activities'
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    action = models.CharField(
        max_length=20,
        choices=ActionType.choices
    )
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Activity logs'

    def __str__(self):
        return f"{self.user.username if self.user else 'System'} {self.action} ticket #{self.ticket.id}"


class FileAsset(models.Model):
    """General-purpose file storage for images, videos, and documents"""

    class FileType(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        DOCUMENT = 'document', 'Document'
        OTHER = 'other', 'Other'

    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='assets/%Y/%m/')
    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices,
        default=FileType.OTHER
    )
    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.BigIntegerField(default=0, help_text='File size in bytes')
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_files'
    )
    description = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags')
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: Link to ticket
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='file_assets'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_file_type_display()})"

    @property
    def file_size_display(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
