import base64, json, os, sys
import urllib.request

VULTR_API_KEY = os.environ.get("VULTR_API_KEY", "2BSQFQU3VO3WFEZTMMVCSIZC2AUBQCCO7I2Q")
SCRIPT_ID = "d2f602f1-11fa-4cf2-bc4f-e90998926898"

script = r"""# HiveClip VM Setup - Install TightVNC + Enable WinRM
Set-ExecutionPolicy Bypass -Scope Process -Force
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Download TightVNC from GitHub mirror (tightvnc.com is blocked from some Vultr regions)
$vncUrl = "https://github.com/lucasaugustodev/hiveclip/releases/download/vnc-installer/tightvnc.msi"
$installer = "C:\Users\Administrator\tightvnc.msi"
& curl.exe -L -o $installer $vncUrl --connect-timeout 15 --max-time 180
$size = (Get-Item $installer -ErrorAction SilentlyContinue).Length
if ($size -lt 1000000) {
    $vncUrl2 = "https://www.tightvnc.com/download/2.8.84/tightvnc-2.8.84-gpl-setup-64bit.msi"
    Invoke-WebRequest -Uri $vncUrl2 -OutFile $installer -UseBasicParsing
}

Start-Process msiexec.exe -ArgumentList "/i `"$installer`" /quiet /norestart ADDLOCAL=Server SET_USEVNCAUTHENTICATION=1 VALUE_OF_USEVNCAUTHENTICATION=1 SET_PASSWORD=1 VALUE_OF_PASSWORD=hiveclip123 SET_USECONTROLAUTHENTICATION=1 VALUE_OF_USECONTROLAUTHENTICATION=1 SET_CONTROLPASSWORD=1 VALUE_OF_CONTROLPASSWORD=hiveclip123" -Wait -NoNewWindow

New-NetFirewallRule -DisplayName "VNC-In" -Direction Inbound -Protocol TCP -LocalPort 5900 -Action Allow -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "WinRM-HTTP" -Direction Inbound -Protocol TCP -LocalPort 5985 -Action Allow -ErrorAction SilentlyContinue

winrm quickconfig -force
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'

Start-Service tvnserver -ErrorAction SilentlyContinue
"HiveClip setup complete $(Get-Date)" | Out-File C:\hiveclip-ready.txt
"""

b64 = base64.b64encode(script.encode()).decode()
payload = json.dumps({"script": b64, "type": "boot", "name": "hiveclip-vnc-setup"})

req = urllib.request.Request(
    f"https://api.vultr.com/v2/startup-scripts/{SCRIPT_ID}",
    data=payload.encode(),
    headers={
        "Authorization": f"Bearer {VULTR_API_KEY}",
        "Content-Type": "application/json",
    },
    method="PATCH",
)
try:
    resp = urllib.request.urlopen(req)
    print(f"Updated startup script: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"Error: {e.code} {e.read().decode()[:200]}")
