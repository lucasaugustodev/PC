Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
"@
Add-Type -AssemblyName System.Windows.Forms

$p = Get-Process mstsc | Select-Object -First 1
$h = $p.MainWindowHandle

# Retry to get focus
for ($i = 0; $i -lt 5; $i++) {
    [Win32]::ShowWindow($h, 3)
    [Win32]::SetForegroundWindow($h)
    Start-Sleep -Milliseconds 500
    $fg = [Win32]::GetForegroundWindow()
    if ($fg -eq $h) {
        Write-Host "RDP in focus on attempt $i"
        break
    }
}

Start-Sleep -Seconds 1

# Use Alt+Tab as fallback
[System.Windows.Forms.SendKeys]::SendWait("%{TAB}")
Start-Sleep -Seconds 2

# Paste
$script = @'
$npmPath = "C:\Users\Administrator\AppData\Roaming\npm"; $machinePath = [Environment]::GetEnvironmentVariable("Path","Machine"); if ($machinePath -notlike "*npm*") { [Environment]::SetEnvironmentVariable("Path", "$machinePath;$npmPath", "Machine") }; $env:Path += ";$npmPath"; claude --version; taskkill /f /im node.exe 2>$null; Start-Sleep 2; $fp = [Environment]::GetEnvironmentVariable("Path","Machine") + ";$npmPath"; Set-Content "C:\claude-launcher-web\start.bat" "@echo off`r`nset PATH=$fp;%PATH%`r`nset PORT=3001`r`ncd /d C:\claude-launcher-web`r`nnode server.js" -Encoding ASCII; schtasks /run /tn "ClaudeLauncherWeb"; Write-Host "DONE"
'@

[System.Windows.Forms.Clipboard]::SetText($script)
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Write-Host "Commands sent"
