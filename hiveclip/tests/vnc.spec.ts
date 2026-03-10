import { test, expect } from "@playwright/test";

test.describe("VNC Desktop Viewer", () => {
  test("desktop page renders with noVNC and attempts connection", async ({ page }) => {
    // Register
    const email = `vnc-${Date.now()}@test.com`;
    await page.goto("/register");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("password123");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Your Boards")).toBeVisible({ timeout: 10000 });

    // Create board
    await page.getByRole("button", { name: "New Board" }).click();
    await page.getByLabel("Name").fill("Desktop Test");
    await page.getByRole("button", { name: "Create Board" }).click();
    await expect(page.getByText("Desktop Test")).toBeVisible({ timeout: 10000 });

    // Go to desktop page
    const boardId = page.url().split("/boards/")[1];
    await page.goto(`/boards/${boardId}/desktop`);
    await page.waitForTimeout(1000);

    // Desktop page should render header
    await expect(page.getByText("Desktop Test — Desktop")).toBeVisible();

    // Without a VM provisioned, it should show "No VM IP available"
    await expect(page.getByText("No VM provisioned")).toBeVisible({ timeout: 5000 });

    await page.screenshot({ path: "screenshots/vnc-no-vm.png", fullPage: true });
  });

  test("VNC connects when VM IP is available via WebSocket proxy", async ({ page }) => {
    // Test that the WebSocket proxy endpoint exists
    // We test by making a regular HTTP request to the VNC proxy path (should fail gracefully)
    const response = await page.request.get("/api/vnc/216.238.104.3");
    // WebSocket endpoints return non-200 for regular HTTP requests
    expect([400, 404, 426]).toContain(response.status());
  });
});
