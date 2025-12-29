"""
Management command to send approval reminders for pending tickets.
Should be run every hour via Task Scheduler.
Only sends reminders between 8am-8pm and if 4+ hours since last reminder.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from api.models import Ticket, Notification
from notifications.telegram import notify_user


class Command(BaseCommand):
    help = 'Send approval reminders for tickets pending approval for too long'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ignore time of day restrictions (8am-8pm)',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options['dry_run']
        force = options['force']

        # Only run between 8am and 8pm unless forced
        if not force and (now.hour < 8 or now.hour >= 20):
            self.stdout.write(
                self.style.WARNING(f'Outside reminder hours (8am-8pm). Current hour: {now.hour}. Use --force to override.')
            )
            return

        four_hours_ago = now - timedelta(hours=4)

        # Find tickets needing reminders:
        # - Status is 'requested' or 'pending_creative'
        # - Has a pending_approver
        # - Not deleted
        # - Either never reminded OR last reminded more than 4 hours ago
        pending_tickets = Ticket.objects.filter(
            status__in=[Ticket.Status.REQUESTED, Ticket.Status.PENDING_CREATIVE],
            pending_approver__isnull=False,
            is_deleted=False,
        ).filter(
            Q(last_approval_reminder_sent__isnull=True) |
            Q(last_approval_reminder_sent__lte=four_hours_ago)
        ).select_related('pending_approver', 'requester')

        if not pending_tickets.exists():
            self.stdout.write(self.style.SUCCESS('No tickets need reminders at this time.'))
            return

        self.stdout.write(f'Found {pending_tickets.count()} tickets needing reminders...')

        sent_count = 0
        for ticket in pending_tickets:
            approver = ticket.pending_approver

            if dry_run:
                self.stdout.write(
                    f'  [DRY RUN] Would remind {approver.username} about #{ticket.id}: {ticket.title}'
                )
                continue

            # Create in-app notification
            from api.views import format_notification_message
            message = format_notification_message(ticket, 'reminder')

            Notification.objects.create(
                user=approver,
                ticket=ticket,
                message=message,
                notification_type=Notification.NotificationType.NEW_REQUEST
            )

            # Send Telegram notification
            notify_user(
                approver,
                'reminder',
                ticket,
                send_to_group=False,  # Don't spam the group with reminders
                actor=None
            )

            # Update last reminder timestamp
            ticket.last_approval_reminder_sent = now
            ticket.save(update_fields=['last_approval_reminder_sent'])

            sent_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'  Reminded {approver.username} about #{ticket.id}: {ticket.title}')
            )

        self.stdout.write(self.style.SUCCESS(f'\nSent {sent_count} reminder(s).'))
