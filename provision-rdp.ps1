# RDP Auto-Provisioner - connects via RDP and runs provision script
Add-Type -AssemblyName System.Windows.Forms

# Open RDP
Start-Process mstsc -ArgumentList "/v:92.246.128.233"
Start-Sleep -Seconds 8

# Accept certificate warning if present
$rdpWin = Get-Process mstsc -ErrorAction SilentlyContinue
if ($rdpWin) {
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Start-Sleep -Seconds 15
}

# Open Run dialog (Win+R)
[System.Windows.Forms.SendKeys]::SendWait("^{ESC}")
Start-Sleep -Seconds 2
[System.Windows.Forms.SendKeys]::SendWait("^{ESC}")
Start-Sleep -Seconds 1

# Actually use Win+R
$wshell = New-Object -ComObject wscript.shell
$wshell.SendKeys("^{ESC}")
Start-Sleep -Seconds 2

# Type powershell command in search/run
$wshell.AppActivate("92.246.128.233")
Start-Sleep -Seconds 1
$wshell.SendKeys("^(l)")
Start-Sleep -Seconds 500

Write-Host "RDP session opened. Sending commands..." -ForegroundColor Yellow

# Open PowerShell via keyboard
$wshell.SendKeys("#{r}")
Start-Sleep -Seconds 2
$wshell.SendKeys("powershell -ExecutionPolicy Bypass")
$wshell.SendKeys("{ENTER}")
Start-Sleep -Seconds 4

# Run provisioning one-liner
$cmd = "irm https://raw.githubusercontent.com/lucasaugustodev/claude-launcher-web/main/provision-remote.ps1 | iex"
$wshell.SendKeys($cmd)
Start-Sleep -Seconds 1
$wshell.SendKeys("{ENTER}")

Write-Host "Provisioning command sent! Check RDP window." -ForegroundColor Green
