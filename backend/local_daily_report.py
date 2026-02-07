"""
Local Daily Report Script - Run on your PC to capture screenshots and send to Telegram

Usage:
    python local_daily_report.py

Requirements:
    pip install playwright requests
    playwright install chromium
"""
import asyncio
import requests
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from PIL import Image
import io

# Configuration - UPDATE THESE VALUES
FRONTEND_URL = "https://juan365-ticketing-frontend.vercel.app"
BACKEND_URL = "https://juan365-task-monitoring-production.up.railway.app"
USERNAME = "Adim"
PASSWORD = "12345678"
TELEGRAM_BOT_TOKEN = "8524912722:AAHVQSBNS0Yj7m5zrJYycNosw8WgcUvCjSU"
TELEGRAM_GROUP_CHAT_ID = "-1003405424360"


async def capture_screenshot():
    """Capture Analytics page screenshot with T+1 date filter"""
    yesterday = datetime.now().date() - timedelta(days=1)

    print(f"Starting screenshot capture for {yesterday}...")

    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)  # Set to True for headless
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=2.5  # Higher for sharper image
        )
        page = await context.new_page()

        try:
            # Login
            print(f"Navigating to {FRONTEND_URL}/login...")
            await page.goto(f"{FRONTEND_URL}/login", timeout=60000)
            await asyncio.sleep(2)

            print(f"Logging in as {USERNAME}...")
            await page.fill('input[name="username"]', USERNAME)
            await page.fill('input[name="password"]', PASSWORD)
            await page.click('button[type="submit"]')

            # Wait for login
            print("Waiting for login to complete...")
            await page.wait_for_url(lambda url: '/login' not in url, timeout=60000)
            await asyncio.sleep(3)
            print(f"Login successful! Now at: {page.url}")

            # Go to Analytics
            print("Navigating to Analytics...")
            await page.goto(f"{FRONTEND_URL}/analytics", timeout=120000)

            # Wait for page to load
            print("Waiting 30s for Analytics to load...")
            await asyncio.sleep(30)

            # Set date filter to yesterday (T+1)
            print(f"Setting date filter to {yesterday}...")
            try:
                from_input = page.locator('input[type="date"]').first
                await from_input.fill(yesterday.strftime('%Y-%m-%d'))

                to_input = page.locator('input[type="date"]').nth(1)
                await to_input.fill(yesterday.strftime('%Y-%m-%d'))

                await page.click('button:has-text("Apply Filter")')
                print("Filter applied, waiting 30s for data to load...")
                await asyncio.sleep(30)
            except Exception as e:
                print(f"Date filter error (continuing anyway): {e}")

            # Take full page screenshot and resize for Telegram
            print("Capturing screenshot...")
            await page.evaluate('window.scrollTo(0, 0)')
            await asyncio.sleep(1)
            screenshot = await page.screenshot(full_page=True)
            print("Screenshot captured!")

            # Resize image to fit Telegram limits while keeping clarity
            img = Image.open(io.BytesIO(screenshot))
            max_dimension = 4096  # Telegram max
            if img.width > max_dimension or img.height > max_dimension:
                ratio = min(max_dimension / img.width, max_dimension / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
                print(f"Resized to {new_size}")

            # Convert to high quality JPEG (better for Telegram viewing)
            output = io.BytesIO()
            img = img.convert('RGB')  # JPEG needs RGB
            img.save(output, format='JPEG', quality=95)
            return output.getvalue()

        finally:
            await browser.close()


def get_metrics_from_api():
    """Get metrics summary from backend API"""
    try:
        # Call the dry-run endpoint to get metrics text
        response = requests.get(
            f"{BACKEND_URL}/api/cron/daily-report/",
            params={"token": "", "dry_run": "true"},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            output = data.get("output", "")
            # Extract the summary text (between the first line and "Dry run complete")
            lines = output.split("\n")
            summary_lines = []
            capture = False
            for line in lines:
                if line.startswith("📊"):
                    capture = True
                if "Dry run complete" in line:
                    break
                if capture:
                    summary_lines.append(line)
            return "\n".join(summary_lines)
    except Exception as e:
        print(f"Error getting metrics: {e}")

    # Fallback summary
    yesterday = datetime.now().date() - timedelta(days=1)
    return f"📊 <b>Creative Team Daily Report</b>\n📅 {yesterday.strftime('%B %d, %Y')} (T+1)"


def send_to_telegram(screenshot_bytes, caption):
    """Send screenshot with caption to Telegram group"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    files = {'photo': ('analytics.jpg', screenshot_bytes, 'image/jpeg')}
    data = {
        'chat_id': TELEGRAM_GROUP_CHAT_ID,
        'caption': caption,
        'parse_mode': 'HTML'
    }

    print("Sending to Telegram...")
    response = requests.post(url, files=files, data=data, timeout=60)
    result = response.json()

    if result.get('ok'):
        print("Successfully sent to Telegram!")
        return True
    else:
        print(f"Telegram error: {result}")
        return False


async def main():
    print("=" * 50)
    print("LOCAL DAILY REPORT")
    print("=" * 50)

    # Get metrics summary from backend
    print("\n1. Getting metrics from backend...")
    summary = get_metrics_from_api()
    try:
        print(summary)
    except UnicodeEncodeError:
        print(summary.encode('ascii', 'replace').decode('ascii'))

    # Capture screenshot
    print("\n2. Capturing screenshot...")
    screenshot = await capture_screenshot()

    # Send to Telegram
    print("\n3. Sending to Telegram...")
    success = send_to_telegram(screenshot, summary)

    if success:
        print("\n" + "=" * 50)
        print("REPORT SENT SUCCESSFULLY!")
        print("=" * 50)
    else:
        print("\nFailed to send report")


if __name__ == "__main__":
    asyncio.run(main())
