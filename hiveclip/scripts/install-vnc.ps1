# Install TightVNC Server on Windows VM
# Usage: powershell -File install-vnc.ps1 -VmIp <ip> -VmPassword <password> -VncPassword <vnc-password>

param(
    [Parameter(Mandatory=$true)][string]$VmIp,
    [Parameter(Mandatory=$true)][string]$VmPassword,
    [string]$VncPassword = "hiveclip123"
)

$secPass = ConvertTo-SecureString $VmPassword -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential("Administrator", $secPass)

Write-Host "Connecting to $VmIp..."

$session = New-PSSession -ComputerName $VmIp -Credential $cred -UseSSL:$false -SessionOption (New-PSSessionOption -SkipCACheck -SkipCNCheck -SkipRevocationCheck)

Invoke-Command -Session $session -ScriptBlock {
    param($VncPassword)

    Write-Host "Downloading TightVNC..."
    $url = "https://www.tightvnc.com/download/2.8.84/tightvnc-2.8.84-gpl-setup-64bit.msi"
    $installer = "$env:TEMP\tightvnc.msi"

    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing

    Write-Host "Installing TightVNC Server..."
    $hexPass = ($VncPassword.PadRight(8, [char]0).Substring(0, 8).ToCharArray() | ForEach-Object { '{0:X2}' -f [int]$_ }) -join ''

    Start-Process msiexec.exe -ArgumentList "/i `"$installer`" /quiet /norestart ADDLOCAL=Server SET_USEVNCAUTHENTICATION=1 VALUE_OF_USEVNCAUTHENTICATION=1 SET_PASSWORD=1 VALUE_OF_PASSWORD=$VncPassword SET_USECONTROLAUTHENTICATION=1 VALUE_OF_USECONTROLAUTHENTICATION=1 SET_CONTROLPASSWORD=1 VALUE_OF_CONTROLPASSWORD=$VncPassword" -Wait -NoNewWindow

    Write-Host "Configuring firewall..."
    New-NetFirewallRule -DisplayName "TightVNC" -Direction Inbound -Protocol TCP -LocalPort 5900 -Action Allow -ErrorAction SilentlyContinue

    Write-Host "Checking TightVNC service..."
    $svc = Get-Service -Name "tvnserver" -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Host "TightVNC Server is $($svc.Status)"
        if ($svc.Status -ne "Running") {
            Start-Service tvnserver
            Write-Host "Started TightVNC Server"
        }
    } else {
        Write-Host "WARNING: TightVNC service not found!"
    }

    Write-Host "Done! VNC should be accessible on port 5900"
} -ArgumentList $VncPassword

Remove-PSSession $session
Write-Host "VNC installation complete on $VmIp"
