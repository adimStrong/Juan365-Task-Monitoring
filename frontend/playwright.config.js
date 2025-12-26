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
  /* Retry failed tests - 3 retries in CI for production URL reliability */
  retries: isCI ? 3 : 1,
  /* Use 1 worker in CI for stability, 2 locally for speed */
  workers: isCI ? 1 : 2,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
    // JUnit reporter for CI integration
    ...(isCI ? [['junit', { outputFile: 'test-results/results.xml' }]] : []),
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
    video: 'retain-on-failure',

    /* Action timeout for clicks, fills, etc - longer in CI */
    actionTimeout: isCI ? 30000 : 15000,

    /* Navigation timeout - longer in CI */
    navigationTimeout: isCI ? 60000 : 30000,
  },

  /* Configure projects for major browsers */
  projects: [
    // Auth setup - runs before tests to create authenticated state
    {
      name: 'setup',
      testMatch: /global\.setup\.js/,
    },
    // Auth tests need to start fresh (no stored state)
    {
      name: 'chromium-auth',
      testMatch: /auth\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
      },
    },
    // Other tests use persisted auth state
    {
      name: 'chromium',
      testIgnore: /auth\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      testIgnore: /auth\.spec\.js/,
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      testIgnore: /auth\.spec\.js/,
      use: {
        ...devices['Desktop Safari'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    /* Test against mobile viewports. */
    {
      name: 'Mobile Chrome',
      testIgnore: /auth\.spec\.js/,
      use: {
        ...devices['Pixel 5'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],

  /* Global timeout - longer in CI */
  timeout: isCI ? 90000 : 60000,

  /* Expect timeout - longer in CI */
  expect: {
    timeout: isCI ? 20000 : 15000
  },
});
