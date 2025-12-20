"""
Management command to get Telegram chat IDs from recent updates
"""
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Get Telegram chat IDs from recent bot updates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-test',
            type=str,
            help='Send a test message to this chat ID'
        )

    def handle(self, *args, **options):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')

        if not token:
            self.stderr.write(self.style.ERROR(
                'TELEGRAM_BOT_TOKEN not configured in settings'
            ))
            return

        api_url = f'https://api.telegram.org/bot{token}'

        if options.get('send_test'):
            self.send_test_message(api_url, options['send_test'])
            return

        self.get_updates(api_url)

    def get_updates(self, api_url):
        """Get recent updates to find chat IDs"""
        self.stdout.write('Fetching recent updates...\n')
        self.stdout.write(
            'Note: If you don\'t see your group, make sure the bot is in the group '
            'and has received at least one message.\n'
        )

        try:
            response = requests.get(
                f'{api_url}/getUpdates',
                params={'limit': 100},
                timeout=10
            )
            result = response.json()

            if not result.get('ok'):
                self.stderr.write(f'API error: {result.get("description")}')
                return

            updates = result.get('result', [])
            if not updates:
                self.stdout.write(self.style.WARNING(
                    'No recent updates found. Try:\n'
                    '1. Send a message to the bot\n'
                    '2. Send a message in the group where the bot is a member\n'
                    '3. Run this command again\n'
                ))
                return

            # Collect unique chats
            chats = {}
            for update in updates:
                message = update.get('message', {})
                chat = message.get('chat', {})
                chat_id = chat.get('id')
                if chat_id and chat_id not in chats:
                    chats[chat_id] = {
                        'type': chat.get('type'),
                        'title': chat.get('title'),
                        'username': chat.get('username'),
                        'first_name': chat.get('first_name'),
                    }

            self.stdout.write(self.style.SUCCESS(f'\nFound {len(chats)} chat(s):\n'))

            for chat_id, info in chats.items():
                chat_type = info['type']
                if chat_type in ('group', 'supergroup'):
                    name = info['title']
                    self.stdout.write(self.style.SUCCESS(
                        f'  GROUP: {name}\n'
                        f'    Chat ID: {chat_id}\n'
                        f'    Type: {chat_type}\n'
                    ))
                else:
                    name = info['first_name'] or info['username'] or 'Unknown'
                    self.stdout.write(
                        f'  PRIVATE: {name}\n'
                        f'    Chat ID: {chat_id}\n'
                    )

            self.stdout.write(
                '\nTo use a group for notifications, set the environment variable:\n'
                '  TELEGRAM_GROUP_CHAT_ID=<chat_id>\n'
            )

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {e}'))

    def send_test_message(self, api_url, chat_id):
        """Send a test message to verify the chat ID works"""
        self.stdout.write(f'Sending test message to {chat_id}...')

        try:
            response = requests.post(
                f'{api_url}/sendMessage',
                json={
                    'chat_id': chat_id,
                    'text': '<b>Test Message</b>\n\nThis is a test from Juan365 Ticketing System.',
                    'parse_mode': 'HTML'
                },
                timeout=10
            )
            result = response.json()

            if result.get('ok'):
                self.stdout.write(self.style.SUCCESS('Test message sent successfully!'))
            else:
                self.stderr.write(self.style.ERROR(
                    f'Failed to send: {result.get("description")}'
                ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {e}'))
