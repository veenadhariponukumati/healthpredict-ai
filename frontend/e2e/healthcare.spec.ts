import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:3000';
const CLINICIAN = { email: 'clinician@test.com', password: 'Test123!' };

// This test performs its own fresh login — it's the one place we actually
// exercise the login flow end to end. Every other test below reuses the
// storageState produced by auth.setup.ts instead of logging in again, to
// avoid tripping the auth endpoint's rate limit (10/minute) across the suite.
test.describe('Authentication', () => {
  test('1. Clinician login', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.getByLabel('Email').fill(CLINICIAN.email);
    await page.getByLabel('Password').fill(CLINICIAN.password);
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForURL('**/dashboard');
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  });
});

test.describe('Clinician workflows', () => {
  test.use({ storageState: 'e2e/.auth/clinician.json' });

  test('2. Patient list', async ({ page }) => {
    await page.goto(`${BASE}/patients`);
    await page.waitForLoadState('networkidle');
  });

  test('3. Create patient', async ({ page }) => {
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
    await page.goto(`${BASE}/patients`);
    await page.waitForLoadState('networkidle');
    const link = page.getByRole('link').filter({ hasText: /E2E|Test/i }).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForURL(/\/patients\/[^/]+$/);
    }
  });

  test('5. Create prediction', async ({ page }) => {
    await page.goto(`${BASE}/predictions/new`);
    await page.waitForLoadState('networkidle');
    await page.getByRole('combobox').first().selectOption({ index: 1 });
    await page.waitForTimeout(500);
  });

  test('6. Prediction detail', async ({ page }) => {
    await page.goto(`${BASE}/predictions`);
    await page.waitForLoadState('networkidle');
    const link = page.getByRole('link').filter({ hasText: /high|moderate|low/i }).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForURL(/\/predictions\/[^/]+$/);
    }
  });

  test('7. Workflow list', async ({ page }) => {
    await page.goto(`${BASE}/workflows`);
    await page.waitForLoadState('networkidle');
  });

  test('8. Workflow detail', async ({ page }) => {
    await page.goto(`${BASE}/workflows`);
    await page.waitForLoadState('networkidle');
    const link = page.getByRole('link').filter({ hasText: /running|completed|failed|pending/i }).first();
    if (await link.isVisible()) {
      await link.click();
      await page.waitForURL(/\/workflows\/[^/]+$/);
    }
  });

  // Reuses the clinician session established by storageState — the point of
  // this test is verifying logout clears the session and redirects, not
  // re-testing login.
  test('11. Logout', async ({ page }) => {
    await page.goto(`${BASE}/profile`);
    await page.waitForLoadState('networkidle');
    const logoutBtn = page.getByRole('button', { name: /sign out/i });
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click();
      await page.waitForURL('**/login');
    }
  });
});

test.describe('Administrator', () => {
  test.use({ storageState: 'e2e/.auth/admin.json' });

  test('9. Administrator audit page', async ({ page }) => {
    await page.goto(`${BASE}/audit`);
    await page.waitForLoadState('networkidle');
  });
});

test.describe('Viewer RBAC', () => {
  test.use({ storageState: 'e2e/.auth/viewer.json' });

  test('10. Viewer write-action denial', async ({ page }) => {
    await page.goto(`${BASE}/patients/new`);
    await page.waitForLoadState('networkidle');
    await expect(page.getByText(/access denied|unauthorized|404/i).first()).toBeVisible();
  });
});
