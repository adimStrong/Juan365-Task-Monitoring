"""
Unified notification service
Sends notifications via both Telegram and Email
"""
import logging
from .telegram import notify_user as telegram_notify
from .email import notify_user_email, is_email_enabled

logger = logging.getLogger(__name__)


def notify_user(user, notification_type: str, ticket, extra_info: str = '',
                send_to_group: bool = True) -> dict:
    """
    Send notification to a user via all available channels (Telegram + Email)

    Args:
        user: User instance
        notification_type: Type of notification
        ticket: Ticket instance
        extra_info: Additional information
        send_to_group: Whether to send to Telegram group

    Returns:
        dict with results for each channel
    """
    results = {
        'telegram': {'individual': False, 'group': False},
        'email': False
    }

    # Send Telegram notification
    try:
        telegram_result = telegram_notify(user, notification_type, ticket, extra_info, send_to_group)
        results['telegram'] = telegram_result
    except Exception as e:
        logger.error(f'Telegram notification failed: {e}')

    # Send Email notification
    try:
        if is_email_enabled() and user and user.email:
            results['email'] = notify_user_email(user, notification_type, ticket, extra_info)
    except Exception as e:
        logger.error(f'Email notification failed: {e}')

    return results
