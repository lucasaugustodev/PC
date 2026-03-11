# Map both servers
$credOld = New-Object System.Management.Automation.PSCredential("Administrator", (ConvertTo-SecureString "g4RQgOY4Jnr8" -AsPlainText -Force))
$credNew = New-Object System.Management.Automation.PSCredential("Administrator", (ConvertTo-SecureString "9q7Gfx3GH3CWyaV4" -AsPlainText -Force))
New-PSDrive -Name "X" -PSProvider FileSystem -Root "\\43.157.180.16\C$" -Credential $credOld
New-PSDrive -Name "Y" -PSProvider FileSystem -Root "\\92.246.128.240\C$" -Credential $credNew

Write-Host "Old server (X:): $(Test-Path 'X:\Users\Administrator')"
Write-Host "New server (Y:): $(Test-Path 'Y:\Users\Administrator')"

if (-not (Test-Path 'X:\Users\Administrator') -or -not (Test-Path 'Y:\Users\Administrator')) {
    Write-Host "FAILED to map drives"
    exit 1
}

# Create target dirs
New-Item -ItemType Directory -Path "Y:\Users\Administrator\Documents\GitHub" -Force | Out-Null
New-Item -ItemType Directory -Path "Y:\Users\Administrator\Desktop" -Force | Out-Null
New-Item -ItemType Directory -Path "Y:\Users\Administrator\.cloudflared" -Force | Out-Null
New-Item -ItemType Directory -Path "Y:\Users\Administrator\.pm2" -Force | Out-Null

# Copy cloudflared config
Write-Host "`n=== Copying .cloudflared ==="
robocopy "X:\Users\Administrator\.cloudflared" "Y:\Users\Administrator\.cloudflared" /E /R:1 /W:1

# Copy PM2 dump
Write-Host "`n=== Copying PM2 dump ==="
Copy-Item "X:\Users\Administrator\.pm2\dump.pm2" "Y:\Users\Administrator\.pm2\dump.pm2" -Force

# Copy LCC-Reports
Write-Host "`n=== Copying LCC-Reports ==="
robocopy "X:\Users\Administrator\Desktop\LCC-Reports" "Y:\Users\Administrator\Desktop\LCC-Reports" /E /MT:8 /R:1 /W:1

# Copy testes-automacao (734MB)
Write-Host "`n=== Copying testes-automacao (734MB) ==="
robocopy "X:\Users\Administrator\Documents\GitHub\testes-automacao" "Y:\Users\Administrator\Documents\GitHub\testes-automacao" /E /MT:8 /R:1 /W:1 /ETA

# Copy exclusive-dash
Write-Host "`n=== Copying exclusive-dash ==="
robocopy "X:\Users\Administrator\Desktop\exclusive-dash" "Y:\Users\Administrator\Desktop\exclusive-dash" /E /MT:8 /R:1 /W:1 /ETA

# Copy woi-recados
Write-Host "`n=== Copying woi-recados ==="
robocopy "X:\Users\Administrator\Desktop\woi-recados" "Y:\Users\Administrator\Desktop\woi-recados" /E /MT:8 /R:1 /W:1 /ETA

# Copy Pronet
Write-Host "`n=== Copying Pronet (317MB) ==="
robocopy "X:\Pronet" "Y:\Pronet" /E /MT:8 /R:1 /W:1 /ETA

# Copy cloudflared binary
Write-Host "`n=== Copying cloudflared.exe ==="
Copy-Item "X:\Users\Administrator\Desktop\cloudflared.exe" "Y:\Users\Administrator\Desktop\cloudflared.exe" -Force

# Cleanup
Remove-PSDrive -Name "X" -Force
Remove-PSDrive -Name "Y" -Force

Write-Host "`n=== ALL COPIES COMPLETE ==="
