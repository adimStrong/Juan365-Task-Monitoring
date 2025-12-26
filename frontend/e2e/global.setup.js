/**
 * Global Setup for E2E Tests
 * Authenticates once and saves state for all tests
 */
import { test as setup, expect } from '@playwright/test';
import { ADMIN_USER } from './fixtures/auth.fixture.js';

const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  // Navigate to login page
  await page.goto('/login', { waitUntil: 'networkidle' });

  // Wait for form to be ready
  await expect(page.locator('form')).toBeVisible({ timeout: 15000 });

  // Fill login credentials
  const usernameInput = page.locator('[data-testid="input-username"], input[name="username"], input[placeholder*="username" i]');
  const passwordInput = page.locator('[data-testid="input-password"], input[type="password"]');

  await usernameInput.fill(ADMIN_USER.username);
  await passwordInput.fill(ADMIN_USER.password);

  // Submit
  const loginBtn = page.locator('[data-testid="btn-login"], button:has-text("Sign in")');
  await loginBtn.click();

  // Wait for redirect to dashboard
  await page.waitForURL(/^(?!.*\/login).*$/, { timeout: 30000 });
  await page.waitForLoadState('networkidle');

  // Verify logged in
  await expect(page.getByRole('heading', { name: /Welcome back/i })).toBeVisible({ timeout: 20000 });

  // Save authenticated state for reuse
  await page.context().storageState({ path: authFile });
});
