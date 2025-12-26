/**
 * Authentication E2E Tests (E2E-AUTH)
 * Tests for login, registration, and logout flows
 */
import { test, expect } from '@playwright/test';
import { ADMIN_USER, login, logout } from './fixtures/auth.fixture.js';

test.describe('Authentication Flow', () => {

  test.beforeEach(async ({ page }) => {
    // Clear cookies and storage
    await page.context().clearCookies();
    await page.goto('/login', { waitUntil: 'networkidle' });
  });

  test('E2E-AUTH-001: Login with valid credentials', async ({ page }) => {
    // Fill login form using data-testid selectors
    const usernameInput = page.locator('[data-testid="input-username"], input[name="username"]');
    const passwordInput = page.locator('[data-testid="input-password"], input[type="password"]');
    const loginBtn = page.locator('[data-testid="btn-login"], button:has-text("Sign in")');

    await usernameInput.fill(ADMIN_USER.username);
    await passwordInput.fill(ADMIN_USER.password);
    await loginBtn.click();

    // Wait for redirect to dashboard (URL should not contain /login)
    await page.waitForURL(/^(?!.*\/login).*$/, { timeout: 20000 });

    // Verify on dashboard - heading "Welcome back, admin!"
    await expect(page.getByRole('heading', { name: /Welcome back/i })).toBeVisible({ timeout: 15000 });
  });

  test('E2E-AUTH-002: Login error for invalid credentials', async ({ page }) => {
    // Fill login form with invalid credentials
    const usernameInput = page.locator('[data-testid="input-username"], input[name="username"]');
    const passwordInput = page.locator('[data-testid="input-password"], input[type="password"]');
    const loginBtn = page.locator('[data-testid="btn-login"], button:has-text("Sign in")');

    await usernameInput.fill('wronguser');
    await passwordInput.fill('wrongpassword');
    await loginBtn.click();

    // Should show error message and stay on login page
    await expect(page.locator('text=/invalid|incorrect|error|failed/i').first()).toBeVisible({ timeout: 10000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('E2E-AUTH-003: Registration flow with success message', async ({ page }) => {
    // Navigate to registration page
    await page.click('text=Create account');
    await expect(page).toHaveURL(/\/register/);

    // Generate unique username
    const uniqueUsername = `testuser_${Date.now()}`;

    // Fill registration form
    await page.fill('input[name="first_name"], input[placeholder*="first" i]', 'Test');
    await page.fill('input[name="last_name"], input[placeholder*="last" i]', 'User');
    await page.fill('input[name="username"]', uniqueUsername);
    await page.fill('input[name="email"], input[type="email"]', `${uniqueUsername}@test.com`);
    await page.fill('input[name="password"]', 'TestPass123!');
    await page.fill('input[name="password_confirm"], input[placeholder*="confirm" i]', 'TestPass123!');

    // Submit registration
    await page.click('button:has-text("Create"), button[type="submit"]');

    // Should show success message about admin approval
    await expect(page.locator('text=/success|created|approval/i').first()).toBeVisible({ timeout: 5000 });
  });

  test('E2E-AUTH-004: Registration validation - password mismatch', async ({ page }) => {
    // Navigate to registration page
    await page.click('text=Create account');

    // Fill form with mismatched passwords
    await page.fill('input[name="first_name"], input[placeholder*="first" i]', 'Test');
    await page.fill('input[name="last_name"], input[placeholder*="last" i]', 'User');
    await page.fill('input[name="username"]', `testuser_${Date.now()}`);
    await page.fill('input[name="email"], input[type="email"]', 'test@test.com');
    await page.fill('input[name="password"]', 'TestPass123!');
    await page.fill('input[name="password_confirm"], input[placeholder*="confirm" i]', 'DifferentPass!');

    // Submit registration
    await page.click('button:has-text("Create"), button[type="submit"]');

    // Should show password mismatch error
    await expect(page.locator('text=/match|mismatch/i')).toBeVisible({ timeout: 5000 });
  });

  test('E2E-AUTH-005: Logout clears session and redirects', async ({ page }) => {
    // First login
    await login(page, ADMIN_USER.username, ADMIN_USER.password);

    // Verify we're logged in
    await expect(page.getByRole('button', { name: 'Logout' })).toBeVisible();

    // Click logout
    await page.getByRole('button', { name: 'Logout' }).click();

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 });

    // Try to access protected route
    await page.goto('/tickets');

    // Should redirect back to login
    await expect(page).toHaveURL(/\/login/);
  });

  test('E2E-AUTH-006: Protected route redirects unauthenticated users', async ({ page }) => {
    // Try to access protected routes without auth
    const protectedRoutes = ['/', '/tickets', '/notifications', '/activity'];

    for (const route of protectedRoutes) {
      await page.goto(route);
      await page.waitForURL(/\/login/, { timeout: 5000 });
      await expect(page).toHaveURL(/\/login/);
    }
  });
});

test.describe('Authenticated Session', () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await login(page, ADMIN_USER.username, ADMIN_USER.password);
  });

  test('User info displayed in header', async ({ page }) => {
    // Check user name is displayed
    await expect(page.getByText('admin').first()).toBeVisible();
  });

  test('Navigation shows correct menu items', async ({ page }) => {
    // Check navigation links - use exact: true to avoid ambiguity
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Tickets', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Activity' })).toBeVisible();
  });
});
