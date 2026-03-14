Add-Type @"
using System;
using System.Runtime.InteropServices;
public class MouseOps3 {
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);
    public static void Click(int x, int y) {
        SetCursorPos(x, y);
        System.Threading.Thread.Sleep(200);
        mouse_event(0x0002, 0, 0, 0, 0);
        mouse_event(0x0004, 0, 0, 0, 0);
    }
}
"@
# The "Login" button text appears to be at the right side of password field around x=555, y=467
[MouseOps3]::Click(555, 467)
Write-Output "CLICKED"
