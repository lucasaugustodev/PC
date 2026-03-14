"""
Install native PostgreSQL as Windows service and patch HiveClip to use it.
This avoids the embedded-postgres admin user issue entirely.
"""
import winrm
import time

ip = "216.238.108.202"
pw = "zR9=u}Z8{H@FAhk)"

s = winrm.Session(ip, auth=("Administrator", pw), transport="ntlm",
                   read_timeout_sec=600, operation_timeout_sec=540)

PATH_PREFIX = (
    r"C:\Program Files\nodejs;"
    r"C:\Program Files\Git\cmd;"
    r"C:\Users\Administrator\AppData\Roaming\npm;"
    r"C:\Python312;C:\Python312\Scripts;"
    r"C:\Program Files\PostgreSQL\16\bin"
)

# Kill old
s.run_cmd("taskkill /f /im node.exe 2>nul")
time.sleep(2)
s.run_cmd(r"rmdir /s /q C:\hiveclip\.pgdata 2>nul")

# Step 1: Install PostgreSQL 16
print("=== Step 1: Install PostgreSQL 16 ===")
r = s.run_cmd(r'dir "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"')
if r.status_code != 0:
    print("  Downloading PostgreSQL 16...")
    r = s.run_cmd(
        'curl.exe -L -o C:/Users/Administrator/pg-setup.exe '
        '"https://get.enterprisedb.com/postgresql/postgresql-16.8-1-windows-x64.exe" '
        '--connect-timeout 15 --max-time 600'
    )
    print(f"  Download RC: {r.status_code}")

    print("  Installing PostgreSQL 16 (silent)...")
    r = s.run_cmd(
        r'C:\Users\Administrator\pg-setup.exe --mode unattended '
        r'--unattendedmodeui none '
        r'--superpassword hiveclip '
        r'--serverport 5488 '
        r'--prefix "C:\Program Files\PostgreSQL\16" '
        r'--datadir "C:\Program Files\PostgreSQL\16\data" '
        r'--servicename postgresql-hiveclip '
        r'--enable-components server'
    )
    print(f"  Install RC: {r.status_code}")
    time.sleep(10)
else:
    print("  PostgreSQL already installed")

# Check service
r = s.run_ps("Get-Service postgresql* | Select-Object Name, Status | Format-Table")
print(f"  Services: {r.std_out.decode('utf-8', errors='replace').strip()}")

# Create hiveclip database
print("\n  Creating hiveclip database...")
r = s.run_cmd(
    f'cmd /c "set PATH={PATH_PREFIX};%PATH% && '
    f'psql -U postgres -p 5488 -c \\"CREATE DATABASE hiveclip;\\" 2>&1"'
)
out = r.std_out.decode("utf-8", errors="replace").strip()
print(f"  DB: {out[:200]}")

# Set PGPASSWORD env
r = s.run_cmd(
    f'cmd /c "set PATH={PATH_PREFIX};%PATH% && set PGPASSWORD=hiveclip && '
    f'psql -U postgres -p 5488 -c \\"SELECT version();\\" 2>&1"'
)
out = r.std_out.decode("utf-8", errors="replace").strip()
print(f"  Version: {out[:200]}")

# Step 2: Patch db.ts to use native PostgreSQL instead of embedded
print("\n=== Step 2: Patch db.ts ===")
new_db_ts = r'''import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "@hiveclip/db";

let sql: ReturnType<typeof postgres> | null = null;

export async function startDb() {
  const connectionString = `postgresql://postgres:hiveclip@localhost:5488/hiveclip`;
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
}

export { schema };
'''

# Write the patched db.ts
ps_write = f"""Set-Content -Path 'C:\\hiveclip\\server\\src\\db.ts' -Value @'
{new_db_ts}
'@ -Encoding UTF8"""
r = s.run_ps(ps_write)
print(f"  Write db.ts RC: {r.status_code}")

# Step 3: Start server as Administrator (PG runs as its own service user)
print("\n=== Step 3: Start HiveClip ===")
s.run_cmd('schtasks /delete /tn "HiveClipServer" /f 2>nul')

# Use Administrator since PG is now external
r = s.run_cmd(
    'schtasks /create /tn "HiveClipServer" /tr '
    '"cmd /c C:\\hiveclip\\start-server.bat > C:\\hiveclip\\server.log 2>&1" '
    '/sc onstart /ru SYSTEM /rl HIGHEST /f'
)
print(f"  Task create RC: {r.status_code}")

r = s.run_cmd('schtasks /run /tn "HiveClipServer"')
print(f"  Task run RC: {r.status_code}")

# Wait for port 3100
print("  Waiting for port 3100...")
port_ok = False
for i in range(25):
    time.sleep(8)
    r = s.run_cmd(
        'powershell -c "Test-NetConnection -ComputerName localhost -Port 3100 '
        '| Select-Object -ExpandProperty TcpTestSucceeded"'
    )
    result = r.std_out.decode().strip()
    if "True" in result:
        port_ok = True
        print(f"  PORT 3100 LISTENING! (attempt {i+1})")
        break
    if i % 5 == 0:
        print(f"  attempt {i+1}: waiting...")

if port_ok:
    print(f"\n{'='*50}")
    print(f"  HIVECLIP CONTROL PLANE RUNNING!")
    print(f"  URL:    http://{ip}:3100")
    print(f"  Health: http://{ip}:3100/api/health")
    print(f"{'='*50}")
else:
    print("\nChecking logs...")
    r = s.run_cmd(r"type C:\hiveclip\server.log")
    out = r.std_out.decode("utf-8", errors="replace")
    print(f"LOG:\n{out[-2000:]}")
