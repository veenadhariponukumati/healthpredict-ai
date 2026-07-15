import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:3000';
const CLINICIAN = { email: 'clinician@test.com', password: 'Test123!' };
const ADMIN = { email: 'admin@test.com', password: 'Test123!' };
const VIEWER = { email: 'viewer@test.com', password: 'Test123!' };

async function loginAs(page: any, user: { email: string; password: string }) {
  await page.goto(`${BASE}/login`);
  await page.getByLabel('Email').fill(user.email);
  await page.getByLabel('Password').fill(user.password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL('**/dashboard');
}

test.describe('Healthcare Platform E2E', () => {
  test('1. Clinician login', async ({ page }) => {
    await loginAs(page, CLINICIAN);
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  });

  test('2. Patient list', async ({ page }) => {
    await loginAs(page, CLINICIAN);
    await page.goto(`${BASE}/patients`);
    await page.waitForLoadState('networkidle');
  });

  test('3. Create patient', async ({ page }) => {
    await loginAs(page, CLINICIAN);
    await page.goto(`${BASE}/patients/new`);
    await page.waitForLoadState('networkidle');
    await page.getByLabel('MRN').fill(`E2E-${Date.now()}`);
    await page.getByLabel('First Name').fill('E2E');
    await page.getByLabel('Last Name').fill('Test');
    await page.getByLabel('Date of Birth').fill('1990-01-15');
    await page.getByRole('button', { name: /create patient|save/i }).click();
    await page.waitForURL(/\/patients\//);
  });

  test('4. Patient detail', async ({ page }) => {
    await loginAs(page, CLINICIAN);
    await page.goto(`${BASE}/patients`);
    await page.waitForLoadState('networkidle');
    const link = page.getByRole('link').filter({ hasText: /E2E|Test/i }).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForURL(/\/patients\/[^/]+$/);
    }
  });

  test('5. Create prediction', async ({ page }) => {
    await loginAs(page, CLINICIAN);
    await page.goto(`${BASE}/predictions/new`);
    await page.waitForLoadState('networkidle');
    await page.getByRole('combobox').first().selectOption({ index: 1 });
    await page.waitForTimeout(500);
  });

  test('6. Prediction detail', async ({ page }) => {
    await loginAs(page, CLINICIAN);
    await page.goto(`${BASE}/predictions`);
    await page.waitForLoadState('networkidle');
    const link = page.getByRole('link').filter({ hasText: /high|moderate|low/i }).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForURL(/\/predictions\/[^/]+$/);
    }
  });

  test('7. Workflow list', async ({ page }) => {
    await loginAs(page, CLINICIAN);
    await page.goto(`${BASE}/workflows`);
    await page.waitForLoadState('networkidle');
  });

  test('8. Workflow detail', async ({ page }) => {
    await loginAs(page, CLINICIAN);
    await page.goto(`${BASE}/workflows`);
    await page.waitForLoadState('networkidle');
    const link = page.getByRole('link').filter({ hasText: /running|completed|failed|pending/i }).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForURL(/\/workflows\/[^/]+$/);
    }
  });

  test('9. Administrator audit page', async ({ page }) => {
    await loginAs(page, ADMIN);
    await page.goto(`${BASE}/audit`);
    await page.waitForLoadState('networkidle');
  });

  test('10. Viewer write-action denial', async ({ page }) => {
    await loginAs(page, VIEWER);
    await page.goto(`${BASE}/patients/new`);
    await page.waitForLoadState('networkidle');
    await expect(page.getByText(/access denied|unauthorized|404/i).first()).toBeVisible();
  });

  test('11. Logout', async ({ page }) => {
    await loginAs(page, CLINICIAN);
    await page.goto(`${BASE}/profile`);
    await page.waitForLoadState('networkidle');
    const logoutBtn = page.getByRole('button', { name: /sign out/i });
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click();
      await page.waitForURL('**/login');
    }
  });
});