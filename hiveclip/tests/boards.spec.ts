import { test, expect } from "@playwright/test";

async function registerAndLogin(page: any) {
  const email = `board-${Date.now()}@test.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Your Boards")).toBeVisible({ timeout: 5000 });
}

test.describe("Boards", () => {
  test("shows empty state when no boards exist", async ({ page }) => {
    await registerAndLogin(page);
    await expect(page.getByText("No boards yet")).toBeVisible();
  });

  test("can create a new board", async ({ page }) => {
    await registerAndLogin(page);
    await page.getByRole("button", { name: "New Board" }).click();
    await page.getByLabel("Name").fill("My Test Board");
    await page.getByRole("button", { name: "Create Board" }).click();
    // Should navigate to board dashboard
    await expect(page.getByText("My Test Board")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("VM Controls")).toBeVisible();
  });

  test("board dashboard shows vm controls", async ({ page }) => {
    await registerAndLogin(page);
    await page.getByRole("button", { name: "New Board" }).click();
    await page.getByLabel("Name").fill("VM Board");
    await page.getByRole("button", { name: "Create Board" }).click();
    await expect(page.getByText("Provision VM")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Desktop Access")).toBeVisible();
  });
});
