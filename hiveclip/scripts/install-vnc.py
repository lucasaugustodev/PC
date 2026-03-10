import winrm
import sys
import os
import time

# Read credentials from args or env vars (env vars avoid shell escaping issues)
ip = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("VM_IP", "216.238.104.3")
pw = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("VM_PASS", "9gL=eh]Scc@jSeW2")

# GitHub mirror for TightVNC MSI (tightvnc.com is blocked from some Vultr regions)
GITHUB_URL = "https://github.com/lucasaugustodev/hiveclip/releases/download/vnc-installer/tightvnc.msi"
TIGHTVNC_URL = "https://www.tightvnc.com/download/2.8.84/tightvnc-2.8.84-gpl-setup-64bit.msi"

print(f"Connecting to {ip}...")
s = winrm.Session(ip, auth=("Administrator", pw), transport="ntlm")

r = s.run_cmd("hostname")
print(f"Hostname: {r.std_out.decode().strip()}")

r = s.run_ps("Get-Service tvnserver -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status")
status = r.std_out.decode().strip()
print(f"TightVNC status: {status or 'NOT INSTALLED'}")

if "Running" in status:
    print("TightVNC already running!")
    sys.exit(0)

# Download MSI via curl.exe (cmd) - try GitHub first, then tightvnc.com
msi_path = r"C:\Users\Administrator\vnc.msi"
downloaded = False
for url in [GITHUB_URL, TIGHTVNC_URL]:
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

# Install
print("Installing TightVNC...")
r = s.run_cmd(
    f'msiexec /i "{msi_path}" /quiet /norestart '
    'ADDLOCAL=Server SET_USEVNCAUTHENTICATION=1 VALUE_OF_USEVNCAUTHENTICATION=1 '
    'SET_PASSWORD=1 VALUE_OF_PASSWORD=hiveclip123 '
    'SET_USECONTROLAUTHENTICATION=1 VALUE_OF_USECONTROLAUTHENTICATION=1 '
    'SET_CONTROLPASSWORD=1 VALUE_OF_CONTROLPASSWORD=hiveclip123'
)
print(f"  Install RC: {r.status_code}")

# Firewall
r = s.run_cmd('netsh advfirewall firewall add rule name=VNC-5900 dir=in action=allow protocol=TCP localport=5900')
print(f"  Firewall RC: {r.status_code}")

# Start service
time.sleep(5)
r = s.run_cmd('net start tvnserver')
print(f"  Start RC: {r.status_code}")

# Verify
r = s.run_cmd('sc query tvnserver')
output = r.std_out.decode()
if "RUNNING" in output:
    print("TightVNC is RUNNING!")
else:
    print(f"Service not running: {output[:200]}")
    sys.exit(1)
