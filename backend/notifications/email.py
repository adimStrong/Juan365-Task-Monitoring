"""
Email notification service for the Ticketing System
Sends notifications to users via email
"""
import logging
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def is_email_enabled():
    """Check if email notifications are enabled"""
    enabled = getattr(settings, 'EMAIL_ENABLED', False)
    host_user = getattr(settings, 'EMAIL_HOST_USER', '')
    host_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    print(f'[EMAIL DEBUG] EMAIL_ENABLED={enabled}, HOST_USER={host_user[:10] if host_user else "not set"}..., PASSWORD_SET={bool(host_password)}')
    return enabled


def send_email_notification(to_email: str, subject: str, html_message: str,
                           plain_message: str = None) -> bool:
    """
    Send an email notification

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_message: HTML content of the email
        plain_message: Plain text version (auto-generated if not provided)

    Returns:
        True if sent successfully, False otherwise
    """
    if not to_email:
        logger.warning('No email address provided for notification')
        return False

    if not is_email_enabled():
        print(f'[EMAIL DEBUG] Email notifications DISABLED - skipping send to {to_email}')
        return False

    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@juan365.com')
        print(f'[EMAIL DEBUG] Attempting to send email to {to_email} from {from_email}')

        # Generate plain text from HTML if not provided
        if not plain_message:
            plain_message = strip_tags(html_message)

        # Create email with both HTML and plain text
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=[to_email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)

        print(f'[EMAIL DEBUG] SUCCESS - Email sent to {to_email}: {subject}')
        return True

    except Exception as e:
        print(f'[EMAIL DEBUG] FAILED - Error sending email to {to_email}: {e}')
        import traceback
        traceback.print_exc()
        return False


def format_ticket_email(notification_type: str, ticket, extra_info: str = '') -> dict:
    """
    Format a ticket notification email

    Args:
        notification_type: Type of notification
        ticket: Ticket instance
        extra_info: Additional information

    Returns:
        dict with 'subject' and 'html' keys
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://juan365-ticketing-frontend.vercel.app')
    ticket_url = f'{frontend_url}/tickets/{ticket.id}'

    # Subject mapping
    subjects = {
        'new_request': f'[Ticket #{ticket.id}] New Request: {ticket.title}',
        'approved': f'[Ticket #{ticket.id}] Approved: {ticket.title}',
        'rejected': f'[Ticket #{ticket.id}] Rejected: {ticket.title}',
        'assigned': f'[Ticket #{ticket.id}] Assigned to You: {ticket.title}',
        'comment': f'[Ticket #{ticket.id}] New Comment: {ticket.title}',
        'deadline': f'[Ticket #{ticket.id}] Deadline Approaching: {ticket.title}',
        'idle': f'[Ticket #{ticket.id}] Task Idle Warning: {ticket.title}',
        'completed': f'[Ticket #{ticket.id}] Completed: {ticket.title}',
        'confirmed': f'[Ticket #{ticket.id}] Completion Confirmed: {ticket.title}',
        'pending_creative': f'[Ticket #{ticket.id}] Pending Creative Approval: {ticket.title}',
    }

    subject = subjects.get(notification_type, f'[Ticket #{ticket.id}] Update: {ticket.title}')

    # Get requester info
    requester_name = ticket.requester.get_full_name() or ticket.requester.username

    # Build HTML email
    html_templates = {
        'new_request': f'''
            <h2>New Ticket Request</h2>
            <p>A new ticket has been submitted and requires your review.</p>
            <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Ticket ID</strong></td><td style="padding: 8px; border: 1px solid #ddd;">#{ticket.id}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Title</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{ticket.title}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Priority</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{ticket.get_priority_display()}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Requester</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{requester_name}</td></tr>
            </table>
            <p style="margin-top: 20px;">Please review and approve/reject this request.</p>
        ''',
        'approved': f'''
            <h2>Ticket Approved</h2>
            <p>Your ticket has been approved and is ready to proceed.</p>
            <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Ticket ID</strong></td><td style="padding: 8px; border: 1px solid #ddd;">#{ticket.id}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Title</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{ticket.title}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Status</strong></td><td style="padding: 8px; border: 1px solid #ddd; color: green;">Approved</td></tr>
            </table>
        ''',
        'rejected': f'''
            <h2>Ticket Rejected</h2>
            <p>Unfortunately, your ticket has been rejected.</p>
            <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Ticket ID</strong></td><td style="padding: 8px; border: 1px solid #ddd;">#{ticket.id}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Title</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{ticket.title}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Status</strong></td><td style="padding: 8px; border: 1px solid #ddd; color: red;">Rejected</td></tr>
                {f'<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Reason</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{extra_info}</td></tr>' if extra_info else ''}
            </table>
        ''',
        'assigned': f'''
            <h2>Ticket Assigned to You</h2>
            <p>A ticket has been assigned to you. Please start working on it.</p>
            <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Ticket ID</strong></td><td style="padding: 8px; border: 1px solid #ddd;">#{ticket.id}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Title</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{ticket.title}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Priority</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{ticket.get_priority_display()}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Deadline</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{ticket.deadline.strftime('%Y-%m-%d %H:%M') if ticket.deadline else 'No deadline'}</td></tr>
            </table>
        ''',
        'comment': f'''
            <h2>New Comment on Ticket</h2>
            <p>A new comment has been added to the ticket.</p>
            <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Ticket ID</strong></td><td style="padding: 8px; border: 1px solid #ddd;">#{ticket.id}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Title</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{ticket.title}</td></tr>
            </table>
            {f'<div style="margin-top: 15px; padding: 10px; background: #f5f5f5; border-radius: 5px;">{extra_info}</div>' if extra_info else ''}
        ''',
        'completed': f'''
            <h2>Ticket Completed</h2>
            <p>The task has been marked as completed. Please confirm completion.</p>
            <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Ticket ID</strong></td><td style="padding: 8px; border: 1px solid #ddd;">#{ticket.id}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Title</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{ticket.title}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Status</strong></td><td style="padding: 8px; border: 1px solid #ddd; color: blue;">Completed</td></tr>
            </table>
        ''',
        'pending_creative': f'''
            <h2>Ticket Pending Creative Approval</h2>
            <p>A ticket is awaiting Creative department approval.</p>
            <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Ticket ID</strong></td><td style="padding: 8px; border: 1px solid #ddd;">#{ticket.id}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Title</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{ticket.title}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Priority</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{ticket.get_priority_display()}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Requester</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{requester_name}</td></tr>
            </table>
            <p style="margin-top: 20px;">Please review and approve this request.</p>
        ''',
    }

    html_content = html_templates.get(notification_type, f'''
        <h2>Ticket Update</h2>
        <p>There's an update on ticket #{ticket.id}: {ticket.title}</p>
    ''')

    # Wrap in email template
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background: #fff; }}
            .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            .button {{ display: inline-block; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 5px; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0;">Juan365 Ticketing</h1>
            </div>
            <div class="content">
                {html_content}
                <p style="margin-top: 20px;">
                    <a href="{ticket_url}" class="button">View Ticket</a>
                </p>
            </div>
            <div class="footer">
                <p>This is an automated message from Juan365 Ticketing System.</p>
                <p>Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    '''

    return {'subject': subject, 'html': html}


def notify_user_email(user, notification_type: str, ticket, extra_info: str = '') -> bool:
    """
    Send email notification to a user

    Args:
        user: User instance
        notification_type: Type of notification
        ticket: Ticket instance
        extra_info: Additional information

    Returns:
        True if sent successfully
    """
    if not user or not user.email:
        logger.info(f'User {user.username if user else "None"} has no email configured')
        return False

    email_data = format_ticket_email(notification_type, ticket, extra_info)
    return send_email_notification(user.email, email_data['subject'], email_data['html'])


def notify_managers_email(notification_type: str, ticket, extra_info: str = '') -> list:
    """
    Send email notification to all managers

    Args:
        notification_type: Type of notification
        ticket: Ticket instance
        extra_info: Additional information

    Returns:
        List of results
    """
    from api.models import User

    results = []
    managers = User.objects.filter(
        role__in=['manager', 'admin'],
        is_active=True,
        is_approved=True
    ).exclude(email='').exclude(email__isnull=True)

    email_data = format_ticket_email(notification_type, ticket, extra_info)

    for manager in managers:
        success = send_email_notification(manager.email, email_data['subject'], email_data['html'])
        results.append({'user': manager.username, 'email': manager.email, 'success': success})

    return results
