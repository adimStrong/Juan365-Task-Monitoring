// @ts-check
import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Juan365 Ticketing System E2E tests
 * @see https://playwright.dev/docs/test-configuration
 */
// CI environment has slower network, use more generous settings
const isCI = !!process.env.CI;

export default defineConfig({
  testDir: './e2e',
  /* Limit parallel tests to avoid race conditions on shared backend */
  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: isCI,
  /* Retry failed tests - more retries in CI */
  retries: isCI ? 2 : 1,
  /* Use 1 worker in CI for stability, 2 locally for speed */
  workers: isCI ? 1 : 2,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list']
  ],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.BASE_URL || 'https://juan365-ticketing-frontend.vercel.app',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',

    /* Video on failure */
    video: 'on-first-retry',

    /* Action timeout for clicks, fills, etc - longer in CI */
    actionTimeout: isCI ? 30000 : 15000,

    /* Navigation timeout - longer in CI */
    navigationTimeout: isCI ? 60000 : 30000,
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    /* Test against mobile viewports. */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  /* Global timeout - longer in CI */
  timeout: isCI ? 90000 : 60000,

  /* Expect timeout - longer in CI */
  expect: {
    timeout: isCI ? 20000 : 15000
  },
});
