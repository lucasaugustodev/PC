"""
HiveClip VM Provisioner
Installs TightVNC + claude-launcher-web on a Windows VM via WinRM.
"""
import winrm
import sys
import os
import time

# Read credentials from args or env vars
ip = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("VM_IP", "")
pw = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("VM_PASS", "")

if not ip or not pw:
    print("Usage: provision-vm.py <ip> <password>")
    sys.exit(1)

GITHUB_VNC_URL = "https://github.com/lucasaugustodev/hiveclip/releases/download/vnc-installer/tightvnc.msi"
TIGHTVNC_URL = "https://www.tightvnc.com/download/2.8.84/tightvnc-2.8.84-gpl-setup-64bit.msi"
LAUNCHER_REPO = "https://github.com/lucasaugustodev/claude-launcher-web.git"

print(f"Connecting to {ip}...")
s = winrm.Session(ip, auth=("Administrator", pw), transport="basic", read_timeout_sec=300, operation_timeout_sec=240)

r = s.run_cmd("hostname")
print(f"Hostname: {r.std_out.decode().strip()}")

# ========== STEP 1: Install TightVNC ==========
print("\n=== Step 1: TightVNC ===")
r = s.run_ps("Get-Service tvnserver -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status")
vnc_status = r.std_out.decode().strip()
print(f"TightVNC status: {vnc_status or 'NOT INSTALLED'}")

if "Running" not in vnc_status:
    msi_path = r"C:\Users\Administrator\vnc.msi"
    downloaded = False
    for url in [GITHUB_VNC_URL, TIGHTVNC_URL]:
        print(f"Downloading from {url[:60]}...")
        r = s.run_cmd(f'curl.exe -L -o "{msi_path}" "{url}" --connect-timeout 15 --max-time 180')
        if r.status_code == 0:
            r2 = s.run_cmd(f'powershell -c "(Get-Item \'{msi_path}\').Length"')
            size = int(r2.std_out.decode().strip() or "0")
            if size > 1000000:
                print(f"  Downloaded OK ({size} bytes)")
                downloaded = True
                break
            print(f"  File too small ({size} bytes)")
        else:
            print(f"  Failed (RC={r.status_code})")

    if not downloaded:
        print("ERROR: Could not download TightVNC MSI")
        sys.exit(1)

    print("Installing TightVNC...")
    r = s.run_cmd(
        f'msiexec /i "{msi_path}" /quiet /norestart '
        'ADDLOCAL=Server SET_USEVNCAUTHENTICATION=1 VALUE_OF_USEVNCAUTHENTICATION=1 '
        'SET_PASSWORD=1 VALUE_OF_PASSWORD=hiveclip123 '
        'SET_USECONTROLAUTHENTICATION=1 VALUE_OF_USECONTROLAUTHENTICATION=1 '
        'SET_CONTROLPASSWORD=1 VALUE_OF_CONTROLPASSWORD=hiveclip123'
    )
    print(f"  Install RC: {r.status_code}")

    r = s.run_cmd('netsh advfirewall firewall add rule name=VNC-5900 dir=in action=allow protocol=TCP localport=5900')
    print(f"  Firewall RC: {r.status_code}")

    time.sleep(5)
    r = s.run_cmd('net start tvnserver')
    print(f"  Start RC: {r.status_code}")

r = s.run_cmd('sc query tvnserver')
if "RUNNING" in r.std_out.decode():
    print("TightVNC: OK")
else:
    print("WARNING: TightVNC not running")

# ========== STEP 2: Install claude-launcher-web ==========
print("\n=== Step 2: claude-launcher-web ===")

# Check if already installed
r = s.run_cmd(r'dir C:\claude-launcher-web\server.js')
launcher_exists = r.status_code == 0

if not launcher_exists:
    # Install Node.js if not present
    r = s.run_cmd('node --version')
    if r.status_code != 0:
        print("Installing Node.js...")
        r = s.run_cmd(
            'curl.exe -L -o C:/Users/Administrator/node-setup.msi '
            '"https://nodejs.org/dist/v22.14.0/node-v22.14.0-x64.msi" '
            '--connect-timeout 15 --max-time 300'
        )
        if r.status_code == 0:
            r2 = s.run_cmd(r'msiexec /i C:\Users\Administrator\node-setup.msi /quiet /norestart')
            print(f"  Node.js install RC: {r2.status_code}")
            time.sleep(5)
        else:
            print("  WARNING: Node.js download failed")
    else:
        print(f"Node.js: {r.std_out.decode().strip()}")

    # Install Git if not present
    r = s.run_cmd('git --version')
    if r.status_code != 0:
        print("Installing Git...")
        r = s.run_cmd(
            'curl.exe -L -o C:/Users/Administrator/git-setup.exe '
            '"https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.2/Git-2.47.1.2-64-bit.exe" '
            '--connect-timeout 15 --max-time 300'
        )
        if r.status_code == 0:
            r2 = s.run_cmd(r'C:\Users\Administrator\git-setup.exe /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"')
            print(f"  Git install RC: {r2.status_code}")
            time.sleep(5)
        else:
            print("  WARNING: Git download failed")
    else:
        print(f"Git: {r.std_out.decode().strip()}")

    # Clone claude-launcher-web
    print("Cloning claude-launcher-web...")
    r = s.run_cmd(f'git clone {LAUNCHER_REPO} C:\\claude-launcher-web')
    print(f"  Clone RC: {r.status_code}")
    if r.status_code != 0:
        print(f"  stderr: {r.std_err.decode()[:200]}")

    # Install npm dependencies
    print("Installing dependencies...")
    r = s.run_cmd(r'cd C:\claude-launcher-web && npm install --production')
    print(f"  npm install RC: {r.status_code}")

else:
    print("claude-launcher-web already installed, pulling latest...")
    r = s.run_cmd(r'cd C:\claude-launcher-web && git pull')
    print(f"  git pull: {r.std_out.decode().strip()[:100]}")

# Open firewall port 3001
r = s.run_cmd('netsh advfirewall firewall add rule name=ClaudeLauncher-3001 dir=in action=allow protocol=TCP localport=3001')
print(f"Firewall port 3001: RC={r.status_code}")

# NOTE: start.bat creation moved to after CLI installs so PATH includes all tools

# ========== STEP 3: Install Dev CLIs ==========
print("\n=== Step 3: Dev CLIs ===")

# First, persist npm global bin + common tool paths into system PATH
NPM_GLOBAL = r"C:\Users\Administrator\AppData\Roaming\npm"
EXTRA_PATHS = [
    r"C:\Program Files\nodejs",
    r"C:\Program Files\Git\cmd",
    r"C:\Program Files\GitHub CLI",
    NPM_GLOBAL,
]

print("Updating system PATH...")
r = s.run_ps('[Environment]::GetEnvironmentVariable("Path","Machine")')
machine_path = r.std_out.decode().strip()

paths_to_add = [p for p in EXTRA_PATHS if p.lower() not in machine_path.lower()]
if paths_to_add:
    new_path = machine_path.rstrip(";") + ";" + ";".join(paths_to_add)
    # Persist to system PATH so it survives reboots
    escaped = new_path.replace("'", "''")
    r = s.run_ps(f"[Environment]::SetEnvironmentVariable('Path', '{escaped}', 'Machine')")
    print(f"  Added to PATH: {', '.join(paths_to_add)}")
else:
    new_path = machine_path
    print("  PATH already configured")

# Build full PATH for current session
r = s.run_ps('[Environment]::GetEnvironmentVariable("Path","User")')
user_path = r.std_out.decode().strip()
full_path = new_path + ";" + user_path

def run_cmd(cmd, label=""):
    """Run cmd with full PATH"""
    wrapped = f'cmd /c "set PATH={full_path} && {cmd}"'
    r = s.run_cmd(wrapped)
    out = r.std_out.decode().strip()
    err = r.std_err.decode().strip()
    if label:
        status = "OK" if r.status_code == 0 else f"RC={r.status_code}"
        detail = out[:120] if r.status_code == 0 else (err or out)[:150]
        print(f"  {label}: {status} - {detail}")
    return r

# --- Install all npm CLIs in a single batch (much faster than sequential) ---
npm_packages = {
    '@anthropic-ai/claude-code': 'claude',
    '@google/gemini-cli': 'gemini',
    'cline': 'cline',
    '@googleworkspace/cli': 'gws',
    'playwright': 'npx playwright',
}

# Check which are already installed
missing = []
for pkg, cmd in npm_packages.items():
    check = f'cmd /c "set PATH={full_path} && {cmd} --version"' if not cmd.startswith('npx') else f'cmd /c "set PATH={full_path} && npx playwright --version"'
    r = s.run_cmd(check)
    if r.status_code != 0:
        missing.append(pkg)
        print(f"  {pkg}: needs install")
    else:
        print(f"  {pkg}: already installed ({r.std_out.decode().strip()[:50]})")

if missing:
    pkg_list = ' '.join(missing)
    print(f"Installing {len(missing)} npm packages in one batch: {pkg_list}")
    run_cmd(f'npm install -g {pkg_list}', f"npm install batch ({len(missing)} packages)")
else:
    print("  All npm packages already installed")

# --- GitHub CLI (MSI installer, not npm) ---
print("Installing GitHub CLI...")
r = run_cmd('gh --version', "Check gh")
if r.status_code != 0:
    print("  Downloading GitHub CLI...")
    r = s.run_cmd(
        'curl.exe -L -o C:/Users/Administrator/gh-setup.msi '
        '"https://github.com/cli/cli/releases/download/v2.67.0/gh_2.67.0_windows_amd64.msi" '
        '--connect-timeout 15 --max-time 180'
    )
    if r.status_code == 0:
        r2 = s.run_cmd(r'msiexec /i C:\Users\Administrator\gh-setup.msi /quiet /norestart')
        print(f"  GitHub CLI install RC: {r2.status_code}")
        time.sleep(3)
        run_cmd('gh --version', "GitHub CLI")
    else:
        print("  WARNING: GitHub CLI download failed")

# --- Playwright chromium browser ---
print("Installing Playwright chromium...")
run_cmd('npx playwright install chromium', "Playwright install chromium")

# ========== STEP 4: Start claude-launcher-web with full PATH ==========
print("\n=== Step 4: Start Launcher ===")

# Re-read system PATH now that all CLIs are installed (gh MSI adds to PATH)
print("Building start.bat with full PATH (after all CLI installs)...")
r = s.run_ps('[Environment]::GetEnvironmentVariable("Path","Machine")')
sys_path = r.std_out.decode().strip()
npm_bin = r"C:\Users\Administrator\AppData\Roaming\npm"
gh_dir = r"C:\Program Files\GitHub CLI"
for extra in [npm_bin, gh_dir]:
    if extra.lower() not in sys_path.lower():
        sys_path = sys_path.rstrip(";") + ";" + extra

bat_content = f"@echo off\nset PATH={sys_path};%PATH%\nset PORT=3001\ncd /d C:\\claude-launcher-web\nnode server.js\n"
escaped_bat = bat_content.replace("'", "''")
r = s.run_ps(f"Set-Content -Path 'C:\\claude-launcher-web\\start.bat' -Value '{escaped_bat}' -Encoding ASCII")
print(f"  Write start.bat: RC={r.status_code}")

# Create a scheduled task to auto-start claude-launcher-web
print("Creating auto-start task...")
s.run_cmd('schtasks /delete /tn "ClaudeLauncherWeb" /f')
r = s.run_cmd(
    'schtasks /create /tn "ClaudeLauncherWeb" /tr '
    '"cmd /c C:\\claude-launcher-web\\start.bat" '
    '/sc onstart /ru SYSTEM /rl HIGHEST /f'
)
print(f"  Task create RC: {r.status_code}")

# Start it now (kill any existing instance first)
print("Starting claude-launcher-web...")
s.run_cmd('taskkill /f /im node.exe 2>nul')
time.sleep(2)
r = s.run_cmd(r'schtasks /run /tn "ClaudeLauncherWeb"')
print(f"  Task run RC: {r.status_code}")

# Wait and check if port 3001 is listening
time.sleep(5)
r = s.run_cmd('powershell -c "Test-NetConnection -ComputerName localhost -Port 3001 | Select-Object -ExpandProperty TcpTestSucceeded"')
port_ok = r.std_out.decode().strip()
print(f"Port 3001 listening: {port_ok}")

# --- Verify all ---
print("\nVerifying installations...")
run_cmd('node --version', "Node.js")
run_cmd('git --version', "Git")
run_cmd('claude --version', "Claude Code")
run_cmd('gh --version', "GitHub CLI")
run_cmd('gemini --version', "Gemini CLI")
run_cmd('cline --version', "Cline CLI")
run_cmd('gws --version', "Google Workspace CLI")
run_cmd('npx playwright --version', "Playwright CLI")

print("\n=== Provisioning complete ===")
print(f"  VNC: {ip}:5900 (password: hiveclip123)")
print(f"  Launcher: {ip}:3001")
print(f"  CLIs: claude, gh, gemini, cline, gws, playwright")
