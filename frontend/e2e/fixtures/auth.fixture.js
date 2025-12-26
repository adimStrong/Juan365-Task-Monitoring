/**
 * Shared Authentication Fixture for E2E Tests
 * Provides consistent login helper and test credentials
 */
import { expect } from '@playwright/test';

// Test credentials - admin user always exists
export const ADMIN_USER = { username: 'admin', password: 'admin123' };

/**
 * Login helper with robust waits and error handling
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} username - Username to login with
 * @param {string} password - Password to login with
 * @param {Object} options - Optional settings
 * @param {number} options.timeout - Timeout for navigation (default: 30000)
 */
export async function login(page, username = ADMIN_USER.username, password = ADMIN_USER.password, options = {}) {
  const timeout = options.timeout || 30000;

  // Navigate to login page with network idle wait
  await page.goto('/login', { waitUntil: 'networkidle', timeout });

  // Wait for login form to be visible
  await expect(page.locator('form')).toBeVisible({ timeout: 10000 });

  // Fill credentials using data-testid or fallback selectors
  const usernameInput = page.locator('[data-testid="input-username"], input[name="username"], input[placeholder*="username" i]');
  const passwordInput = page.locator('[data-testid="input-password"], input[type="password"]');

  await usernameInput.fill(username);
  await passwordInput.fill(password);

  // Submit form
  const loginBtn = page.locator('[data-testid="btn-login"], button:has-text("Sign in")');
  await loginBtn.click();

  // Wait for navigation away from login page
  await page.waitForURL(/^(?!.*\/login).*$/, { timeout });

  // Wait for dashboard to fully load
  await page.waitForLoadState('networkidle');

  // Verify login succeeded by checking for welcome message
  await expect(page.getByRole('heading', { name: /Welcome back/i })).toBeVisible({ timeout: 20000 });
}

/**
 * Logout helper
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function logout(page) {
  const logoutBtn = page.locator('[data-testid="btn-logout"], button:has-text("Logout")');
  await expect(logoutBtn).toBeVisible({ timeout: 5000 });
  await logoutBtn.click();
  await page.waitForURL(/\/login/, { timeout: 10000 });
}

/**
 * Check if user is logged in
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<boolean>}
 */
export async function isLoggedIn(page) {
  try {
    await page.waitForLoadState('networkidle');
    const welcomeHeading = page.getByRole('heading', { name: /Welcome back/i });
    return await welcomeHeading.isVisible({ timeout: 3000 });
  } catch {
    return false;
  }
}

/**
 * Navigate to a page and wait for it to be ready
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} path - Path to navigate to (e.g., '/tickets')
 */
export async function navigateAndWait(page, path) {
  await page.goto(path, { waitUntil: 'networkidle' });
  await page.waitForLoadState('networkidle');
}
