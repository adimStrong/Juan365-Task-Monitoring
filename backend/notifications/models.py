from django.db import models
from django.conf import settings
import secrets
import string
from datetime import timedelta
from django.utils import timezone


class TelegramConnectionCode(models.Model):
    """
    Temporary codes for linking Telegram accounts to users.
    Users generate a code, then send it to the bot to link their account.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='telegram_codes'
    )
    code = models.CharField(max_length=8, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.code}'

    @classmethod
    def generate_code(cls):
        """Generate a random 6-character alphanumeric code"""
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(6))

    @classmethod
    def create_for_user(cls, user):
        """Create a new connection code for a user, invalidating old ones"""
        # Delete any existing unused codes for this user
        cls.objects.filter(user=user, used=False).delete()

        # Create new code that expires in 10 minutes
        code = cls.generate_code()
        expires_at = timezone.now() + timedelta(minutes=10)

        return cls.objects.create(
            user=user,
            code=code,
            expires_at=expires_at
        )

    def is_valid(self):
        """Check if the code is still valid (not expired and not used)"""
        return not self.used and timezone.now() < self.expires_at

    def mark_used(self):
        """Mark the code as used"""
        self.used = True
        self.save(update_fields=['used'])


class UserNotificationPreferences(models.Model):
    """
    Per-user notification preferences for Telegram
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    # Notification types
    notify_new_tickets = models.BooleanField(default=True)
    notify_approvals = models.BooleanField(default=True)
    notify_rejections = models.BooleanField(default=True)
    notify_assignments = models.BooleanField(default=True)
    notify_comments = models.BooleanField(default=True)
    notify_completions = models.BooleanField(default=True)
    notify_deadlines = models.BooleanField(default=True)

    # Quiet hours (optional)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'User notification preferences'

    def __str__(self):
        return f'{self.user.username} preferences'
