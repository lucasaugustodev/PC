// Installs TightVNC on a remote Windows VM via WinRM
// Run with: node scripts/setup-vnc-remote.js <ip> <password>

const { execSync } = require("child_process");

const ip = process.argv[2] || "216.238.104.3";
const password = process.argv[3] || "9gL=eh]Scc@jSeW2";

const psScript = `
$ErrorActionPreference = 'Stop'
$pass = ConvertTo-SecureString '${password}' -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential('Administrator', $pass)

# Add to trusted hosts
Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '${ip}' -Force -Concatenate

$session = New-PSSession -ComputerName '${ip}' -Credential $cred -ErrorAction Stop
Write-Host "Connected to $($ip)"

Invoke-Command -Session $session -ScriptBlock {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    # Check if TightVNC already installed
    $svc = Get-Service -Name "tvnserver" -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Host "TightVNC already installed, status: $($svc.Status)"
        if ($svc.Status -ne 'Running') { Start-Service tvnserver }
        return
    }

    Write-Host "Downloading TightVNC..."
    $url = "https://www.tightvnc.com/download/2.8.84/tightvnc-2.8.84-gpl-setup-64bit.msi"
    $installer = "$env:TEMP\\tightvnc.msi"
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing

    Write-Host "Installing TightVNC..."
    Start-Process msiexec.exe -ArgumentList "/i `"$installer`" /quiet /norestart ADDLOCAL=Server SET_USEVNCAUTHENTICATION=1 VALUE_OF_USEVNCAUTHENTICATION=1 SET_PASSWORD=1 VALUE_OF_PASSWORD=hiveclip123 SET_USECONTROLAUTHENTICATION=1 VALUE_OF_USECONTROLAUTHENTICATION=1 SET_CONTROLPASSWORD=1 VALUE_OF_CONTROLPASSWORD=hiveclip123" -Wait -NoNewWindow

    Write-Host "Configuring firewall..."
    New-NetFirewallRule -DisplayName "VNC-5900" -Direction Inbound -Protocol TCP -LocalPort 5900 -Action Allow -ErrorAction SilentlyContinue

    Start-Sleep -Seconds 3
    $svc = Get-Service -Name "tvnserver" -ErrorAction SilentlyContinue
    if ($svc) {
        Start-Service tvnserver -ErrorAction SilentlyContinue
        Write-Host "TightVNC installed and running!"
    } else {
        Write-Host "WARNING: tvnserver service not found after install"
    }
}

Remove-PSSession $session
Write-Host "Done!"
`;

try {
  // Must run as admin for Set-Item WSMan
  const result = execSync(
    `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "${psScript.replace(/"/g, '\\"').replace(/\n/g, '; ')}"`,
    { stdio: "inherit", timeout: 120000 }
  );
} catch (e) {
  console.error("Failed:", e.message);
  process.exit(1);
}
