#Requires AutoHotkey v2.0
#SingleInstance Force

; Open RDP
Run "mstsc /v:92.246.128.233"

; Wait for RDP window
Sleep 5000

; If there's a certificate warning, accept it
WinWait("Conexão de Área de Trabalho Remota",, 15)
if WinExist("Conexão de Área de Trabalho Remota") {
    WinActivate
    Sleep 1000
    Send "{Enter}"
}

; Wait for desktop to load
Sleep 15000

; Open PowerShell via Win+R
Send "#r"
Sleep 2000
Send "powershell -ExecutionPolicy Bypass{Enter}"
Sleep 3000

; Download and run provisioning script
provCmd := "irm https://raw.githubusercontent.com/lucasaugustodev/claude-launcher-web/main/provision-remote.ps1 | iex"
Send provCmd
Sleep 500
Send "{Enter}"

; Done - script will run on its own
