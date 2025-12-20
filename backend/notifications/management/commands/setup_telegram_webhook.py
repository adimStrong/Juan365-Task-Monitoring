"""
Management command to set up Telegram webhook
"""
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Set up Telegram webhook for the bot'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='Webhook URL (e.g., https://your-domain.com/api/telegram/webhook/)'
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete existing webhook instead of setting one'
        )
        parser.add_argument(
            '--info',
            action='store_true',
            help='Show current webhook info'
        )

    def handle(self, *args, **options):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')

        if not token:
            self.stderr.write(self.style.ERROR(
                'TELEGRAM_BOT_TOKEN not configured in settings'
            ))
            return

        api_url = f'https://api.telegram.org/bot{token}'

        if options['info']:
            self.show_webhook_info(api_url)
            return

        if options['delete']:
            self.delete_webhook(api_url)
            return

        webhook_url = options.get('url')
        if not webhook_url:
            self.stderr.write(self.style.ERROR(
                'Please provide --url argument with your webhook URL'
            ))
            self.stderr.write(
                'Example: python manage.py setup_telegram_webhook '
                '--url https://your-app.railway.app/api/telegram/webhook/'
            )
            return

        self.set_webhook(api_url, webhook_url)

    def show_webhook_info(self, api_url):
        """Show current webhook configuration"""
        self.stdout.write('Fetching webhook info...')

        # Get bot info
        try:
            response = requests.get(f'{api_url}/getMe', timeout=10)
            bot_info = response.json()
            if bot_info.get('ok'):
                bot = bot_info['result']
                self.stdout.write(self.style.SUCCESS(
                    f"\nBot Info:"
                    f"\n  Username: @{bot.get('username')}"
                    f"\n  Name: {bot.get('first_name')}"
                    f"\n  ID: {bot.get('id')}"
                ))
        except Exception as e:
            self.stderr.write(f'Failed to get bot info: {e}')

        # Get webhook info
        try:
            response = requests.get(f'{api_url}/getWebhookInfo', timeout=10)
            info = response.json()
            if info.get('ok'):
                webhook = info['result']
                self.stdout.write(self.style.SUCCESS(
                    f"\nWebhook Info:"
                    f"\n  URL: {webhook.get('url') or '(not set)'}"
                    f"\n  Pending updates: {webhook.get('pending_update_count', 0)}"
                    f"\n  Last error: {webhook.get('last_error_message', 'None')}"
                ))
        except Exception as e:
            self.stderr.write(f'Failed to get webhook info: {e}')

    def set_webhook(self, api_url, webhook_url):
        """Set the webhook URL"""
        self.stdout.write(f'Setting webhook to: {webhook_url}')

        try:
            response = requests.post(
                f'{api_url}/setWebhook',
                json={
                    'url': webhook_url,
                    'allowed_updates': ['message', 'callback_query']
                },
                timeout=10
            )
            result = response.json()

            if result.get('ok'):
                self.stdout.write(self.style.SUCCESS(
                    f'Webhook set successfully!'
                ))
                self.show_webhook_info(api_url)
            else:
                self.stderr.write(self.style.ERROR(
                    f'Failed to set webhook: {result.get("description")}'
                ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {e}'))

    def delete_webhook(self, api_url):
        """Delete the current webhook"""
        self.stdout.write('Deleting webhook...')

        try:
            response = requests.post(
                f'{api_url}/deleteWebhook',
                timeout=10
            )
            result = response.json()

            if result.get('ok'):
                self.stdout.write(self.style.SUCCESS('Webhook deleted successfully!'))
            else:
                self.stderr.write(self.style.ERROR(
                    f'Failed to delete webhook: {result.get("description")}'
                ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {e}'))
