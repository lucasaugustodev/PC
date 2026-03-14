#!/bin/bash
set -e
echo "=== HiveClip Control Plane Deploy ==="

echo ">>> System packages"
apt-get update -qq
apt-get install -y -qq curl git python3 python3-pip postgresql postgresql-client >/dev/null 2>&1
echo "  Done"

echo ">>> Node.js 22"
curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1
apt-get install -y -qq nodejs >/dev/null 2>&1
node --version

echo ">>> pnpm"
npm install -g pnpm >/dev/null 2>&1
pnpm --version

echo ">>> pywinrm"
pip3 install pywinrm --break-system-packages -q 2>/dev/null || pip3 install pywinrm -q
echo "  Done"

echo ">>> PostgreSQL"
systemctl start postgresql
systemctl enable postgresql
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'hiveclip';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE hiveclip;" 2>/dev/null || true
PG_HBA=$(find /etc/postgresql -name pg_hba.conf | head -1)
sed -i 's/peer$/md5/' "$PG_HBA"
sed -i 's/scram-sha-256$/md5/' "$PG_HBA"
systemctl restart postgresql
echo "  Done"

echo ">>> Clone repo"
if [ ! -d /opt/hiveclip ]; then
    git clone https://github.com/lucasaugustodev/hiveclip.git /opt/hiveclip
else
    cd /opt/hiveclip && git pull
fi

echo ">>> pnpm install"
cd /opt/hiveclip
pnpm install --no-frozen-lockfile 2>&1 | tail -3

echo ">>> Patch db.ts"
cat > /opt/hiveclip/server/src/db.ts << 'DBEOF'
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "@hiveclip/db";

let sql: ReturnType<typeof postgres> | null = null;

export async function startDb() {
  const connectionString = `postgresql://postgres:hiveclip@localhost:5432/hiveclip`;
  sql = postgres(connectionString);
  const db = drizzle(sql, { schema });

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
DBEOF
echo "  Done"

echo ">>> .env"
cat > /opt/hiveclip/server/.env << 'ENVEOF'
VULTR_API_KEY=2BSQFQU3VO3WFEZTMMVCSIZC2AUBQCCO7I2Q
JWT_SECRET=hiveclip-prod-secret-2026-linux
PORT=3100
ENVEOF

echo ">>> systemd service"
cat > /etc/systemd/system/hiveclip.service << 'SVCEOF'
[Unit]
Description=HiveClip Control Plane
After=network.target postgresql.service

[Service]
Type=simple
WorkingDirectory=/opt/hiveclip/server
ExecStart=/usr/bin/npx tsx src/index.ts
Restart=always
RestartSec=5
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
SVCEOF
systemctl daemon-reload
systemctl enable hiveclip

echo ">>> Firewall"
ufw allow 3100/tcp 2>/dev/null || true

echo ">>> Starting HiveClip"
systemctl start hiveclip
for i in $(seq 1 15); do
    if curl -s http://localhost:3100/api/health >/dev/null 2>&1; then
        echo ""
        echo "=================================================="
        echo "  HIVECLIP RUNNING on http://216.238.123.232:3100"
        echo "=================================================="
        exit 0
    fi
    sleep 4
done
echo "LOGS:"
journalctl -u hiveclip --no-pager -n 30
