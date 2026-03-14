Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class MouseOps {
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);
    public static void Click(int x, int y) {
        SetCursorPos(x, y);
        System.Threading.Thread.Sleep(100);
        mouse_event(0x0002, 0, 0, 0, 0); // left down
        mouse_event(0x0004, 0, 0, 0, 0); // left up
    }
}
"@
# The Login button appears to be around x=520, y=490 based on the screenshot
# The Suprema login window is centered, Login button is the blue button
[MouseOps]::Click(520, 490)
Write-Output "CLICKED LOGIN"
