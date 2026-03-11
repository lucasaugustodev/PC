#Requires AutoHotkey v2.0
#SingleInstance Force

vmIP := "92.246.128.240"
provCmd := "irm https://raw.githubusercontent.com/lucasaugustodev/claude-launcher-web/main/provision-remote.ps1 | iex"

; Step 1: Launch RDP
Run("mstsc /v:" vmIP)
Sleep(5000)

; Step 2: Handle certificate warning
try {
    WinWait("Conexao de Area de Trabalho Remota",, 10)
    Send("{Enter}")
} catch {
}
try {
    WinWait("Remote Desktop Connection",, 5)
    Send("{Enter}")
} catch {
}

; Step 3: Wait for remote desktop to load
Sleep(20000)

; Step 4: Open PowerShell via Win+R
Send("#r")
Sleep(2000)
Send("powershell")
Sleep(500)
Send("{Enter}")
Sleep(4000)

; Step 5: Paste and run provision command
A_Clipboard := provCmd
Sleep(500)
Send("^v")
Sleep(1000)
Send("{Enter}")

Sleep(2000)
ExitApp()
