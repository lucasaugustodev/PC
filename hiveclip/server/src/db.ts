import EmbeddedPostgres from "embedded-postgres";
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "@hiveclip/db";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.resolve(__dirname, "../../.pgdata");

let pg: EmbeddedPostgres | null = null;
let sql: ReturnType<typeof postgres> | null = null;

export async function startDb() {
  pg = new EmbeddedPostgres({
    databaseDir: DATA_DIR,
    user: "hiveclip",
    password: "hiveclip",
    port: 5488,
    persistent: true,
  });

  try {
    await pg.initialise();
  } catch {
    // Data dir already exists, that's fine
  }
  await pg.start();

  const connectionString = `postgresql://hiveclip:hiveclip@localhost:5488/postgres`;
  sql = postgres(connectionString);
  const db = drizzle(sql, { schema });

  // Create tables if they don't exist
  await sql`CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
  )`;

  await sql`CREATE TABLE IF NOT EXISTS boards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'provisioning',
    brand_color TEXT,
    issue_prefix TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
  )`;

  await sql`CREATE TABLE IF NOT EXISTS vms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id UUID UNIQUE NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    vultr_instance_id TEXT UNIQUE,
    region TEXT NOT NULL,
    plan TEXT NOT NULL,
    os TEXT NOT NULL,
    ip_address TEXT,
    internal_ip TEXT,
    hostname TEXT,
    admin_password TEXT,
    vnc_port INTEGER DEFAULT 5900,
    paperclip_port INTEGER DEFAULT 3100,
    vultr_status TEXT,
    power_status TEXT,
    server_status TEXT,
    paperclip_healthy BOOLEAN DEFAULT false,
    vnc_healthy BOOLEAN DEFAULT false,
    last_health_check TIMESTAMP,
    provisioning_step TEXT,
    provisioning_progress INTEGER DEFAULT 0,
    provisioning_total INTEGER DEFAULT 12,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
  )`;

  return { db, sql };
}

export async function stopDb() {
  if (sql) await sql.end();
  if (pg) await pg.stop();
}

export { schema };
