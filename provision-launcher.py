import paramiko
import os
import sys
import time
import tarfile
import io

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

HOST = '64.176.15.189'
USER = 'root'
PASS = 'M3g*e#hmbhwQ2#(D'
PROJECT_DIR = r'C:\Users\PC\claude-launcher-web'
REMOTE_DIR = '/opt/claude-launcher-web'

def ssh_connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    return ssh

def run_cmd(ssh, cmd, timeout=300):
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out[-2000:] if len(out) > 2000 else out)
    if err:
        print(f"STDERR: {err[-1000:]}" if len(err) > 1000 else f"STDERR: {err}")
    print(f"Exit code: {exit_code}")
    return exit_code, out, err

def create_tar():
    """Create tar of the project, excluding node_modules and .git"""
    buf = io.BytesIO()
    exclude = {'node_modules', '.git', 'data', '.env'}

    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for root, dirs, files in os.walk(PROJECT_DIR):
            # Skip excluded dirs
            dirs[:] = [d for d in dirs if d not in exclude]
            for f in files:
                filepath = os.path.join(root, f)
                arcname = os.path.relpath(filepath, PROJECT_DIR)
                try:
                    tar.add(filepath, arcname=arcname)
                except Exception as e:
                    print(f"Skip {arcname}: {e}")

    buf.seek(0)
    return buf

def upload_project(ssh):
    print("\n=== Creating project archive ===")
    tar_buf = create_tar()
    tar_size = tar_buf.getbuffer().nbytes
    print(f"Archive size: {tar_size / 1024 / 1024:.1f} MB")

    sftp = ssh.open_sftp()

    # Create remote dir
    run_cmd(ssh, f'mkdir -p {REMOTE_DIR}')

    # Upload tar
    remote_tar = f'{REMOTE_DIR}/project.tar.gz'
    print(f"Uploading to {remote_tar}...")
    sftp.putfo(tar_buf, remote_tar)
    print("Upload complete!")

    # Extract
    run_cmd(ssh, f'cd {REMOTE_DIR} && tar xzf project.tar.gz && rm project.tar.gz')
    sftp.close()

def main():
    ssh = ssh_connect()
    print("Connected to server!")

    # Step 1: Install Docker
    print("\n=== Step 1: Installing Docker ===")
    run_cmd(ssh, 'apt-get update -qq')
    run_cmd(ssh, 'apt-get install -y -qq ca-certificates curl gnupg lsb-release', timeout=120)
    run_cmd(ssh, 'install -m 0755 -d /etc/apt/keyrings')
    run_cmd(ssh, 'curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc')
    run_cmd(ssh, 'chmod a+r /etc/apt/keyrings/docker.asc')
    run_cmd(ssh, '''echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null''')
    run_cmd(ssh, 'apt-get update -qq', timeout=120)
    run_cmd(ssh, 'apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin', timeout=300)
    run_cmd(ssh, 'systemctl enable docker && systemctl start docker')
    run_cmd(ssh, 'docker --version')

    # Step 2: Upload project
    print("\n=== Step 2: Uploading project ===")
    upload_project(ssh)
    run_cmd(ssh, f'ls -la {REMOTE_DIR}/')

    # Step 3: Build Docker image
    print("\n=== Step 3: Building Docker image ===")
    exit_code, _, _ = run_cmd(ssh, f'cd {REMOTE_DIR} && docker compose build --no-cache', timeout=600)
    if exit_code != 0:
        print("Build failed! Trying with docker build directly...")
        run_cmd(ssh, f'cd {REMOTE_DIR} && docker build -t claude-launcher-web .', timeout=600)

    # Step 4: Start container
    print("\n=== Step 4: Starting container ===")
    run_cmd(ssh, f'cd {REMOTE_DIR} && docker compose up -d', timeout=120)

    # Step 5: Verify
    print("\n=== Step 5: Verification ===")
    time.sleep(5)
    run_cmd(ssh, 'docker ps')
    run_cmd(ssh, 'docker logs claude-launcher-web --tail 20')
    run_cmd(ssh, 'curl -s http://localhost:3001/api/health || echo "Health check failed"')

    # Step 6: Open firewall
    print("\n=== Step 6: Firewall ===")
    run_cmd(ssh, 'ufw allow 3001/tcp 2>/dev/null; iptables -I INPUT -p tcp --dport 3001 -j ACCEPT 2>/dev/null; echo "Port 3001 opened"')

    print(f"\n{'='*50}")
    print(f"DONE! Claude Launcher Web should be available at:")
    print(f"  http://64.176.15.189:3001")
    print(f"{'='*50}")

    ssh.close()

if __name__ == '__main__':
    main()
