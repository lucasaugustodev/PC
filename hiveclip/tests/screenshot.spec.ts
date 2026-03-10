import { test } from "@playwright/test";

test("screenshot login page", async ({ page }) => {
  await page.goto("/login");
  await page.waitForTimeout(1000);
  await page.screenshot({ path: "screenshots/login.png", fullPage: true });
});

test("screenshot board list after register", async ({ page }) => {
  const email = `ss-${Date.now()}@test.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: "screenshots/boards.png", fullPage: true });
});
