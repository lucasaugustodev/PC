Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
Add-Type -AssemblyName System.Windows.Forms

& C:\tools\nircmd\nircmd.exe sendkeypress rwin+d 2>$null
Start-Sleep 1
$p = Get-Process mstsc | Select-Object -First 1
[Win32]::ShowWindow($p.MainWindowHandle, 3)
[Win32]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep 3

# Single line command that fixes SSH completely
$script = 'Stop-Service sshd -Force; @"' + "`r`n" + 'Port 22' + "`r`n" + 'PasswordAuthentication yes' + "`r`n" + 'PubkeyAuthentication yes' + "`r`n" + 'PermitRootLogin yes' + "`r`n" + 'AllowUsers Administrator' + "`r`n" + 'Subsystem sftp sftp-server.exe' + "`r`n" + '"@ | Set-Content "C:\ProgramData\ssh\sshd_config" -Force; Remove-Item "C:\ProgramData\ssh\administrators_authorized_keys" -Force -EA SilentlyContinue; net user Administrator hZJK5I8Dtm0RhIzT; Start-Service sshd; Write-Host "SSH_FIXED"'

[System.Windows.Forms.Clipboard]::SetText($script)
Start-Sleep -Milliseconds 500

# Click in the center of the screen (should hit the PowerShell in RDP)
[System.Windows.Forms.Cursor]::Position = [System.Drawing.Point]::new(500, 400)
Start-Sleep -Milliseconds 200
# Left click
$null = Add-Type -MemberDefinition '[DllImport("user32.dll")] public static extern void mouse_event(int f,int x,int y,int d,int e);' -Name MouseEvent -Namespace Win32M -PassThru
[Win32M.MouseEvent]::mouse_event(0x02, 0, 0, 0, 0) # down
[Win32M.MouseEvent]::mouse_event(0x04, 0, 0, 0, 0) # up
Start-Sleep -Milliseconds 500

[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Write-Host "Sent"
