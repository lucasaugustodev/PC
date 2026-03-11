Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
Add-Type -AssemblyName System.Windows.Forms

# Show desktop, then activate RDP
& C:\tools\nircmd\nircmd.exe sendkeypress rwin+d 2>$null
Start-Sleep 1
$p = Get-Process mstsc | Select-Object -First 1
[Win32]::ShowWindow($p.MainWindowHandle, 3)
[Win32]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep 2

$script = @'
Stop-Service sshd -Force; $cfg = "C:\ProgramData\ssh\sshd_config"; @"
Port 22
PasswordAuthentication yes
PubkeyAuthentication yes
PermitRootLogin yes
AllowUsers Administrator
Subsystem sftp sftp-server.exe
"@ | Set-Content $cfg -Force -Encoding ASCII; Remove-Item "C:\ProgramData\ssh\administrators_authorized_keys" -Force -ErrorAction SilentlyContinue; net user Administrator hZJK5I8Dtm0RhIzT; Start-Service sshd; netsh advfirewall firewall add rule name=SSH-22 dir=in action=allow protocol=TCP localport=22 2>$null; Get-Content $cfg; Write-Host "SSH FIXED"; Test-NetConnection localhost -Port 22
'@

[System.Windows.Forms.Clipboard]::SetText($script)
Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
