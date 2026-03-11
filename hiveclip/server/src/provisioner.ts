import { eq } from "drizzle-orm";
import { vms } from "@hiveclip/db";
import { VultrClient } from "@hiveclip/vultr";
import { execFile, spawn } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import net from "node:net";
import { fileURLToPath } from "node:url";
import type { Db } from "./app.js";

// Spawn python with env vars for credentials (avoids shell escaping issues with special chars in passwords)
function runPython(args: string[], env: Record<string, string>, timeout: number): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn("python", args, {
      env: { ...process.env, ...env },
      timeout,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d: Buffer) => { stdout += d.toString(); });
    child.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });
    child.on("close", (code) => {
      if (code === 0) resolve({ stdout, stderr });
      else reject(new Error(`Python exited with code ${code}: ${stderr.slice(0, 1000)}`));
    });
    child.on("error", reject);
  });
}

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const INSTALL_SCRIPT = path.resolve(__dirname, "../../scripts/provision-vm.py");

const POLL_INTERVAL = 15_000; // 15 seconds
const MAX_WAIT = 15 * 60_000; // 15 minutes

export interface ProvisionJob {
  vmId: string;
  boardId: string;
  vultrInstanceId: string;
}

export type Provisioner = ReturnType<typeof startProvisioningWorker>;

const activeJobs = new Map<string, NodeJS.Timeout>();

export function startProvisioningWorker(db: Db) {
  const vultr = new VultrClient(process.env.VULTR_API_KEY || "");
  async function updateVmStatus(vmId: string, step: string, progress: number, extra?: Record<string, unknown>) {
    await db.update(vms).set({
      provisioningStep: step,
      provisioningProgress: progress,
      updatedAt: new Date(),
      ...extra,
    }).where(eq(vms.id, vmId));
  }

  async function processJob(job: ProvisionJob) {
    const { vmId, boardId, vultrInstanceId } = job;
    const startTime = Date.now();

    console.log(`[Provisioner] Starting for board ${boardId.slice(0, 8)}, VM ${vultrInstanceId.slice(0, 8)}`);

    // Step 1: Wait for VM to boot
    await updateVmStatus(vmId, "wait_boot", 1);
    let instance;
    while (Date.now() - startTime < MAX_WAIT) {
      try {
        instance = await vultr.getInstance(vultrInstanceId);
        await db.update(vms).set({
          ipAddress: instance.main_ip !== "0.0.0.0" ? instance.main_ip : null,
          vultrStatus: instance.status,
          powerStatus: instance.power_status,
          serverStatus: instance.server_status,
          updatedAt: new Date(),
        }).where(eq(vms.id, vmId));

        if (instance.status === "active" && instance.server_status === "ok" && instance.main_ip !== "0.0.0.0") {
          console.log(`[Provisioner] VM ${vultrInstanceId.slice(0, 8)} is ready at ${instance.main_ip}`);
          break;
        }
      } catch (err: any) {
        console.error(`[Provisioner] Poll error:`, err.message);
      }
      await sleep(POLL_INTERVAL);
    }

    if (!instance || instance.server_status !== "ok") {
      console.error(`[Provisioner] Timeout waiting for VM ${vultrInstanceId.slice(0, 8)}`);
      await updateVmStatus(vmId, "error", 1, { vultrStatus: "timeout" });
      return;
    }

    const vmIp = instance.main_ip;
    // Use password from Vultr API, or fall back to what's stored in DB
    let vmPass = instance.default_password;
    if (!vmPass) {
      const [dbVm] = await db.select().from(vms).where(eq(vms.id, vmId)).limit(1);
      vmPass = dbVm?.adminPassword || "";
    }

    // Step 2: Wait for WinRM to be available (and VM fully configured — hostname != "guest")
    await updateVmStatus(vmId, "wait_winrm", 3);
    console.log(`[Provisioner] Waiting for WinRM on ${vmIp} (pass length: ${vmPass.length})...`);
    let winrmReady = false;
    for (let attempt = 0; attempt < 40; attempt++) {
      try {
        console.log(`[Provisioner] WinRM attempt ${attempt + 1}/40 on ${vmIp}...`);
        const { stdout } = await runPython([
          "-c",
          `import os,winrm; s=winrm.Session(os.environ['VM_IP'],auth=('Administrator',os.environ['VM_PASS']),transport='ntlm'); r=s.run_cmd('hostname'); print(r.std_out.decode().strip())`,
        ], { VM_IP: vmIp, VM_PASS: vmPass }, 60_000);
        const hostname = stdout.trim();
        if (hostname) {
          // Skip if hostname is still default "guest" — VM hasn't finished Vultr setup
          if (hostname.toLowerCase() === "guest") {
            console.log(`[Provisioner] WinRM connected but hostname is "guest" — VM still configuring, waiting...`);
            await sleep(15_000);
            continue;
          }
          console.log(`[Provisioner] WinRM ready on ${vmIp}, hostname: ${hostname}`);
          winrmReady = true;
          break;
        }
      } catch (err: any) {
        console.log(`[Provisioner] WinRM attempt ${attempt + 1} failed: ${err.message?.slice(0, 100)}`);
      }
      await sleep(15_000);
    }

    if (!winrmReady) {
      console.error(`[Provisioner] WinRM not available on ${vmIp}`);
      await updateVmStatus(vmId, "error", 3, { vultrStatus: "winrm_timeout" });
      return;
    }

    // Extra stabilization delay — Windows VMs may reboot after initial Vultr config
    console.log(`[Provisioner] Waiting 30s for VM stabilization...`);
    await sleep(30_000);

    // Step 3: Install VNC + Launcher + CLIs (all in one Python script, with retry)
    await updateVmStatus(vmId, "install_software", 6);
    console.log(`[Provisioner] Script path: ${INSTALL_SCRIPT}`);
    let installOk = false;
    for (let attempt = 1; attempt <= 3; attempt++) {
      console.log(`[Provisioner] Install attempt ${attempt}/3 on ${vmIp}...`);
      const installStart = Date.now();
      try {
        const { stdout, stderr } = await runPython([
          INSTALL_SCRIPT,
        ], { VM_IP: vmIp, VM_PASS: vmPass }, 1_200_000); // 20 min timeout for full install
        const elapsed = ((Date.now() - installStart) / 1000).toFixed(0);
        console.log(`[Provisioner] Install completed in ${elapsed}s`);
        console.log(`[Provisioner] Install output (last 800):`, stdout.slice(-800));
        if (stderr && !stderr.includes("CLIXML")) {
          console.warn(`[Provisioner] Install stderr:`, stderr.slice(-500));
        }
        installOk = true;
        break;
      } catch (err: any) {
        const elapsed = ((Date.now() - installStart) / 1000).toFixed(0);
        console.error(`[Provisioner] Install attempt ${attempt} FAILED after ${elapsed}s:`, err.message?.slice(0, 2000));
        if (attempt < 3) {
          console.log(`[Provisioner] Waiting 30s before retry...`);
          await sleep(30_000);
        }
      }
    }
    if (!installOk) {
      console.error(`[Provisioner] All install attempts failed for ${vmIp}`);
      await updateVmStatus(vmId, "error", 6);
      return;
    }

    // Step 4: Verify VNC is running
    await updateVmStatus(vmId, "health_check", 10);
    const vncOk = await checkPort(vmIp, 5900, 30_000);
    if (!vncOk) {
      console.error(`[Provisioner] VNC port not open on ${vmIp}`);
      await updateVmStatus(vmId, "error", 10);
      return;
    }

    // Step 5: Done!
    await updateVmStatus(vmId, "ready", 12, {
      vncHealthy: true,
      vncPort: 5900,
      adminPassword: vmPass,
    });

    // Update board status
    const { boards } = await import("@hiveclip/db");
    await db.update(boards).set({ status: "running", updatedAt: new Date() }).where(eq(boards.id, boardId));

    console.log(`[Provisioner] Board ${boardId.slice(0, 8)} fully provisioned! VNC ready at ${vmIp}:5900`);
    activeJobs.delete(boardId);
  }

  function enqueue(job: ProvisionJob) {
    if (activeJobs.has(job.boardId)) return;
    // Start immediately in background
    activeJobs.set(job.boardId, setTimeout(() => {}, 0));
    processJob(job).catch((err) => {
      console.error(`[Provisioner] Unexpected error:`, err);
      activeJobs.delete(job.boardId);
    });
  }

  return { enqueue };
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function checkPort(host: string, port: number, timeout: number): Promise<boolean> {
  return new Promise((resolve) => {
    const s = new net.Socket();
    s.setTimeout(timeout);
    s.connect(port, host, () => { s.destroy(); resolve(true); });
    s.on("timeout", () => { s.destroy(); resolve(false); });
    s.on("error", () => { s.destroy(); resolve(false); });
  });
}
