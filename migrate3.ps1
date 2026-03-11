$OLD = "\\43.157.180.16\C$"
$NEW = "\\92.246.128.240\C$"

cmd /c "net use \\43.157.180.16\C$ /user:Administrator g4RQgOY4Jnr8"
cmd /c "net use \\92.246.128.240\C$ /user:Administrator 9q7Gfx3GH3CWyaV4"

Write-Host "Old: $(Test-Path "$OLD\Users\Administrator") New: $(Test-Path "$NEW\Users\Administrator")"
if (-not (Test-Path "$OLD\Users\Administrator")) { Write-Host "FAILED"; exit 1 }

Write-Host "=== Copying .cloudflared ==="
robocopy "$OLD\Users\Administrator\.cloudflared" "$NEW\Users\Administrator\.cloudflared" /E /R:1 /W:1 /NJH /NJS
Write-Host "=== Copying PM2 dump ==="
Copy-Item "$OLD\Users\Administrator\.pm2\dump.pm2" "$NEW\Users\Administrator\.pm2\dump.pm2" -Force -ErrorAction SilentlyContinue
Write-Host "=== Copying LCC-Reports ==="
robocopy "$OLD\Users\Administrator\Desktop\LCC-Reports" "$NEW\Users\Administrator\Desktop\LCC-Reports" /E /MT:8 /R:1 /W:1 /NJH /NJS
Write-Host "=== Copying testes-automacao (734MB) ==="
robocopy "$OLD\Users\Administrator\Documents\GitHub\testes-automacao" "$NEW\Users\Administrator\Documents\GitHub\testes-automacao" /E /MT:8 /R:1 /W:1 /NJH /NJS
Write-Host "=== Copying exclusive-dash ==="
robocopy "$OLD\Users\Administrator\Desktop\exclusive-dash" "$NEW\Users\Administrator\Desktop\exclusive-dash" /E /MT:8 /R:1 /W:1 /NJH /NJS
Write-Host "=== Copying woi-recados ==="
robocopy "$OLD\Users\Administrator\Desktop\woi-recados" "$NEW\Users\Administrator\Desktop\woi-recados" /E /MT:8 /R:1 /W:1 /NJH /NJS
Write-Host "=== Copying Pronet (317MB) ==="
robocopy "$OLD\Pronet" "$NEW\Pronet" /E /MT:8 /R:1 /W:1 /NJH /NJS
Write-Host "=== Copying cloudflared.exe ==="
Copy-Item "$OLD\Users\Administrator\Desktop\cloudflared.exe" "$NEW\Users\Administrator\Desktop\cloudflared.exe" -Force -ErrorAction SilentlyContinue
Write-Host "=== ALL COPIES COMPLETE ==="
