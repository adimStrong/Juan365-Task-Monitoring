#!/usr/bin/env python
"""One-time script to delete all tickets. Run with: python manage.py shell < delete_all_tickets.py"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticketing.settings')
django.setup()

from api.models import Ticket, TicketComment, TicketAttachment, TicketCollaborator, TicketAnalytics, ActivityLog, Notification

# Delete all related data first
print("Deleting all ticket-related data...")

count = TicketComment.objects.all().count()
TicketComment.objects.all().delete()
print(f"Deleted {count} comments")

count = TicketAttachment.objects.all().count()
TicketAttachment.objects.all().delete()
print(f"Deleted {count} attachments")

count = TicketCollaborator.objects.all().count()
TicketCollaborator.objects.all().delete()
print(f"Deleted {count} collaborators")

count = TicketAnalytics.objects.all().count()
TicketAnalytics.objects.all().delete()
print(f"Deleted {count} analytics records")

count = ActivityLog.objects.all().count()
ActivityLog.objects.all().delete()
print(f"Deleted {count} activity logs")

count = Notification.objects.all().count()
Notification.objects.all().delete()
print(f"Deleted {count} notifications")

# Finally delete all tickets
count = Ticket.objects.all().count()
Ticket.objects.all().delete()
print(f"Deleted {count} tickets")

print("\nAll tickets and related data have been deleted!")
