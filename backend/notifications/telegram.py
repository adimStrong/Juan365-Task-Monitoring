"""
Telegram notification service for the Ticketing System
Sends notifications to both group chat and individual users
"""
import requests
import logging
import json
from django.conf import settings

logger = logging.getLogger(__name__)


def format_duration(seconds):
    """Format duration in seconds to human-readable string"""
    if seconds is None or seconds < 0:
        return 'N/A'

    if seconds < 60:
        return f'{int(seconds)}s'
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f'{minutes}m {secs}s' if secs > 0 else f'{minutes}m'
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f'{hours}h {minutes}m' if minutes > 0 else f'{hours}h'


def get_ticket_summary(ticket):
    """Generate a summary of ticket processing times and output"""
    summary_lines = []

    # Processing time (started -> completed)
    if ticket.started_at and ticket.completed_at:
        processing_seconds = (ticket.completed_at - ticket.started_at).total_seconds()
        summary_lines.append(f'⏱ <b>Processing Time:</b> {format_duration(processing_seconds)}')

    # Total time (created -> completed)
    if ticket.created_at and ticket.completed_at:
        total_seconds = (ticket.completed_at - ticket.created_at).total_seconds()
        summary_lines.append(f'📅 <b>Total Time:</b> {format_duration(total_seconds)}')

    # Output quantity
    if ticket.quantity and ticket.quantity > 0:
        # For Ads/Telegram, sum up product items instead
        if ticket.request_type in ['ads', 'telegram_channel']:
            try:
                total_qty = sum(item.quantity for item in ticket.product_items.all())
                if total_qty > 0:
                    summary_lines.append(f'📦 <b>Output:</b> {total_qty} items')
            except:
                pass
        else:
            summary_lines.append(f'📦 <b>Output:</b> {ticket.quantity} creative(s)')

    # Criteria (Image/Video)
    if ticket.criteria:
        criteria_display = 'Video 🎬' if ticket.criteria == 'video' else 'Image 🖼'
        summary_lines.append(f'📋 <b>Type:</b> {criteria_display}')

    return chr(10).join(summary_lines) if summary_lines else ''


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


def format_ticket_notification(notification_type: str, ticket, extra_info: str = '', actor=None) -> str:
    """
    Format a ticket notification message for Telegram

    Args:
        notification_type: Type of notification
        ticket: Ticket instance
        extra_info: Additional information (e.g., rejection reason)
        actor: User who performed the action (optional)

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
        'pending_creative': '🔄',
        'overdue': '🚨',
        'started': '▶️',
        'revision_requested': '🔄',
        'collaborator_added': '👥',
        'restored': '♻️',
        'rollback': '⏪',
    }

    emoji = emojis.get(notification_type, '📌')

    # Get actor display name
    actor_name = ''
    if actor:
        actor_name = actor.get_full_name() or actor.username

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
{f"<b>Approved by:</b> {actor_name}" if actor_name else ""}

The ticket has been approved and is ready to proceed.
''',
        'pending_creative': f'''
{emoji} <b>Ticket Pending Creative Approval</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> Dept Approved → Pending Creative
{f"<b>Approved by:</b> {actor_name}" if actor_name else ""}

Waiting for Creative department to review.
''',
        'rejected': f'''
{emoji} <b>Ticket Rejected</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> Rejected
{f"<b>Rejected by:</b> {actor_name}" if actor_name else ""}
{f"<b>Reason:</b> {extra_info}" if extra_info else ""}
''',
        'assigned': f'''
{emoji} <b>Ticket Assigned</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Assigned to:</b> {ticket.assigned_to.get_full_name() if ticket.assigned_to else 'Unknown'}
{f"<b>Assigned by:</b> {actor_name}" if actor_name else ""}
<b>Priority:</b> {ticket.get_priority_display()}
<b>Deadline:</b> {ticket.deadline.strftime('%Y-%m-%d %H:%M') if ticket.deadline else 'No deadline'}
''',
        'comment': f'''
{emoji} <b>New Comment</b>

<b>#{ticket.id}</b> - {ticket.title}
{f"<b>Comment by:</b> {actor_name}" if actor_name else ""}

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
{f"<b>Completed by:</b> {actor_name}" if actor_name else ""}

{get_ticket_summary(ticket)}

Great work! The task has been completed.
''',
        'confirmed': f'''
{emoji} <b>Completion Confirmed!</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> Confirmed ✓
{f"<b>Confirmed by:</b> {actor_name}" if actor_name else ""}

The requester has confirmed that the task was completed satisfactorily. Great job!
''',
        'rollback': f'''
⏪ <b>Ticket Rolled Back</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> {ticket.get_status_display()}
{f"<b>Rolled back by:</b> {actor_name}" if actor_name else ""}

The ticket has been restored to a previous state.
''',
        'started': f'''
▶️ <b>Work Started</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> In Progress
{f"<b>Started by:</b> {actor_name}" if actor_name else ""}
<b>Priority:</b> {ticket.get_priority_display()}
<b>Deadline:</b> {ticket.deadline.strftime('%Y-%m-%d %H:%M') if ticket.deadline else 'No deadline'}

The assignee has started working on this ticket.
''',
        'revision_requested': f'''
🔄 <b>Revision Requested</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> Needs Revision
{f"<b>Requested by:</b> {actor_name}" if actor_name else ""}
{f"<b>Comments:</b> {extra_info}" if extra_info else ""}

Please review the feedback and make necessary changes.
''',
        'collaborator_added': f'''
👥 <b>Added as Collaborator</b>

<b>#{ticket.id}</b> - {ticket.title}
{f"<b>Added by:</b> {actor_name}" if actor_name else ""}
<b>Priority:</b> {ticket.get_priority_display()}
<b>Deadline:</b> {ticket.deadline.strftime('%Y-%m-%d %H:%M') if ticket.deadline else 'No deadline'}

You have been added as a collaborator on this ticket.
''',
        'restored': f'''
♻️ <b>Ticket Restored</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> {ticket.get_status_display()}
{f"<b>Restored by:</b> {actor_name}" if actor_name else ""}

This ticket has been restored from trash.
''',
    }

    # Improved fallback with more context
    fallback = f'''{emoji} <b>Ticket Update</b>

<b>#{ticket.id}</b> - {ticket.title}
<b>Status:</b> {ticket.get_status_display()}
<b>Priority:</b> {ticket.get_priority_display()}
{f"<b>Action by:</b> {actor_name}" if actor_name else ""}
'''
    return messages.get(notification_type, fallback)


def get_user_mention(user) -> str:
    """
    Get a formatted mention string for a user.
    Uses telegram_id if numeric (for chat_id mention), or username if available.

    Args:
        user: User instance

    Returns:
        Formatted mention string
    """
    if not user:
        return ''

    # If user has telegram_id and it looks like a Telegram username (not numeric)
    telegram_id = user.telegram_id
    if telegram_id:
        # Check if it's a username (starts with @ or is alphanumeric without @)
        if telegram_id.startswith('@'):
            return telegram_id
        # If it's numeric, it's a chat ID - we can use HTML mention
        try:
            int(telegram_id)
            # It's a numeric chat_id - use HTML mention format
            display_name = user.first_name or user.username
            return f'<a href="tg://user?id={telegram_id}">{display_name}</a>'
        except ValueError:
            # It's a username without @
            return f'@{telegram_id}'

    # Fallback to just the display name
    return user.first_name or user.username


def notify_user(user, notification_type: str, ticket, extra_info: str = '',
                send_to_group: bool = True, actor=None) -> dict:
    """
    Send notification to a user via Telegram AND to the group.
    Includes @mention of the user in group notifications.

    Args:
        user: User instance (can be None for group-only notifications)
        notification_type: Type of notification
        ticket: Ticket instance
        extra_info: Additional information
        send_to_group: Whether to also send to the group chat
        actor: User who performed the action (for "Approved by", "Assigned by", etc.)

    Returns:
        dict with 'individual' and 'group' success status
    """
    results = {'individual': False, 'group': False}

    message = format_ticket_notification(notification_type, ticket, extra_info, actor=actor)
    keyboard = create_ticket_keyboard(ticket.id, show_actions=(notification_type == 'new_request'))

    # Send to group if enabled
    if send_to_group:
        group_chat_id = getattr(settings, 'TELEGRAM_GROUP_CHAT_ID', '')
        if group_chat_id:
            # Add @mention to group message if user has telegram info
            group_message = message
            if user:
                mention = get_user_mention(user)
                if mention:
                    group_message = f'{mention}\n\n{message}'
            results['group'] = send_telegram_message(group_chat_id, group_message, reply_markup=keyboard)

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
