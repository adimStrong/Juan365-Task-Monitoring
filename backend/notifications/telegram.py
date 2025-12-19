"""
Telegram notification service for the Ticketing System
"""
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Bot token
TELEGRAM_BOT_TOKEN = '8481475169:AAGjcIX9_AwtWQt9PjkHByKGLr2wvq_Dqsk'
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}'


def send_telegram_message(chat_id: str, message: str, parse_mode: str = 'HTML') -> bool:
    """
    Send a message via Telegram bot

    Args:
        chat_id: Telegram chat ID of the recipient
        message: Message text to send
        parse_mode: 'HTML' or 'Markdown'

    Returns:
        True if sent successfully, False otherwise
    """
    if not chat_id:
        logger.warning('No chat_id provided for Telegram notification')
        return False

    try:
        url = f'{TELEGRAM_API_URL}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': parse_mode
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()
        if result.get('ok'):
            logger.info(f'Telegram message sent to {chat_id}')
            return True
        else:
            logger.error(f'Telegram API error: {result}')
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f'Failed to send Telegram message: {e}')
        return False


def format_ticket_notification(notification_type: str, ticket, extra_info: str = '') -> str:
    """
    Format a ticket notification message for Telegram

    Args:
        notification_type: Type of notification
        ticket: Ticket instance
        extra_info: Additional information (e.g., rejection reason)

    Returns:
        Formatted HTML message
    """
    # Emoji mapping for notification types
    emojis = {
        'new_request': '📋',
        'approved': '✅',
        'rejected': '❌',
        'assigned': '👤',
        'comment': '💬',
        'deadline': '⏰',
        'idle': '⚠️',
        'completed': '🎉',
    }

    emoji = emojis.get(notification_type, '📌')

    # Build message
    messages = {
        'new_request': f'''
{emoji} <b>New Ticket Request</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Priority:</b> {ticket.get_priority_display()}
<b>From:</b> {ticket.requester.get_full_name() or ticket.requester.username}

Please review and approve/reject this request.
''',
        'approved': f'''
{emoji} <b>Ticket Approved</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> Approved ✓

Your ticket has been approved and is ready to proceed.
''',
        'rejected': f'''
{emoji} <b>Ticket Rejected</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> Rejected

{f"<b>Reason:</b> {extra_info}" if extra_info else ""}
''',
        'assigned': f'''
{emoji} <b>Ticket Assigned to You</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Priority:</b> {ticket.get_priority_display()}
<b>Deadline:</b> {ticket.deadline.strftime('%Y-%m-%d %H:%M') if ticket.deadline else 'No deadline'}

Please start working on this task.
''',
        'comment': f'''
{emoji} <b>New Comment</b>

<b>#{ticket.id}</b> - {ticket.title}

{extra_info if extra_info else "A new comment was added to the ticket."}
''',
        'deadline': f'''
{emoji} <b>Deadline Approaching!</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Deadline:</b> {ticket.deadline.strftime('%Y-%m-%d %H:%M') if ticket.deadline else 'N/A'}

This task is due soon. Please complete it on time.
''',
        'idle': f'''
{emoji} <b>Task Idle Warning</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> {ticket.get_status_display()}

This task has been idle for more than 1 day. Please update progress.
''',
        'completed': f'''
{emoji} <b>Ticket Completed</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> Completed ✓

The task has been successfully completed!
''',
    }

    return messages.get(notification_type, f'{emoji} Notification for ticket #{ticket.id}')


def notify_user(user, notification_type: str, ticket, extra_info: str = '') -> bool:
    """
    Send notification to a user via Telegram

    Args:
        user: User instance
        notification_type: Type of notification
        ticket: Ticket instance
        extra_info: Additional information

    Returns:
        True if sent successfully
    """
    if not user.telegram_id:
        logger.info(f'User {user.username} has no telegram_id configured')
        return False

    message = format_ticket_notification(notification_type, ticket, extra_info)
    return send_telegram_message(user.telegram_id, message)


def send_test_notification(chat_id: str) -> bool:
    """Send a test notification to verify the bot is working"""
    message = '''
🎉 <b>Ticketing System Connected!</b>

Your Telegram notifications are now active.

You will receive alerts for:
• New ticket requests
• Approvals & rejections
• Task assignments
• Comments
• Deadline reminders
• Idle task warnings
'''
    return send_telegram_message(chat_id, message)
