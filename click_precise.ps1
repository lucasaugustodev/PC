Add-Type @"
using System;
using System.Runtime.InteropServices;
public class MC {
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);
}
"@
# Window: Left=278 Top=111, Size=421x759
# In ref image (407x700): Login button center is approx x=325, y=365
# Scale: 421/407=1.034, 759/700=1.084 (accounting for title bar ~30px)
# Absolute: 278 + 325*1.034 = 278+336 = 614, 111 + 30 + 335*1.084 = 141+363 = 504
# Try clicking right at the "Login" text
[MC]::SetCursorPos(614, 490)
Start-Sleep -Milliseconds 300
[MC]::mouse_event(0x0002, 0, 0, 0, 0)
[MC]::mouse_event(0x0004, 0, 0, 0, 0)
Write-Output "CLICKED at 614,490"
