import { test, expect } from "@playwright/test";

test.describe("Auth flow", () => {
  test("shows login page by default", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Sign in to your account")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
  });

  test("can navigate to register page", async ({ page }) => {
    await page.goto("/login");
    await page.getByText("Register").click();
    await expect(page.getByText("Create a new account")).toBeVisible();
  });

  test("can register a new account", async ({ page }) => {
    const email = `reg-${Date.now()}@test.com`;
    await page.goto("/register");
    await page.getByLabel("Display Name").fill("Test User");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("password123");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Your Boards")).toBeVisible({ timeout: 10000 });
  });

  test("can login with registered account", async ({ page }) => {
    const email = `login-${Date.now()}@test.com`;
    // Register
    await page.goto("/register");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("password123");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Your Boards")).toBeVisible({ timeout: 10000 });

    // Logout
    await page.evaluate(() => localStorage.removeItem("hiveclip.token"));
    await page.goto("/login");

    // Login
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("password123");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText("Your Boards")).toBeVisible({ timeout: 10000 });
  });
});
