Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
Add-Type -AssemblyName System.Windows.Forms

$p = Get-Process mstsc | Select-Object -First 1
[Win32]::ShowWindow($p.MainWindowHandle, 3)
[Win32]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep -Seconds 2

# One big block to paste
$script = @'
$npmPath = "C:\Users\Administrator\AppData\Roaming\npm"
$machinePath = [Environment]::GetEnvironmentVariable("Path","Machine")
if ($machinePath -notlike "*npm*") { [Environment]::SetEnvironmentVariable("Path", "$machinePath;$npmPath", "Machine"); Write-Host "Added npm to PATH" } else { Write-Host "npm already in PATH" }
$env:Path += ";$npmPath"
claude --version
taskkill /f /im node.exe 2>$null
Start-Sleep 2
$fullPath = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + $npmPath
$bat = "@echo off`r`nset PATH=$fullPath;%PATH%`r`nset PORT=3001`r`ncd /d C:\claude-launcher-web`r`nnode server.js"
Set-Content "C:\claude-launcher-web\start.bat" $bat -Encoding ASCII
schtasks /run /tn "ClaudeLauncherWeb"
Write-Host "DONE"
'@

# Copy to clipboard and paste
[System.Windows.Forms.Clipboard]::SetText($script)
Start-Sleep -Milliseconds 500

# Ctrl+V to paste into RDP
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
