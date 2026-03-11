import paramiko, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('64.176.15.189', username='root', password='M3g*e#hmbhwQ2#(D', timeout=30)

def run(cmd, t=300):
    print(f'\n>>> {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=t)
    ec = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out:
        print(out[-1500:])
    if err and ec > 0:
        print(f'ERR: {err[-500:]}')
    print(f'[exit {ec}]')
    return ec, out

# Stop docker container
run('docker compose -f /opt/claude-launcher-web/docker-compose.yml down 2>/dev/null; docker stop claude-launcher-web 2>/dev/null; docker rm claude-launcher-web 2>/dev/null; echo done')

# Install Node.js 18
run('curl -fsSL https://deb.nodesource.com/setup_18.x | bash -', 120)
run('apt-get install -y -qq nodejs', 120)
run('node --version && npm --version')

# Install build tools for node-pty
run('apt-get install -y -qq build-essential python3 make gcc g++', 60)

# Install pm2
run('npm install -g pm2', 60)

# Install Claude Code CLI globally
run('npm install -g @anthropic-ai/claude-code', 60)

# GitHub CLI
run('gh --version 2>/dev/null || echo "gh not found, installing..." && apt-get install -y -qq gh 2>/dev/null; gh --version', 120)

# npm install in project dir
run('cd /opt/claude-launcher-web && rm -rf node_modules && npm install', 180)

# Start with pm2
run('pm2 delete claude-launcher-web 2>/dev/null; cd /opt/claude-launcher-web && PORT=3001 pm2 start server.js --name claude-launcher-web', 30)
run('pm2 save', 10)
run('pm2 startup systemd -u root --hp /root 2>&1 | tail -3', 10)

time.sleep(4)
run('pm2 status')
run('curl -s http://localhost:3001/api/health')

ssh.close()
print()
print('=' * 50)
print('Claude Launcher Web: http://64.176.15.189:3001')
print('=' * 50)
