Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
$p = Get-Process mstsc | Select-Object -First 1
$h = $p.MainWindowHandle
[Win32]::ShowWindow($h, 3)
[Win32]::SetForegroundWindow($h)
Start-Sleep -Seconds 2
