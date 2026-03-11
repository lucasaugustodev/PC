#Requires AutoHotkey v2.0

; Activate RDP window
if WinExist("ahk_exe mstsc.exe") {
    WinActivate
    WinMaximize
    Sleep 2000

    ; Click in center to make sure we're focused inside the RDP
    WinGetPos(&x, &y, &w, &h, "ahk_exe mstsc.exe")
    Click(x + w/2, y + h/2)
    Sleep 500

    ; Open PowerShell: Win+R, type powershell, Enter
    ; But Win key might go to local machine in RDP
    ; Use Ctrl+Alt+End to send Ctrl+Alt+Del to remote, or just click Start

    ; Alternative: right-click taskbar -> Windows PowerShell (Admin)
    ; Or just click on existing PowerShell window if visible

    ; Safest: use the existing PowerShell - just click on it in taskbar
    ; Let's type the command directly

    ; First, let's try sending Win+X which opens Power User menu in RDP
    ; In RDP, local Win key goes to local machine, need to use on-screen

    ; Simple approach: just type directly if a PowerShell/cmd is already focused
    Sleep 500

    ; Type the commands with SendText (literal text, no special keys)
    cmd := "cd C:\claude-launcher-web; npm install; $env:PORT='3001'; Start-Process powershell -ArgumentList '-Command', 'cd C:\claude-launcher-web; $env:PORT=3001; node server.js' -WindowStyle Normal; Write-Host 'SERVER STARTING'"

    ; Use clipboard approach - more reliable
    A_Clipboard := cmd
    Sleep 300
    Send "^v"
    Sleep 500
    Send "{Enter}"
    Sleep 1000

    ; Take screenshot
    Run 'C:\tools\nircmd\nircmd.exe savescreenshot C:\Users\PC\rdp-ahk-result.png'
} else {
    MsgBox "RDP window not found!"
}

ExitApp
