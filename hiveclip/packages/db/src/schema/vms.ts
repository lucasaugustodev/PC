import { boolean, integer, pgTable, text, timestamp, uuid } from "drizzle-orm/pg-core";
import { boards } from "./boards.js";

export const vms = pgTable("vms", {
  id: uuid("id").primaryKey().defaultRandom(),
  boardId: uuid("board_id")
    .unique()
    .notNull()
    .references(() => boards.id, { onDelete: "cascade" }),
  vultrInstanceId: text("vultr_instance_id").unique(),
  region: text("region").notNull(),
  plan: text("plan").notNull(),
  os: text("os").notNull(),
  ipAddress: text("ip_address"),
  internalIp: text("internal_ip"),
  hostname: text("hostname"),
  adminPassword: text("admin_password"),
  vncPort: integer("vnc_port").default(5900),
  paperclipPort: integer("paperclip_port").default(3100),
  vultrStatus: text("vultr_status"),
  powerStatus: text("power_status"),
  serverStatus: text("server_status"),
  paperclipHealthy: boolean("paperclip_healthy").default(false),
  vncHealthy: boolean("vnc_healthy").default(false),
  lastHealthCheck: timestamp("last_health_check"),
  provisioningStep: text("provisioning_step"),
  provisioningProgress: integer("provisioning_progress").default(0),
  provisioningTotal: integer("provisioning_total").default(12),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});
