"""
Telegram notification service for the Ticketing System
Sends notifications to both group chat and individual users
"""
import requests
import logging
import json
from django.conf import settings

logger = logging.getLogger(__name__)


def get_api_url():
    """Get Telegram API URL using token from settings"""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token:
        return None
    return f'https://api.telegram.org/bot{token}'


def send_telegram_message(chat_id: str, message: str, parse_mode: str = 'HTML',
                          reply_markup: dict = None) -> bool:
    """
    Send a message via Telegram bot

    Args:
        chat_id: Telegram chat ID of the recipient
        message: Message text to send
        parse_mode: 'HTML' or 'Markdown'
        reply_markup: Optional inline keyboard markup

    Returns:
        True if sent successfully, False otherwise
    """
    if not chat_id:
        logger.warning('No chat_id provided for Telegram notification')
        return False

    api_url = get_api_url()
    if not api_url:
        logger.warning('Telegram bot token not configured')
        return False

    try:
        url = f'{api_url}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': parse_mode
        }

        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)

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


def create_ticket_keyboard(ticket_id: int, show_actions: bool = False) -> dict:
    """
    Create inline keyboard for ticket notifications

    Args:
        ticket_id: The ticket ID
        show_actions: Whether to show approve/reject buttons (for managers)

    Returns:
        Inline keyboard markup dict
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://juan365-ticketing-frontend.vercel.app')
    ticket_url = f'{frontend_url}/tickets/{ticket_id}'

    buttons = [[{'text': 'View Ticket', 'url': ticket_url}]]

    if show_actions:
        buttons.append([
            {'text': 'Approve', 'callback_data': f'approve_{ticket_id}'},
            {'text': 'Reject', 'callback_data': f'reject_{ticket_id}'}
        ])

    return {'inline_keyboard': buttons}


def send_group_notification(notification_type: str, ticket, extra_info: str = '') -> bool:
    """
    Send notification to the configured Telegram group

    Args:
        notification_type: Type of notification
        ticket: Ticket instance
        extra_info: Additional information

    Returns:
        True if sent successfully
    """
    group_chat_id = getattr(settings, 'TELEGRAM_GROUP_CHAT_ID', '')
    if not group_chat_id:
        logger.info('Telegram group chat ID not configured')
        return False

    message = format_ticket_notification(notification_type, ticket, extra_info)
    show_actions = notification_type == 'new_request'
    keyboard = create_ticket_keyboard(ticket.id, show_actions=show_actions)

    return send_telegram_message(group_chat_id, message, reply_markup=keyboard)


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
        'confirmed': '✔️',
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

The task has been completed. Awaiting requester confirmation.
''',
        'confirmed': f'''
{emoji} <b>Completion Confirmed!</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> Confirmed by Requester ✓

The requester has confirmed that the task was completed satisfactorily. Great job!
''',
    }

    return messages.get(notification_type, f'{emoji} Notification for ticket #{ticket.id}')


def notify_user(user, notification_type: str, ticket, extra_info: str = '',
                send_to_group: bool = True) -> dict:
    """
    Send notification to a user via Telegram AND to the group

    Args:
        user: User instance (can be None for group-only notifications)
        notification_type: Type of notification
        ticket: Ticket instance
        extra_info: Additional information
        send_to_group: Whether to also send to the group chat

    Returns:
        dict with 'individual' and 'group' success status
    """
    results = {'individual': False, 'group': False}

    message = format_ticket_notification(notification_type, ticket, extra_info)
    keyboard = create_ticket_keyboard(ticket.id, show_actions=(notification_type == 'new_request'))

    # Send to group if enabled
    if send_to_group:
        group_chat_id = getattr(settings, 'TELEGRAM_GROUP_CHAT_ID', '')
        if group_chat_id:
            results['group'] = send_telegram_message(group_chat_id, message, reply_markup=keyboard)

    # Send to individual user if they have telegram_id
    if user and user.telegram_id:
        results['individual'] = send_telegram_message(user.telegram_id, message, reply_markup=keyboard)
    elif user:
        logger.info(f'User {user.username} has no telegram_id configured')

    return results


def notify_managers(notification_type: str, ticket, extra_info: str = '') -> list:
    """
    Send notification to all managers (for new ticket requests)

    Args:
        notification_type: Type of notification
        ticket: Ticket instance
        extra_info: Additional information

    Returns:
        List of results for each manager
    """
    from api.models import User

    results = []
    managers = User.objects.filter(role__in=['manager', 'admin'], is_active=True, is_approved=True)

    # Send to group once
    send_group_notification(notification_type, ticket, extra_info)

    # Send to each manager with telegram_id
    message = format_ticket_notification(notification_type, ticket, extra_info)
    keyboard = create_ticket_keyboard(ticket.id, show_actions=True)

    for manager in managers:
        if manager.telegram_id:
            success = send_telegram_message(manager.telegram_id, message, reply_markup=keyboard)
            results.append({'user': manager.username, 'success': success})

    return results


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
# Bot: Juan365_creatives_ticketing_bot
