import { test as setup, expect } from '@playwright/test';

const BASE = 'http://localhost:3000';
const CLINICIAN = { email: 'clinician@test.com', password: 'Test123!' };
const ADMIN = { email: 'admin@test.com', password: 'Test123!' };
const VIEWER = { email: 'viewer@test.com', password: 'Test123!' };

async function login(page: import('@playwright/test').Page, user: { email: string; password: string }) {
  await page.goto(`${BASE}/login`);
  await page.getByLabel('Email').fill(user.email);
  await page.getByLabel('Password').fill(user.password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL('**/dashboard');
  await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
}

// One real login per role, reused as storageState by the rest of the suite.
// This keeps meaningful auth coverage (each role's login is exercised exactly
// once here) while avoiding 11 redundant logins hitting the auth rate limit.

setup('authenticate as clinician', async ({ page }) => {
  await login(page, CLINICIAN);
  await page.context().storageState({ path: 'e2e/.auth/clinician.json' });
});

setup('authenticate as admin', async ({ page }) => {
  await login(page, ADMIN);
  await page.context().storageState({ path: 'e2e/.auth/admin.json' });
});

setup('authenticate as viewer', async ({ page }) => {
  await login(page, VIEWER);
  await page.context().storageState({ path: 'e2e/.auth/viewer.json' });
});
