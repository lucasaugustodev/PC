export type BoardStatus = "provisioning" | "starting" | "running" | "stopped" | "error" | "destroying";
export type UserRole = "admin" | "user";
export type MembershipRole = "owner" | "admin" | "member" | "viewer";

export interface User {
  id: string;
  email: string;
  displayName: string | null;
  role: UserRole;
  createdAt: string;
}

export interface Board {
  id: string;
  ownerId: string;
  name: string;
  description: string | null;
  status: BoardStatus;
  brandColor: string | null;
  issuePrefix: string | null;
  createdAt: string;
  updatedAt: string;
  vm?: Vm | null;
}

export interface Vm {
  id: string;
  boardId: string;
  vultrInstanceId: string | null;
  region: string;
  plan: string;
  os: string;
  ipAddress: string | null;
  internalIp: string | null;
  hostname: string | null;
  vncPort: number;
  paperclipPort: number;
  vultrStatus: string | null;
  powerStatus: string | null;
  serverStatus: string | null;
  paperclipHealthy: boolean;
  vncHealthy: boolean;
  lastHealthCheck: string | null;
  provisioningStep: string | null;
  provisioningProgress: number;
  provisioningTotal: number;
  createdAt: string;
  updatedAt: string;
}

export interface BoardMembership {
  id: string;
  boardId: string;
  userId: string;
  role: MembershipRole;
  createdAt: string;
}

export interface ActivityLogEntry {
  id: string;
  boardId: string | null;
  userId: string | null;
  action: string;
  details: Record<string, unknown> | null;
  createdAt: string;
}

export interface ProvisioningStep {
  name: string;
  description: string;
  order: number;
}

export const PROVISIONING_STEPS: ProvisioningStep[] = [
  { name: "create_vm", description: "Creating server", order: 0 },
  { name: "wait_boot", description: "Waiting for boot", order: 1 },
  { name: "install_node", description: "Installing Node.js", order: 2 },
  { name: "install_git", description: "Installing Git", order: 3 },
  { name: "install_paperclip", description: "Installing Paperclip", order: 4 },
  { name: "configure_db", description: "Configuring database", order: 5 },
  { name: "install_vnc", description: "Installing VNC", order: 6 },
  { name: "configure_firewall", description: "Configuring firewall", order: 7 },
  { name: "install_claude", description: "Installing Claude Code", order: 8 },
  { name: "start_services", description: "Starting services", order: 9 },
  { name: "health_check", description: "Health check", order: 10 },
  { name: "finalize", description: "Finalizing", order: 11 },
];
