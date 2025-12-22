"""
API views for Telegram notifications
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import TelegramConnectionCode, UserNotificationPreferences
from .telegram import send_telegram_message, send_test_notification

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_connection_code(request):
    """
    Generate a new Telegram connection code for the current user.
    User must send this code to the Telegram bot to link their account.
    """
    user = request.user

    # Check if user already has Telegram linked
    if user.telegram_id:
        return Response({
            'status': 'already_connected',
            'message': 'Telegram is already connected to your account',
            'telegram_id': user.telegram_id
        })

    # Generate new code
    code_obj = TelegramConnectionCode.create_for_user(user)

    bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')

    return Response({
        'status': 'code_generated',
        'code': code_obj.code,
        'expires_in_minutes': 10,
        'bot_username': bot_username,
        'instructions': f'Send this code to our Telegram bot: @{bot_username}' if bot_username else 'Send this code to our Telegram bot'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def connection_status(request):
    """
    Check the Telegram connection status for the current user.
    """
    user = request.user

    if user.telegram_id:
        return Response({
            'connected': True,
            'telegram_id': user.telegram_id
        })

    # Check if there's a pending code
    pending_code = TelegramConnectionCode.objects.filter(
        user=user, used=False
    ).first()

    return Response({
        'connected': False,
        'pending_code': pending_code.code if pending_code and pending_code.is_valid() else None,
        'pending_expires_at': pending_code.expires_at.isoformat() if pending_code and pending_code.is_valid() else None
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disconnect_telegram(request):
    """
    Disconnect Telegram from the current user's account.
    """
    user = request.user

    if not user.telegram_id:
        return Response({
            'status': 'not_connected',
            'message': 'Telegram is not connected to your account'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Clear the telegram_id
    user.telegram_id = None
    user.save(update_fields=['telegram_id'])

    # Delete any pending codes
    TelegramConnectionCode.objects.filter(user=user).delete()

    return Response({
        'status': 'disconnected',
        'message': 'Telegram has been disconnected from your account'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_notification(request):
    """
    Send a test notification to the current user's Telegram.
    """
    user = request.user

    if not user.telegram_id:
        return Response({
            'status': 'not_connected',
            'message': 'Connect Telegram first to receive test notifications'
        }, status=status.HTTP_400_BAD_REQUEST)

    success = send_test_notification(user.telegram_id)

    if success:
        return Response({
            'status': 'sent',
            'message': 'Test notification sent successfully'
        })
    else:
        return Response({
            'status': 'failed',
            'message': 'Failed to send test notification'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(['POST'])
def telegram_webhook(request):
    """
    Webhook endpoint for Telegram bot updates.
    Handles incoming messages from users (e.g., connection codes).
    """
    try:
        data = json.loads(request.body)
        logger.debug(f'Telegram webhook received: {data}')

        # Handle message updates
        message = data.get('message', {})
        if message:
            chat_id = str(message.get('chat', {}).get('id', ''))
            text = message.get('text', '').strip().upper()
            from_user = message.get('from', {})
            username = from_user.get('username', 'Unknown')

            if text:
                # Check if it's a connection code
                code_obj = TelegramConnectionCode.objects.filter(
                    code=text
                ).first()

                if code_obj and code_obj.is_valid():
                    # Link the Telegram account
                    user = code_obj.user
                    user.telegram_id = chat_id
                    user.save(update_fields=['telegram_id'])

                    # Mark code as used
                    code_obj.mark_used()

                    # Send confirmation message
                    send_telegram_message(
                        chat_id,
                        f'<b>Account Linked!</b>\n\n'
                        f'Your Telegram is now connected to <b>{user.username}</b>.\n\n'
                        f'You will receive notifications for:\n'
                        f'• New ticket requests\n'
                        f'• Approvals & rejections\n'
                        f'• Task assignments\n'
                        f'• Comments\n'
                        f'• Deadline reminders'
                    )
                    logger.info(f'Telegram account {chat_id} linked to user {user.username}')

                elif text == '/START':
                    # Handle /start command
                    send_telegram_message(
                        chat_id,
                        '<b>Welcome to Juan365 Ticketing Bot!</b>\n\n'
                        'To link your account:\n'
                        '1. Go to your profile settings in the web app\n'
                        '2. Click "Connect Telegram"\n'
                        '3. Send the code here\n\n'
                        'Once connected, you will receive ticket notifications directly in Telegram.'
                    )

                elif text == '/STATUS':
                    # Check if this chat_id is linked to any user
                    from api.models import User
                    user = User.objects.filter(telegram_id=chat_id).first()
                    if user:
                        send_telegram_message(
                            chat_id,
                            f'<b>Connection Status</b>\n\n'
                            f'Connected to: <b>{user.username}</b>\n'
                            f'Email: {user.email}\n'
                            f'Role: {user.role.title()}'
                        )
                    else:
                        send_telegram_message(
                            chat_id,
                            '<b>Not Connected</b>\n\n'
                            'Your Telegram is not linked to any account.\n'
                            'Go to the web app settings to connect.'
                        )

                elif text == '/HELP':
                    send_telegram_message(
                        chat_id,
                        '<b>Available Commands</b>\n\n'
                        '/start - Welcome message\n'
                        '/status - Check connection status\n'
                        '/help - Show this help\n\n'
                        'To link your account, use the "Connect Telegram" '
                        'feature in the web app settings.'
                    )

                else:
                    # Unknown command or invalid code
                    send_telegram_message(
                        chat_id,
                        'I didn\'t recognize that command or code.\n\n'
                        'If you\'re trying to link your account, make sure you\'re using '
                        'the correct 6-character code from the web app.\n\n'
                        'Type /help for available commands.'
                    )

        # Handle callback queries (inline button clicks)
        callback = data.get('callback_query', {})
        if callback:
            callback_id = callback.get('id')
            callback_data = callback.get('data', '')
            chat_id = str(callback.get('message', {}).get('chat', {}).get('id', ''))

            # Answer the callback to remove the loading state
            api_url = f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}'
            import requests
            requests.post(
                f'{api_url}/answerCallbackQuery',
                json={
                    'callback_query_id': callback_id,
                    'text': 'Please use the web app to perform this action.'
                }
            )

        return JsonResponse({'ok': True})

    except Exception as e:
        logger.error(f'Telegram webhook error: {e}')
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_link_telegram(request):
    """
    Admin endpoint to manually link a user's Telegram account.
    Only admins can use this endpoint.
    """
    user = request.user

    if user.role != 'admin':
        return Response({
            'error': 'Only admins can use this endpoint'
        }, status=status.HTTP_403_FORBIDDEN)

    user_id = request.data.get('user_id')
    telegram_id = request.data.get('telegram_id')

    if not user_id or not telegram_id:
        return Response({
            'error': 'user_id and telegram_id are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    from api.models import User
    try:
        target_user = User.objects.get(id=user_id)
        target_user.telegram_id = str(telegram_id)
        target_user.save(update_fields=['telegram_id'])

        return Response({
            'status': 'linked',
            'user': target_user.username,
            'telegram_id': telegram_id
        })
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def notification_preferences(request):
    """
    Get or update notification preferences for the current user.
    """
    user = request.user

    # Get or create preferences
    prefs, created = UserNotificationPreferences.objects.get_or_create(user=user)

    if request.method == 'GET':
        return Response({
            'notify_new_tickets': prefs.notify_new_tickets,
            'notify_approvals': prefs.notify_approvals,
            'notify_rejections': prefs.notify_rejections,
            'notify_assignments': prefs.notify_assignments,
            'notify_comments': prefs.notify_comments,
            'notify_completions': prefs.notify_completions,
            'notify_deadlines': prefs.notify_deadlines,
            'quiet_hours_start': prefs.quiet_hours_start.isoformat() if prefs.quiet_hours_start else None,
            'quiet_hours_end': prefs.quiet_hours_end.isoformat() if prefs.quiet_hours_end else None,
        })

    elif request.method == 'PATCH':
        # Update preferences
        allowed_fields = [
            'notify_new_tickets', 'notify_approvals', 'notify_rejections',
            'notify_assignments', 'notify_comments', 'notify_completions',
            'notify_deadlines', 'quiet_hours_start', 'quiet_hours_end'
        ]

        for field in allowed_fields:
            if field in request.data:
                setattr(prefs, field, request.data[field])

        prefs.save()

        return Response({
            'status': 'updated',
            'message': 'Notification preferences updated'
        })
