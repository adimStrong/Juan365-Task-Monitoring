"""
Management command to send overdue ticket reminders.
Sends notifications to assigned users and managers about overdue tickets.

Usage:
    python manage.py send_overdue_reminders
    python manage.py send_overdue_reminders --dry-run  # Preview without sending
    python manage.py send_overdue_reminders --force    # Ignore time restrictions
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import Ticket, Notification
from notifications.telegram import notify_user, send_telegram_message, create_ticket_keyboard
from django.conf import settings


class Command(BaseCommand):
    help = 'Send reminders for overdue tickets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview which reminders would be sent without actually sending them'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send reminders regardless of time or previous reminder sent'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        now = timezone.now()

        # Only run between 8am and 8pm unless forced
        if not force:
            hour = now.hour
            if hour < 8 or hour >= 20:
                self.stdout.write(
                    self.style.WARNING(f'Outside operating hours (8am-8pm). Current hour: {hour}. Use --force to override.')
                )
                return

        # Find overdue tickets that are still active
        active_statuses = [
            Ticket.Status.REQUESTED,
            Ticket.Status.PENDING_CREATIVE,
            Ticket.Status.APPROVED,
            Ticket.Status.IN_PROGRESS
        ]

        overdue_tickets = Ticket.objects.filter(
            status__in=active_statuses,
            deadline__lt=now,
            is_deleted=False
        ).select_related('assigned_to', 'requester', 'target_department')

        if not overdue_tickets.exists():
            self.stdout.write(self.style.SUCCESS('No overdue tickets found.'))
            return

        self.stdout.write(f'Found {overdue_tickets.count()} overdue ticket(s)')

        reminders_sent = 0
        skipped = 0

        for ticket in overdue_tickets:
            # Check if we already sent a reminder recently (within 4 hours)
            if not force and ticket.last_overdue_reminder_sent:
                hours_since_last = (now - ticket.last_overdue_reminder_sent).total_seconds() / 3600
                if hours_since_last < 4:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Skipping #{ticket.id} - reminder sent {hours_since_last:.1f}h ago'
                        )
                    )
                    skipped += 1
                    continue

            # Calculate how overdue
            overdue_hours = (now - ticket.deadline).total_seconds() / 3600
            overdue_text = f'{int(overdue_hours)}h' if overdue_hours < 24 else f'{int(overdue_hours/24)}d {int(overdue_hours%24)}h'

            if dry_run:
                self.stdout.write(
                    f'  [DRY RUN] Would send reminder for #{ticket.id} - {ticket.title} '
                    f'(overdue by {overdue_text})'
                )
                reminders_sent += 1
                continue

            # Create in-app notification
            notification_message = f'#{ticket.id} - {ticket.title} ({ticket.get_priority_display()}) - OVERDUE by {overdue_text}!'

            # Notify assigned user
            if ticket.assigned_to:
                Notification.objects.create(
                    user=ticket.assigned_to,
                    ticket=ticket,
                    notification_type='overdue',
                    message=notification_message
                )

            # Notify requester
            if ticket.requester and ticket.requester != ticket.assigned_to:
                Notification.objects.create(
                    user=ticket.requester,
                    ticket=ticket,
                    notification_type='overdue',
                    message=notification_message
                )

            # Send Telegram notification (only to Rob and Yeng)
            telegram_message = f'''
🚨 <b>OVERDUE TICKET ALERT</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Priority:</b> {ticket.get_priority_display()}
<b>Overdue by:</b> {overdue_text}
<b>Deadline was:</b> {ticket.deadline.strftime('%Y-%m-%d %H:%M')}
<b>Assigned to:</b> {ticket.assigned_to.get_full_name() if ticket.assigned_to else 'Unassigned'}

Please complete this task immediately!
'''
            keyboard = create_ticket_keyboard(ticket.id)

            # Only send to Rob and Yeng (specific telegram handles)
            NOTIFY_TELEGRAM_IDS = ['@robjuan365', '@yengj365']
            for telegram_id in NOTIFY_TELEGRAM_IDS:
                send_telegram_message(telegram_id, telegram_message, reply_markup=keyboard)

            # Also send to group with @mentions
            group_chat_id = getattr(settings, 'TELEGRAM_GROUP_CHAT_ID', '')
            if group_chat_id:
                group_message = f'@robjuan365 @yengj365

{telegram_message}'
                send_telegram_message(group_chat_id, group_message, reply_markup=keyboard)

            # Update last reminder sent
            ticket.last_overdue_reminder_sent = now
            ticket.save(update_fields=['last_overdue_reminder_sent'])

            self.stdout.write(
                self.style.SUCCESS(
                    f'  Sent reminder for #{ticket.id} - {ticket.title} (overdue by {overdue_text})'
                )
            )
            reminders_sent += 1

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would have sent {reminders_sent} reminder(s)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Sent {reminders_sent} reminder(s), skipped {skipped}'))
