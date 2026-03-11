$OLD = "\\43.157.180.16\C$"
$NEW = "\\92.246.128.240\C$"

# Establish SMB connections with credentials using net use
cmd /c "net use \\43.157.180.16\C$ /user:Administrator g4RQgOY4Jnr8"
cmd /c "net use \\92.246.128.240\C$ /user:Administrator 9q7Gfx3GH3CWyaV4"

Write-Host "Old server: $(Test-Path "$OLD\Users\Administrator")"
Write-Host "New server: $(Test-Path "$NEW\Users\Administrator")"

if (-not (Test-Path "$OLD\Users\Administrator") -or -not (Test-Path "$NEW\Users\Administrator")) {
    Write-Host "FAILED to connect"
    exit 1
}

# Create target dirs
@("Documents\GitHub", "Desktop", ".cloudflared", ".pm2") | ForEach-Object {
    New-Item -ItemType Directory -Path "$NEW\Users\Administrator\$_" -Force | Out-Null
}

# Copy cloudflared config
Write-Host "`n=== Copying .cloudflared ==="
robocopy "$OLD\Users\Administrator\.cloudflared" "$NEW\Users\Administrator\.cloudflared" /E /R:1 /W:1

# Copy PM2 dump
Write-Host "`n=== Copying PM2 dump ==="
Copy-Item "$OLD\Users\Administrator\.pm2\dump.pm2" "$NEW\Users\Administrator\.pm2\dump.pm2" -Force

# Copy LCC-Reports
Write-Host "`n=== Copying LCC-Reports ==="
robocopy "$OLD\Users\Administrator\Desktop\LCC-Reports" "$NEW\Users\Administrator\Desktop\LCC-Reports" /E /MT:8 /R:1 /W:1

# Copy testes-automacao (734MB)
Write-Host "`n=== Copying testes-automacao (734MB) ==="
robocopy "$OLD\Users\Administrator\Documents\GitHub\testes-automacao" "$NEW\Users\Administrator\Documents\GitHub\testes-automacao" /E /MT:8 /R:1 /W:1 /ETA

# Copy exclusive-dash
Write-Host "`n=== Copying exclusive-dash ==="
robocopy "$OLD\Users\Administrator\Desktop\exclusive-dash" "$NEW\Users\Administrator\Desktop\exclusive-dash" /E /MT:8 /R:1 /W:1 /ETA

# Copy woi-recados
Write-Host "`n=== Copying woi-recados ==="
robocopy "$OLD\Users\Administrator\Desktop\woi-recados" "$NEW\Users\Administrator\Desktop\woi-recados" /E /MT:8 /R:1 /W:1 /ETA

# Copy Pronet
Write-Host "`n=== Copying Pronet (317MB) ==="
robocopy "$OLD\Pronet" "$NEW\Pronet" /E /MT:8 /R:1 /W:1 /ETA

# Copy cloudflared binary
Write-Host "`n=== Copying cloudflared.exe ==="
Copy-Item "$OLD\Users\Administrator\Desktop\cloudflared.exe" "$NEW\Users\Administrator\Desktop\cloudflared.exe" -Force

# Cleanup
cmd /c "net use \\43.157.180.16\C$ /delete /yes"
cmd /c "net use \\92.246.128.240\C$ /delete /yes"

Write-Host "`n=== ALL COPIES COMPLETE ==="
