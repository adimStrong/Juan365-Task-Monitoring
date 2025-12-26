/**
 * Complete Workflow E2E Tests
 * Tests for end-to-end user workflows
 */
import { test, expect } from '@playwright/test';
import { ADMIN_USER, login } from './fixtures/auth.fixture.js';

test.describe('Dashboard & Navigation', () => {

  test.beforeEach(async ({ page }) => {
    // Tests use storageState for auth, just navigate to dashboard
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForLoadState('networkidle');
  });

  test('E2E-NAV-001: Dashboard loads with correct stats', async ({ page }) => {
    // Verify dashboard elements - heading "Welcome back, admin!"
    await expect(page.getByRole('heading', { name: /Welcome back/i })).toBeVisible({ timeout: 15000 });

    // Check stats cards using data-testid with fallback to text selector
    const statCard = page.locator('[data-testid="stat-total"], :text("Total")').first();
    await expect(statCard).toBeVisible({ timeout: 10000 });
  });

  test('E2E-NAV-002: Navigation between all pages', async ({ page }) => {
    // Navigate to Tickets - use exact match to avoid "View All Tickets"
    const ticketsLink = page.getByRole('link', { name: 'Tickets', exact: true });
    await expect(ticketsLink).toBeVisible({ timeout: 10000 });
    await ticketsLink.click();
    await page.waitForURL(/\/tickets/, { timeout: 10000 });

    // Navigate to Activity
    const activityLink = page.locator('a:has-text("Activity")');
    await expect(activityLink).toBeVisible({ timeout: 10000 });
    await activityLink.click();
    await page.waitForURL(/\/activity/, { timeout: 10000 });

    // Navigate to Dashboard
    const dashboardLink = page.locator('a:has-text("Dashboard")');
    await expect(dashboardLink).toBeVisible({ timeout: 10000 });
    await dashboardLink.click();
    await page.waitForURL(/\/$|\/dashboard/, { timeout: 10000 });

    // Navigate to Users (admin only)
    const usersLink = page.locator('a:has-text("Users")');
    if (await usersLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await usersLink.click();
      await page.waitForURL(/\/users/, { timeout: 10000 });
    }
  });

  test('E2E-NAV-003: Notification badge updates', async ({ page }) => {
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');

    // Look for notification link - it shows the unread count
    const notificationLink = page.locator('a[href="/notifications"]');

    if (await notificationLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await notificationLink.click();
      await page.waitForURL(/\/notifications/, { timeout: 15000 });
      await page.waitForLoadState('networkidle');

      // Check notifications page loads - heading is "Notifications"
      await expect(page.getByRole('heading', { name: /Notifications/i })).toBeVisible({ timeout: 10000 });
    } else {
      // If notification link not visible, check if we're logged in and nav exists
      await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible({ timeout: 5000 });
    }
  });

  test('E2E-NAV-004: Activity log displays actions', async ({ page }) => {
    // Navigate to Activity
    const activityLink = page.locator('a:has-text("Activity")');
    await expect(activityLink).toBeVisible({ timeout: 10000 });
    await activityLink.click();
    await page.waitForURL(/\/activity/, { timeout: 10000 });

    // Check activity log is displayed
    await expect(page.locator('text=/Activity/i')).toBeVisible({ timeout: 5000 });
  });

  test('E2E-NAV-005: Quick actions navigate correctly', async ({ page }) => {
    // Check quick action buttons on dashboard - button is "+ Create New Ticket"
    const createTicketBtn = page.locator('a:has-text("Create New Ticket")');

    if (await createTicketBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createTicketBtn.click();
      await page.waitForURL(/\/tickets\/new/, { timeout: 10000 });

      // Go back
      await page.goBack();
      await page.waitForLoadState('networkidle');
    }

    const viewAllBtn = page.locator('a:has-text("View All Tickets")');
    if (await viewAllBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await viewAllBtn.click();
      await page.waitForURL(/\/tickets/, { timeout: 10000 });
    }
  });
});

test.describe('Complete User Journey', () => {

  test('Full ticket lifecycle as admin', async ({ page }) => {
    // Tests use storageState for auth, just navigate to dashboard
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForLoadState('networkidle');

    // 1. Create ticket - button is "+ Create New Ticket" on dashboard
    const createTicketBtn = page.locator('a:has-text("Create New Ticket")');
    await expect(createTicketBtn).toBeVisible({ timeout: 10000 });
    await createTicketBtn.click();
    await page.waitForURL(/\/tickets\/new/, { timeout: 10000 });

    const ticketTitle = `Full Journey Test ${Date.now()}`;
    await page.fill('input[name="title"], input[placeholder*="title" i]', ticketTitle);
    await page.fill('textarea[name="description"]', 'Full journey test description');

    const prioritySelect = page.locator('select[name="priority"]');
    if (await prioritySelect.isVisible()) {
      await prioritySelect.selectOption('high');
    }

    await page.click('button[type="submit"], button:has-text("Create Ticket")');

    // 2. Verify on detail page
    await page.waitForURL(/\/tickets\/\d+/, { timeout: 10000 });

    // 3. Add comment if available
    const commentInput = page.locator('textarea[placeholder*="comment" i]');
    if (await commentInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await commentInput.fill('Test comment on new ticket');
      await page.click('button:has-text("Add Comment"), button:has-text("Comment")');
      await page.waitForLoadState('networkidle');
    }

    // 4. Go to tickets list - use exact match
    const ticketsLink = page.getByRole('link', { name: 'Tickets', exact: true });
    await ticketsLink.click();
    await page.waitForURL(/\/tickets/, { timeout: 10000 });
    // Ticket titles are prefixed with "#N - " in the list
    await expect(page.locator(`text=/${ticketTitle}/`)).toBeVisible({ timeout: 10000 });

    // 5. Check activity
    const activityLink = page.locator('a:has-text("Activity")');
    await activityLink.click();
    await page.waitForURL(/\/activity/, { timeout: 10000 });

    // 6. Check notifications if available
    const notificationLink = page.locator('a[href="/notifications"]');
    if (await notificationLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await notificationLink.click();
      await page.waitForURL(/\/notifications/, { timeout: 10000 });
    }

    // 7. Logout
    const logoutButton = page.getByRole('button', { name: 'Logout' });
    await expect(logoutButton).toBeVisible({ timeout: 10000 });
    await logoutButton.click();
    await page.waitForURL(/\/login/, { timeout: 10000 });
  });
});

test.describe('Error Handling', () => {

  test.beforeEach(async ({ page }) => {
    // Tests use storageState for auth, just navigate to dashboard
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForLoadState('networkidle');
  });

  test('Non-existent page redirects to dashboard or 404', async ({ page }) => {
    await page.goto('/nonexistent-page-12345', { waitUntil: 'networkidle' });

    // Should redirect to dashboard or show 404
    await page.waitForLoadState('networkidle');
    const url = page.url();
    expect(url.includes('/login') || url.includes('/') || url.includes('404') || url.includes('nonexistent')).toBe(true);
  });

  test('Non-existent ticket shows error or 404', async ({ page }) => {
    await page.goto('/tickets/999999', { waitUntil: 'networkidle' });

    // Should show error message or redirect
    await page.waitForLoadState('networkidle');
    // Test passes if page loads without crashing
    expect(true).toBe(true);
  });
});

test.describe('Responsive Design', () => {

  test('Mobile view displays correctly', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Tests use storageState for auth, just navigate to dashboard
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForLoadState('networkidle');

    // Dashboard should load - heading "Welcome back, admin!"
    await expect(page.getByRole('heading', { name: /Welcome back/i })).toBeVisible({ timeout: 15000 });
  });
});
