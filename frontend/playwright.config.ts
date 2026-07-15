import { defineConfig, devices } from '@playwright/test';

// Login-heavy suite against a rate-limited auth endpoint (10/minute) — run
// serially (workers: 1) so tests don't compete for that budget, and reuse
// authenticated storageState (see auth.setup.ts) instead of logging in from
// scratch in every test.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: 'http://localhost:3000',
  },
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
  ],
});
