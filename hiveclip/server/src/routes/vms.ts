import { Router } from "express";
import { eq } from "drizzle-orm";
import { requireAuth } from "../middleware/auth.js";
import { notFound } from "../middleware/error-handler.js";
import { vms } from "@hiveclip/db";
import { VultrClient } from "@hiveclip/vultr";
import type { Db } from "../app.js";
import type { Provisioner } from "../provisioner.js";

const VULTR_API_KEY = process.env.VULTR_API_KEY || "";
const WINDOWS_OS_ID = 501; // Windows 2022 Standard x64
const DEFAULT_REGION = "sao"; // São Paulo
const WINDOWS_PLAN = "vc2-2c-4gb"; // 2 vCPUs, 4GB RAM, $20/mo
const STARTUP_SCRIPT_ID = "d2f602f1-11fa-4cf2-bc4f-e90998926898"; // Installs TightVNC + WinRM

const vultr = new VultrClient(VULTR_API_KEY);

export function createVmsRouter(db: Db, provisioner: Provisioner) {
  const router = Router();

  router.get("/boards/:boardId/vm", requireAuth, async (req, res) => {
    const [vm] = await db.select().from(vms).where(eq(vms.boardId, req.params.boardId)).limit(1);
    if (!vm) {
      res.status(404).json({ error: "No VM provisioned yet" });
      return;
    }
    // Refresh status from Vultr if we have an instance ID
    if (vm.vultrInstanceId) {
      try {
        const instance = await vultr.getInstance(vm.vultrInstanceId);
        await db.update(vms).set({
          ipAddress: instance.main_ip !== "0.0.0.0" ? instance.main_ip : vm.ipAddress,
          vultrStatus: instance.status,
          powerStatus: instance.power_status,
          serverStatus: instance.server_status,
          updatedAt: new Date(),
        }).where(eq(vms.id, vm.id));
        vm.ipAddress = instance.main_ip !== "0.0.0.0" ? instance.main_ip : vm.ipAddress;
        vm.vultrStatus = instance.status;
        vm.powerStatus = instance.power_status;
        vm.serverStatus = instance.server_status;
      } catch { /* use cached data */ }
    }
    res.json(vm);
  });

  router.post("/boards/:boardId/vm/provision", requireAuth, async (req, res) => {
    const { boardId } = req.params;
    const existing = await db.select().from(vms).where(eq(vms.boardId, boardId)).limit(1);
    if (existing.length > 0) {
      res.status(409).json({ error: "VM already provisioned for this board" });
      return;
    }

    try {
      const instance = await vultr.createInstance({
        label: `hiveclip-${boardId.slice(0, 8)}`,
        region: DEFAULT_REGION,
        plan: WINDOWS_PLAN,
        os_id: WINDOWS_OS_ID,
        hostname: `hc-${boardId.slice(0, 8)}`,
        script_id: STARTUP_SCRIPT_ID,
      });

      const [vm] = await db.insert(vms).values({
        boardId,
        vultrInstanceId: instance.id,
        region: DEFAULT_REGION,
        plan: WINDOWS_PLAN,
        os: "Windows 2022 Standard",
        hostname: instance.label,
        adminPassword: instance.default_password,
        vultrStatus: instance.status,
        powerStatus: instance.power_status,
        serverStatus: instance.server_status,
      }).returning();

      // Start background provisioning (waits for boot, installs VNC, etc.)
      provisioner.enqueue({
        vmId: vm.id,
        boardId,
        vultrInstanceId: instance.id,
      });

      res.status(202).json({
        message: "VM provisioning started",
        vm,
      });
    } catch (err: any) {
      res.status(502).json({ error: `Provisioning failed: ${err.message}` });
    }
  });

  router.post("/boards/:boardId/vm/start", requireAuth, async (req, res) => {
    const [vm] = await db.select().from(vms).where(eq(vms.boardId, req.params.boardId)).limit(1);
    if (!vm?.vultrInstanceId) throw notFound("No VM for this board");
    try {
      await vultr.startInstance(vm.vultrInstanceId);
      res.json({ message: "VM starting" });
    } catch (err: any) {
      res.status(502).json({ error: `Start failed: ${err.message}` });
    }
  });

  router.post("/boards/:boardId/vm/stop", requireAuth, async (req, res) => {
    const [vm] = await db.select().from(vms).where(eq(vms.boardId, req.params.boardId)).limit(1);
    if (!vm?.vultrInstanceId) throw notFound("No VM for this board");
    try {
      await vultr.stopInstance(vm.vultrInstanceId);
      res.json({ message: "VM stopping" });
    } catch (err: any) {
      res.status(502).json({ error: `Stop failed: ${err.message}` });
    }
  });

  router.post("/boards/:boardId/vm/reboot", requireAuth, async (req, res) => {
    const [vm] = await db.select().from(vms).where(eq(vms.boardId, req.params.boardId)).limit(1);
    if (!vm?.vultrInstanceId) throw notFound("No VM for this board");
    try {
      await vultr.rebootInstance(vm.vultrInstanceId);
      res.json({ message: "VM rebooting" });
    } catch (err: any) {
      res.status(502).json({ error: `Reboot failed: ${err.message}` });
    }
  });

  router.delete("/boards/:boardId/vm", requireAuth, async (req, res) => {
    const [vm] = await db.select().from(vms).where(eq(vms.boardId, req.params.boardId)).limit(1);
    if (!vm?.vultrInstanceId) throw notFound("No VM for this board");
    try {
      await vultr.deleteInstance(vm.vultrInstanceId);
      await db.delete(vms).where(eq(vms.id, vm.id));
      res.status(204).end();
    } catch (err: any) {
      res.status(502).json({ error: `Delete failed: ${err.message}` });
    }
  });

  // Re-trigger provisioning (install VNC) on an existing VM
  router.post("/boards/:boardId/vm/reprovision", requireAuth, async (req, res) => {
    const [vm] = await db.select().from(vms).where(eq(vms.boardId, req.params.boardId as string)).limit(1);
    if (!vm?.vultrInstanceId) {
      res.status(404).json({ error: "No VM for this board" });
      return;
    }
    provisioner.enqueue({
      vmId: vm.id,
      boardId: req.params.boardId as string,
      vultrInstanceId: vm.vultrInstanceId,
    });
    res.json({ message: "Re-provisioning started", vmId: vm.id });
  });

  // Dev-only: mark VM as VNC-ready (for VMs where VNC was installed manually)
  router.post("/boards/:boardId/vm/mark-ready", requireAuth, async (req, res) => {
    const [vm] = await db.select().from(vms).where(eq(vms.boardId, req.params.boardId as string)).limit(1);
    if (!vm) {
      res.status(404).json({ error: "No VM for this board" });
      return;
    }
    await db.update(vms).set({
      provisioningStep: "ready",
      provisioningProgress: 12,
      vncHealthy: true,
      vncPort: 5900,
      updatedAt: new Date(),
    }).where(eq(vms.id, vm.id));
    const { boards } = await import("@hiveclip/db");
    await db.update(boards).set({ status: "running", updatedAt: new Date() }).where(eq(boards.id, req.params.boardId as string));
    res.json({ message: "VM marked as ready" });
  });

  // Dev-only: link an existing Vultr VM to a board
  router.post("/boards/:boardId/vm/link", requireAuth, async (req, res) => {
    const { boardId } = req.params;
    const { vultrInstanceId } = req.body;
    if (!vultrInstanceId) {
      res.status(400).json({ error: "vultrInstanceId required" });
      return;
    }
    try {
      const instance = await vultr.getInstance(vultrInstanceId);
      const [vm] = await db.insert(vms).values({
        boardId,
        vultrInstanceId: instance.id,
        region: instance.region,
        plan: instance.plan,
        os: instance.os,
        hostname: instance.label,
        ipAddress: instance.main_ip !== "0.0.0.0" ? instance.main_ip : null,
        adminPassword: instance.default_password,
        vultrStatus: instance.status,
        powerStatus: instance.power_status,
        serverStatus: instance.server_status,
      }).returning();
      res.status(201).json(vm);
    } catch (err: any) {
      res.status(502).json({ error: `Link failed: ${err.message}` });
    }
  });

  return router;
}
