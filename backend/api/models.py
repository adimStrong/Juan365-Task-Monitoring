from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Department(models.Model):
    """Department model with manager for approval workflow"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments'
    )
    is_creative = models.BooleanField(default=False, help_text='Flag for Creative department')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model for ticket categorization"""

    class Category(models.TextChoices):
        GENERAL = 'general', 'General'
        ADS = 'ads', 'Ads'
        TELEGRAM = 'telegram', 'Telegram'

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
        help_text='Product category for filtering by request type'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


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
    user_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        help_text='Department this user belongs to'
    )
    department = models.CharField(max_length=100, blank=True, help_text='Legacy field - use user_department instead')
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

    # Password management fields
    is_locked = models.BooleanField(default=False, help_text='Account locked due to failed login attempts')
    locked_at = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.role in [self.Role.ADMIN, self.Role.MANAGER]

    @property
    def is_creative_manager(self):
        """Check if user is the Creative department manager"""
        try:
            creative_dept = Department.objects.get(is_creative=True)
            return creative_dept.manager == self
        except Department.DoesNotExist:
            return False


class Ticket(models.Model):
    """Main ticket model for task management"""

    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        PENDING_CREATIVE = 'pending_creative', 'Pending Creative Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    class RequestType(models.TextChoices):
        SOCMED_POSTING = 'socmed_posting', 'Socmed Posting'
        WEBSITE_BANNER = 'website_banner', 'Website Banner (H5 & WEB)'
        PHOTOSHOOT = 'photoshoot', 'Photoshoot'
        VIDEOSHOOT = 'videoshoot', 'Videoshoot'
        LIVE_PRODUCTION = 'live_production', 'Live Production'
        ADS = 'ads', 'Ads'
        TELEGRAM_CHANNEL = 'telegram_channel', 'Telegram Official Channel'

    class FileFormat(models.TextChoices):
        STILL = 'still', 'Still'
        GIF = 'gif', 'Gif'
        VIDEO_LANDSCAPE = 'video_landscape', 'Video (Landscape)'
        VIDEO_PORTRAIT = 'video_portrait', 'Video (Portrait)'

    class Criteria(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'

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
        default=Status.REQUESTED,
        db_index=True  # Indexed for filtering
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True  # Indexed for filtering
    )

    deadline = models.DateTimeField(null=True, blank=True, db_index=True)  # Indexed for overdue queries
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)  # Indexed for date range queries
    updated_at = models.DateTimeField(auto_now=True)

    # Status timestamps for analytics
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    # Two-step approval tracking
    dept_approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dept_approved_tickets',
        help_text='Department manager who gave first approval'
    )
    dept_approved_at = models.DateTimeField(null=True, blank=True, help_text='When department manager approved')
    assigned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Scheduled task fields (for videoshoot/photoshoot/live_production)
    scheduled_start = models.DateTimeField(
        null=True, blank=True,
        help_text='Scheduled start time (for videoshoot/photoshoot/live_production)'
    )
    scheduled_end = models.DateTimeField(
        null=True, blank=True,
        help_text='Scheduled end time (for videoshoot/photoshoot/live_production)'
    )
    actual_end = models.DateTimeField(
        null=True, blank=True,
        help_text='Actual end time (input by assigned person on completion)'
    )

    # Overdue reminder tracking
    last_overdue_reminder_sent = models.DateTimeField(
        null=True, blank=True,
        help_text='When the last overdue reminder was sent'
    )

    # Categorization with ForeignKeys
    ticket_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        help_text='Product this ticket relates to'
    )
    target_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        help_text='Department handling this ticket'
    )

    # Legacy char fields (kept for backwards compatibility)
    product = models.CharField(max_length=100, blank=True, help_text='Legacy field')
    department = models.CharField(max_length=100, blank=True, help_text='Legacy field')

    # Approval routing
    pending_approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_approvals',
        help_text='User who needs to approve this ticket'
    )

    # Analytics fields
    class Complexity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    complexity = models.CharField(
        max_length=20,
        choices=Complexity.choices,
        default=Complexity.MEDIUM
    )
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    # Requester confirmation when task is completed
    confirmed_by_requester = models.BooleanField(default=False, help_text='Requester confirms task completion')
    confirmed_at = models.DateTimeField(null=True, blank=True)

    # Soft delete fields
    is_deleted = models.BooleanField(default=False, db_index=True, help_text='Soft delete flag')
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_tickets',
        help_text='User who deleted this ticket'
    )

    # Rollback tracking
    last_rollback_at = models.DateTimeField(null=True, blank=True, help_text='Last time this ticket was rolled back')
    rollback_count = models.IntegerField(default=0, help_text='Number of times this ticket has been rolled back')

    # New fields for request type and file format
    request_type = models.CharField(
        max_length=50,
        choices=RequestType.choices,
        blank=True,
        help_text='Type of creative request'
    )
    file_format = models.CharField(
        max_length=50,
        choices=FileFormat.choices,
        blank=True,
        help_text='File format (only for Socmed Posting)'
    )

    # Revision tracking
    revision_count = models.IntegerField(default=0, help_text='Number of revision requests')

    # Quantity and criteria fields for request types
    quantity = models.PositiveIntegerField(
        default=1,
        help_text='Number of creatives needed (max 1000)'
    )
    criteria = models.CharField(
        max_length=10,
        choices=Criteria.choices,
        blank=True,
        help_text='Creative type: image or video'
    )

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


class TicketProductItem(models.Model):
    """For Ads and Telegram request types - stores multiple products with quantities"""

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='product_items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='ticket_items'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text='Quantity for this product (max 1000)'
    )
    criteria = models.CharField(
        max_length=10,
        choices=Ticket.Criteria.choices,
        blank=True,
        help_text='Auto-set for Ads: VID=video, STATIC=image'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        # Auto-set criteria for Ads products based on product name
        if self.product and not self.criteria:
            if 'VID' in self.product.name.upper():
                self.criteria = 'video'
            elif 'STATIC' in self.product.name.upper():
                self.criteria = 'image'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class TicketAnalytics(models.Model):
    """Analytics data for ticket lifecycle tracking"""

    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.CASCADE,
        related_name='analytics'
    )

    # Timestamps for each stage
    created_at = models.DateTimeField(help_text='When ticket was created')
    dept_approved_at = models.DateTimeField(null=True, blank=True, help_text='When dept manager approved')
    creative_approved_at = models.DateTimeField(null=True, blank=True, help_text='When creative approved')
    assigned_at = models.DateTimeField(null=True, blank=True, help_text='When ticket was assigned')
    acknowledged_at = models.DateTimeField(null=True, blank=True, help_text='When designer acknowledged/started editing')
    started_at = models.DateTimeField(null=True, blank=True, help_text='When work started')
    completed_at = models.DateTimeField(null=True, blank=True, help_text='When work completed')
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text='When requester confirmed')

    # Rollback tracking
    last_rollback_at = models.DateTimeField(null=True, blank=True, help_text='Last rollback time')
    rollback_count = models.IntegerField(default=0, help_text='Total rollback count')

    # Duration calculations (in minutes)
    time_to_dept_approval = models.IntegerField(null=True, blank=True, help_text='Minutes from creation to dept approval')
    time_to_creative_approval = models.IntegerField(null=True, blank=True, help_text='Minutes from dept approval to creative approval')
    time_to_assignment = models.IntegerField(null=True, blank=True, help_text='Minutes from creative approval to assignment')
    time_to_acknowledge = models.IntegerField(null=True, blank=True, help_text='Minutes from assignment to acknowledgment')
    time_to_start = models.IntegerField(null=True, blank=True, help_text='Minutes from assignment to start')
    time_to_complete = models.IntegerField(null=True, blank=True, help_text='Minutes from start to completion')
    total_cycle_time = models.IntegerField(null=True, blank=True, help_text='Total minutes from creation to confirmation')

    class Meta:
        verbose_name_plural = 'Ticket analytics'

    def __str__(self):
        return f"Analytics for Ticket #{self.ticket.id}"

    def calculate_durations(self):
        """Calculate all duration fields based on timestamps"""
        if self.dept_approved_at and self.created_at:
            self.time_to_dept_approval = int((self.dept_approved_at - self.created_at).total_seconds() / 60)

        if self.creative_approved_at and self.dept_approved_at:
            self.time_to_creative_approval = int((self.creative_approved_at - self.dept_approved_at).total_seconds() / 60)
        elif self.creative_approved_at and self.created_at:
            # For creative dept users who skip dept approval
            self.time_to_creative_approval = int((self.creative_approved_at - self.created_at).total_seconds() / 60)

        if self.assigned_at and self.creative_approved_at:
            self.time_to_assignment = int((self.assigned_at - self.creative_approved_at).total_seconds() / 60)

        # Time from assignment to acknowledgment (designer clicks "Start Editing") - stored in seconds
        if self.acknowledged_at and self.assigned_at:
            self.time_to_acknowledge = int((self.acknowledged_at - self.assigned_at).total_seconds())

        if self.started_at and self.assigned_at:
            self.time_to_start = int((self.started_at - self.assigned_at).total_seconds() / 60)

        if self.completed_at and self.started_at:
            self.time_to_complete = int((self.completed_at - self.started_at).total_seconds() / 60)

        if self.confirmed_at and self.created_at:
            self.total_cycle_time = int((self.confirmed_at - self.created_at).total_seconds() / 60)

        self.save()


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
        PENDING_CREATIVE = 'pending_creative', 'Pending Creative Approval'
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
    """Activity log for audit trail with state snapshots for rollback"""

    class ActionType(models.TextChoices):
        CREATED = 'created', 'Created'
        UPDATED = 'updated', 'Updated'
        DEPT_APPROVED = 'dept_approved', 'Department Approved'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        ASSIGNED = 'assigned', 'Assigned'
        STARTED = 'started', 'Started'
        COMPLETED = 'completed', 'Completed'
        CONFIRMED = 'confirmed', 'Confirmed by Requester'
        REVISION_REQUESTED = 'revision_requested', 'Revision Requested'
        COMMENTED = 'commented', 'Commented'
        DELETED = 'deleted', 'Deleted'
        ROLLBACK = 'rollback', 'Rolled Back'

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
    snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text='Ticket state snapshot at this point for rollback functionality'
    )
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


class PasswordResetToken(models.Model):
    """Token for password reset functionality"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Password reset for {self.user.username}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired


class LoginAttempt(models.Model):
    """Track login attempts for security auditing"""

    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = 'Success' if self.success else 'Failed'
        return f"{self.username} - {status} - {self.created_at}"
