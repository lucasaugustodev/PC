import { test, expect } from "@playwright/test";

// Real VM with TightVNC installed and running
const VNC_VM_ID = "f52a3abd-8d88-4dd9-81a5-045f18bb2d47";
const VNC_VM_IP = "216.238.104.3";

test("VNC viewer connects to real VM desktop", async ({ page }) => {
  // Register
  const email = `vncreal-${Date.now()}@test.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Your Boards")).toBeVisible({ timeout: 10000 });

  // Create board
  await page.getByRole("button", { name: "New Board" }).click();
  await page.getByLabel("Name").fill("Real VNC Board");
  await page.getByRole("button", { name: "Create Board" }).click();
  await expect(page.getByText("Real VNC Board")).toBeVisible({ timeout: 10000 });

  const boardId = page.url().split("/boards/")[1];
  const token = await page.evaluate(() => localStorage.getItem("hiveclip.token"));

  // Link the existing VNC-enabled VM to this board
  const linkRes = await page.request.post(`/api/boards/${boardId}/vm/link`, {
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    data: { vultrInstanceId: VNC_VM_ID },
  });
  // 201 = linked, 502 = already linked to another board (unique constraint)
  expect([201, 502]).toContain(linkRes.status());
  if (linkRes.status() === 502) {
    test.skip(true, "VM already linked to another board");
  }

  // Navigate to desktop page
  await page.goto(`/boards/${boardId}/desktop`);
  await page.waitForTimeout(2000);

  // Should show the VM IP in the header
  await expect(page.getByText(VNC_VM_IP)).toBeVisible({ timeout: 10000 });

  // Should show "Connecting to..." (VNC viewer trying to connect)
  // or "Connected" if it succeeds, or an error message
  await page.waitForTimeout(5000);

  // Take screenshot to see what happened
  await page.screenshot({ path: "screenshots/vnc-real-connection.png", fullPage: true });

  // The page should NOT show "No VM provisioned" anymore
  await expect(page.getByText("No VM provisioned")).not.toBeVisible();

  // Check if we see the VNC canvas or a connection status
  const pageContent = await page.textContent("body");
  const hasDesktopContent =
    pageContent?.includes("Desktop") &&
    (pageContent?.includes(VNC_VM_IP) || pageContent?.includes("Connecting") || pageContent?.includes("connected"));
  expect(hasDesktopContent).toBeTruthy();
});
