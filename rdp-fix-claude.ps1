Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
Add-Type -AssemblyName System.Windows.Forms

# Minimize all, then activate RDP
$null = & C:\tools\nircmd\nircmd.exe sendkeypress rwin+d
Start-Sleep 1
$p = Get-Process mstsc | Select-Object -First 1
[Win32]::ShowWindow($p.MainWindowHandle, 3)
[Win32]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep 2

# Click on the PowerShell window area in the RDP
[System.Windows.Forms.SendKeys]::SendWait("")
Start-Sleep -Milliseconds 500

$script = 'npm list -g @anthropic-ai/claude-code; where.exe claude 2>$null; ls "$env:APPDATA\npm\claude*" 2>$null; ls "$env:APPDATA\npm\node_modules\@anthropic-ai" 2>$null; npm install -g @anthropic-ai/claude-code; $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User") + ";$env:APPDATA\npm"; claude --version'

[System.Windows.Forms.Clipboard]::SetText($script)
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
