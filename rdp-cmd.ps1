Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
# Activate RDP
$p = Get-Process mstsc | Select-Object -First 1
[Win32]::ShowWindow($p.MainWindowHandle, 3)
[Win32]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep -Seconds 2

# Send keystrokes into RDP
Add-Type -AssemblyName System.Windows.Forms

# Type the commands
$cmds = @(
    '$npmPath = "C:\Users\Administrator\AppData\Roaming\npm"',
    '$machinePath = [Environment]::GetEnvironmentVariable("Path","Machine")',
    'if ($machinePath -notlike "*npm*") { [Environment]::SetEnvironmentVariable("Path", "$machinePath;$npmPath", "Machine"); Write-Host "Added npm to PATH" }',
    '$env:Path += ";$npmPath"',
    'claude --version',
    'taskkill /f /im node.exe',
    'Start-Sleep 2',
    '$batContent = "@echo off`nset PATH=" + [Environment]::GetEnvironmentVariable("Path","Machine") + ";$npmPath;%PATH%`nset PORT=3001`ncd /d C:\claude-launcher-web`nnode server.js"',
    'Set-Content -Path "C:\claude-launcher-web\start.bat" -Value $batContent -Encoding ASCII',
    'schtasks /run /tn "ClaudeLauncherWeb"',
    'Write-Host "DONE - Launcher restarting with updated PATH"'
)

foreach ($cmd in $cmds) {
    [System.Windows.Forms.SendKeys]::SendWait($cmd)
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Start-Sleep -Milliseconds 800
}
