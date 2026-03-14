Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinPos {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
}
"@
$p = Get-Process -Name "SupremaPoker" -ErrorAction SilentlyContinue
if ($p) {
    $r = New-Object WinPos+RECT
    [WinPos]::GetWindowRect($p.MainWindowHandle, [ref]$r)
    Write-Output "LEFT=$($r.Left) TOP=$($r.Top) RIGHT=$($r.Right) BOTTOM=$($r.Bottom)"
    Write-Output "WIDTH=$($r.Right - $r.Left) HEIGHT=$($r.Bottom - $r.Top)"
} else {
    Write-Output "NOT_FOUND"
}
