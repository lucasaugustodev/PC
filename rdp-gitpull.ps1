Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);
}
"@
Add-Type -AssemblyName System.Windows.Forms

# Minimize all
& C:\tools\nircmd\nircmd.exe sendkeypress rwin+d 2>$null
Start-Sleep 2

# Click on RDP in taskbar - it should be one of the taskbar icons
# RDP window title contains "92.246.131.103"
$p = Get-Process mstsc | Select-Object -First 1
[Win32]::ShowWindow($p.MainWindowHandle, 3)
Start-Sleep 1
[Win32]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep 2

# Double-click in center of screen to ensure we're in the RDP and click on the PowerShell
# First, simulate Alt+Tab a few times to get to RDP
[System.Windows.Forms.SendKeys]::SendWait("%{TAB}")
Start-Sleep 2

# Type the command directly (not clipboard - SendKeys types character by character)
# Simple command: open new PowerShell
[System.Windows.Forms.SendKeys]::SendWait("^{ESCAPE}")  # Open Start menu
Start-Sleep 1
# Type powershell 
$chars = "powershell"
foreach ($c in $chars.ToCharArray()) {
    [System.Windows.Forms.SendKeys]::SendWait($c.ToString())
    Start-Sleep -Milliseconds 50
}
Start-Sleep 1
# Press Enter to open it
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Start-Sleep 3

# Now type the commands
$cmd = "cd C:\claude-launcher-web; git pull origin main; taskkill /f /im node.exe; Start-Sleep 3; schtasks /run /tn ClaudeLauncherWeb; Write-Host DONE"
[System.Windows.Forms.Clipboard]::SetText($cmd)
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Write-Host "Sent"
