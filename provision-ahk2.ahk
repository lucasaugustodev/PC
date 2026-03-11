#Requires AutoHotkey v2.0
#SingleInstance Force

; Step 1: Close any existing RDP to this IP
try {
    WinClose("92.246.128.240")
    Sleep(2000)
}

; Step 2: Launch RDP with fullscreen + keyboardhook=2
Run('mstsc "C:\Users\PC\hiveclip-auto.rdp"')
Sleep(8000)

; Step 3: Handle certificate warning - send Tab+Enter or just Enter
Send("{Tab}{Enter}")
Sleep(3000)
Send("{Enter}")
Sleep(20000)

; Step 4: Now in fullscreen RDP, Win+R goes to REMOTE machine
Send("#r")
Sleep(3000)
Send("powershell")
Sleep(500)
Send("{Enter}")
Sleep(5000)

; Step 5: Paste provision command
A_Clipboard := "irm https://raw.githubusercontent.com/lucasaugustodev/claude-launcher-web/main/provision-remote.ps1 | iex"
Sleep(500)
Send("^v")
Sleep(1000)
Send("{Enter}")

Sleep(3000)
ExitApp()
