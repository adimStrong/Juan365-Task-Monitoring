"""
Daily Report Command - Sends T+1 dashboard screenshots with summary to Telegram

Captures screenshots of Dashboard and Analytics pages and sends them to the
configured Telegram group with a comparison summary of yesterday vs month average.

Run manually:
    python manage.py send_daily_report

For production, configure external cron (e.g., UptimeRobot) to call:
    GET /api/cron/daily-report/?token=<CRON_SECRET_TOKEN>
    Schedule: 8:00 AM Manila (00:00 UTC)
"""
import asyncio
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send daily report with dashboard screenshots to Telegram'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Calculate metrics and print summary without sending to Telegram',
        )
        parser.add_argument(
            '--skip-screenshots',
            action='store_true',
            help='Send only text summary without screenshots',
        )
        parser.add_argument(
            '--test-browser',
            action='store_true',
            help='Test if browser can launch without capturing or sending anything',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting daily report generation...')

        # Test browser mode - just check if browser can launch
        if options.get('test_browser', False):
            self.stdout.write('Testing browser launch only...')
            try:
                asyncio.run(self.test_browser_launch())
                self.stdout.write(self.style.SUCCESS('Browser test PASSED!'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Browser test FAILED: {e}'))
            return

        dry_run = options.get('dry_run', False)
        skip_screenshots = options.get('skip_screenshots', False)

        # Calculate dates (T+1: report for yesterday)
        yesterday = timezone.now().date() - timedelta(days=1)
        month_start = yesterday.replace(day=1)

        # Calculate metrics
        metrics = self.calculate_metrics(yesterday, month_start)

        # Generate summary text
        summary = self.format_summary(metrics, yesterday)
        # Handle Windows console encoding issues with emojis
        try:
            self.stdout.write(summary)
        except UnicodeEncodeError:
            self.stdout.write(summary.encode('ascii', 'replace').decode('ascii'))

        if dry_run:
            self.stdout.write(self.style.SUCCESS('Dry run complete. No messages sent.'))
            return

        # Check configuration
        group_chat_id = getattr(settings, 'TELEGRAM_GROUP_CHAT_ID', '')
        if not group_chat_id:
            self.stdout.write(self.style.ERROR('TELEGRAM_GROUP_CHAT_ID not configured'))
            return

        # Capture screenshots
        screenshots = []
        if not skip_screenshots:
            try:
                screenshots = asyncio.run(self.capture_screenshots())
                self.stdout.write(f'Captured {len(screenshots)} screenshots')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Screenshot capture failed: {e}'))
                self.stdout.write('Continuing with text-only report...')

        # Send to Telegram
        self.send_report(group_chat_id, summary, screenshots)
        self.stdout.write(self.style.SUCCESS('Daily report sent successfully!'))

    def calculate_metrics(self, yesterday, month_start):
        """Calculate ticket metrics for yesterday and month-to-date"""
        from api.models import Ticket

        # Yesterday's stats
        yesterday_created = Ticket.objects.filter(
            created_at__date=yesterday,
            is_deleted=False
        ).count()

        yesterday_completed = Ticket.objects.filter(
            completed_at__date=yesterday,
            is_deleted=False
        ).count()

        # Month-to-date stats
        days_in_period = (yesterday - month_start).days + 1

        month_created = Ticket.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=yesterday,
            is_deleted=False
        ).count()

        month_completed = Ticket.objects.filter(
            completed_at__date__gte=month_start,
            completed_at__date__lte=yesterday,
            is_deleted=False
        ).count()

        # Averages
        avg_created = round(month_created / days_in_period, 1) if days_in_period > 0 else 0
        avg_completed = round(month_completed / days_in_period, 1) if days_in_period > 0 else 0

        # Current status counts
        status_counts = {}
        for status in ['requested', 'pending_creative', 'approved', 'in_progress', 'completed', 'rejected']:
            status_counts[status] = Ticket.objects.filter(
                status=status,
                is_deleted=False
            ).count()

        # Overdue count
        overdue_count = Ticket.objects.filter(
            deadline__lt=timezone.now(),
            status__in=['approved', 'in_progress'],
            is_deleted=False
        ).count()

        return {
            'yesterday_created': yesterday_created,
            'yesterday_completed': yesterday_completed,
            'month_avg_created': avg_created,
            'month_avg_completed': avg_completed,
            'month_total_created': month_created,
            'month_total_completed': month_completed,
            'days_in_period': days_in_period,
            'status_counts': status_counts,
            'overdue_count': overdue_count,
        }

    def format_summary(self, metrics, yesterday):
        """Format the daily report summary text with T+1 vs month comparison"""
        sc = metrics['status_counts']

        # Yesterday's activity
        y_created = metrics['yesterday_created']
        y_completed = metrics['yesterday_completed']

        # Month averages
        avg_created = metrics['month_avg_created']
        avg_completed = metrics['month_avg_completed']

        # Month totals
        m_created = metrics['month_total_created']
        m_completed = metrics['month_total_completed']
        days = metrics['days_in_period']

        # Calculate percentage change vs month average
        def pct_change(today, avg):
            if avg == 0:
                return "+100%" if today > 0 else "0%"
            change = ((today - avg) / avg) * 100
            sign = "+" if change >= 0 else ""
            return f"{sign}{change:.0f}%"

        # Trend arrows
        def trend(today, avg):
            if today > avg:
                return "↑"
            elif today < avg:
                return "↓"
            return "→"

        # Current queue status
        pending_approval = sc.get('requested', 0) + sc.get('pending_creative', 0)
        in_queue = sc.get('approved', 0)
        in_progress = sc.get('in_progress', 0)
        overdue = metrics['overdue_count']

        # Completion rate
        completion_rate = round((m_completed / m_created * 100), 0) if m_created > 0 else 0

        return f"""📊 <b>Creative Team Daily Report</b>
📅 {yesterday.strftime('%B %d, %Y')} (T+1)

<b>Yesterday's Activity:</b>
• Created: {y_created} tickets
• Completed: {y_completed} tickets

<b>vs Month Average:</b>
• Created: {y_created} vs {avg_created}/day ({pct_change(y_created, avg_created)} {trend(y_created, avg_created)})
• Completed: {y_completed} vs {avg_completed}/day ({pct_change(y_completed, avg_completed)} {trend(y_completed, avg_completed)})

<b>Month-to-Date ({days} days):</b>
• Total Created: {m_created}
• Total Completed: {m_completed}
• Completion Rate: {completion_rate:.0f}%

<b>Current Queue:</b>
• Pending Approval: {pending_approval}
• In Queue: {in_queue}
• In Progress: {in_progress}
• Overdue: {overdue}"""

    async def test_browser_launch(self):
        """Test if Playwright browser can launch successfully"""
        import subprocess
        import os
        import shutil

        self.stdout.write('=== Browser Launch Test ===')

        # Check nix store
        if os.path.exists('/nix/store'):
            entries = os.listdir('/nix/store')
            self.stdout.write(f'/nix/store has {len(entries)} entries')

            # Find glib
            glib_found = False
            chromium_found = False
            nix_lib_paths = []

            for entry in entries:
                entry_path = f'/nix/store/{entry}'

                # Check for glib
                glib_lib = f'{entry_path}/lib/libglib-2.0.so.0'
                if os.path.exists(glib_lib):
                    glib_found = True
                    self.stdout.write(f'Found libglib: {glib_lib}')

                # Check for chromium
                chromium_bin = f'{entry_path}/bin/chromium'
                if os.path.exists(chromium_bin):
                    chromium_found = True
                    self.stdout.write(f'Found chromium: {chromium_bin}')

                # Collect lib paths
                lib_path = f'{entry_path}/lib'
                if os.path.isdir(lib_path):
                    nix_lib_paths.append(lib_path)

            self.stdout.write(f'glib found: {glib_found}, chromium found: {chromium_found}')
            self.stdout.write(f'Total lib paths: {len(nix_lib_paths)}')

            # Set LD_LIBRARY_PATH
            if nix_lib_paths:
                os.environ['LD_LIBRARY_PATH'] = ':'.join(nix_lib_paths)
                self.stdout.write('LD_LIBRARY_PATH set')
        else:
            self.stdout.write('/nix/store does not exist')

        # Check PATH for chromium
        chromium_path = shutil.which('chromium') or shutil.which('chromium-browser')
        self.stdout.write(f'Chromium in PATH: {chromium_path}')

        # Install playwright
        self.stdout.write('Running playwright install...')
        result = subprocess.run(['playwright', 'install', 'chromium'], capture_output=True, text=True, env=os.environ.copy())
        self.stdout.write(f'Install result: {result.returncode}')

        # Try to launch browser
        self.stdout.write('Attempting browser launch...')
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            self.stdout.write('Browser launched successfully!')
            page = await browser.new_page()
            await page.goto('about:blank')
            self.stdout.write('Page created and navigated!')
            await browser.close()
            self.stdout.write('Browser closed successfully!')

    async def capture_screenshots(self):
        """Capture Analytics page screenshots with T+1 date filter using Playwright"""
        import subprocess
        import os

        # Debug: Check what's available on the system
        self.stdout.write('Checking system environment...')

        # Check for chromium in common locations
        chromium_locations = [
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
        ]

        # Search PATH
        import shutil
        for cmd in ['chromium', 'chromium-browser', 'google-chrome']:
            path = shutil.which(cmd)
            if path:
                chromium_locations.insert(0, path)
                self.stdout.write(f'Found {cmd} in PATH: {path}')

        # Search nix store
        if os.path.exists('/nix/store'):
            nix_entries = os.listdir('/nix/store')
            self.stdout.write(f'Found {len(nix_entries)} entries in /nix/store')

            # Find chromium and set up library paths
            nix_lib_paths = []
            for entry in nix_entries:
                entry_path = f'/nix/store/{entry}'

                # Look for chromium binary
                for bin_name in ['bin/chromium', 'bin/chromium-browser', 'bin/google-chrome-stable']:
                    chromium_bin = f'{entry_path}/{bin_name}'
                    if os.path.exists(chromium_bin):
                        chromium_locations.insert(0, chromium_bin)
                        self.stdout.write(f'Found chromium in nix: {chromium_bin}')

                # Collect library paths
                lib_path = f'{entry_path}/lib'
                if os.path.isdir(lib_path):
                    nix_lib_paths.append(lib_path)

            # Set LD_LIBRARY_PATH
            if nix_lib_paths:
                existing_ld = os.environ.get('LD_LIBRARY_PATH', '')
                new_ld = ':'.join(nix_lib_paths)
                os.environ['LD_LIBRARY_PATH'] = f'{new_ld}:{existing_ld}' if existing_ld else new_ld
                self.stdout.write(f'Set LD_LIBRARY_PATH with {len(nix_lib_paths)} paths')

        # Install Playwright browser
        self.stdout.write('Installing Playwright chromium...')
        result = subprocess.run(
            ['playwright', 'install', 'chromium'],
            capture_output=True, text=True,
            env=os.environ.copy()
        )
        self.stdout.write(f'Playwright install: {"OK" if result.returncode == 0 else result.stderr[:200]}')

        from playwright.async_api import async_playwright

        frontend_url = getattr(settings, 'FRONTEND_URL', '')
        username = getattr(settings, 'REPORT_USERNAME', '')
        password = getattr(settings, 'REPORT_PASSWORD', '')

        if not all([frontend_url, username, password]):
            raise ValueError('FRONTEND_URL, REPORT_USERNAME, or REPORT_PASSWORD not configured')

        # Calculate yesterday's date for T+1 filter
        yesterday = timezone.now().date() - timedelta(days=1)
        date_str = yesterday.strftime('%m/%d/%Y')  # Format: MM/DD/YYYY

        screenshots = []

        async with async_playwright() as p:
            # Try system chromium paths
            import shutil
            possible_paths = [
                '/usr/bin/chromium',
                '/usr/bin/chromium-browser',
                '/usr/bin/google-chrome',
            ]

            # Search in nix store for chromium
            if os.path.exists('/nix/store'):
                for entry in os.listdir('/nix/store'):
                    chromium_bin = f'/nix/store/{entry}/bin/chromium'
                    if os.path.exists(chromium_bin):
                        possible_paths.insert(0, chromium_bin)
                        break

            # Also search in PATH
            path_chromium = shutil.which('chromium') or shutil.which('chromium-browser')
            if path_chromium:
                possible_paths.insert(0, path_chromium)

            chromium_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    chromium_path = path
                    break

            if chromium_path:
                self.stdout.write(f'Using system chromium: {chromium_path}')
                browser = await p.chromium.launch(headless=True, executable_path=chromium_path, args=['--no-sandbox', '--disable-dev-shm-usage'])
            else:
                self.stdout.write('Using Playwright bundled chromium')
                browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                device_scale_factor=2  # High DPI for better quality
            )
            page = await context.new_page()

            try:
                # Login
                self.stdout.write('Logging in...')
                await page.goto(f'{frontend_url}/login', timeout=60000, wait_until='networkidle')
                await asyncio.sleep(2)  # Wait for page to stabilize

                # Fill login form
                self.stdout.write('Filling login form...')
                await page.fill('input[name="username"]', username)
                await page.fill('input[name="password"]', password)
                await page.click('button[type="submit"]')

                # Wait for redirect to dashboard (longer timeout)
                self.stdout.write('Waiting for login redirect...')
                await page.wait_for_url('**/', timeout=60000)
                await asyncio.sleep(5)  # Wait for auth to settle

                # Go to Analytics page
                self.stdout.write('Navigating to Analytics...')
                await page.goto(f'{frontend_url}/analytics', timeout=120000, wait_until='networkidle')

                # CRITICAL: Wait 60 seconds for full page load (date inputs are disabled while loading)
                self.stdout.write('Waiting 60s for Analytics to fully load...')
                await asyncio.sleep(60)

                # Set T+1 date filter (yesterday) - inputs should now be enabled
                self.stdout.write(f'Setting date filter to {date_str}...')
                try:
                    # Fill From Date (no clear needed - fill() replaces value)
                    from_input = page.locator('input[type="date"]').first
                    await from_input.fill(yesterday.strftime('%Y-%m-%d'))

                    # Fill To Date
                    to_input = page.locator('input[type="date"]').nth(1)
                    await to_input.fill(yesterday.strftime('%Y-%m-%d'))

                    # Click Apply Filter button
                    await page.click('button:has-text("Apply Filter")')
                    self.stdout.write('Filter applied, waiting 60s for data to reload...')

                    # Wait for filtered data to load
                    await asyncio.sleep(60)

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Date filter error: {e}'))

                # Take full page screenshot
                self.stdout.write('Capturing full page...')
                await page.evaluate('window.scrollTo(0, 0)')
                await asyncio.sleep(0.5)
                full_page = await page.screenshot(full_page=True)
                screenshots.append(('analytics_full', full_page))
                self.stdout.write('Full page screenshot captured')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Screenshot error: {e}'))
                raise
            finally:
                await browser.close()

        return screenshots

    def send_report(self, chat_id, summary, screenshots):
        """Send the report to Telegram"""
        from notifications.telegram import send_telegram_message, send_telegram_media_group

        if screenshots:
            # Send screenshots as media group with summary as caption
            success = send_telegram_media_group(chat_id, screenshots, caption=summary)
            if not success:
                # Fallback: send text first, then photos separately
                self.stdout.write('Media group failed, sending separately...')
                send_telegram_message(chat_id, summary)
                from notifications.telegram import send_telegram_photo
                for name, photo_bytes in screenshots:
                    send_telegram_photo(chat_id, photo_bytes)
        else:
            # Text-only report
            send_telegram_message(chat_id, summary)
