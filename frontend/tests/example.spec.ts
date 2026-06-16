import { test, expect } from '@playwright/test';

test('has title and navigates', async ({ page }) => {
  // Navigate to a website
  await page.goto('https://playwright.dev/');

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/Playwright/);
});
