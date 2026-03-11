#Requires AutoHotkey v2.0
#SingleInstance Force

; First, activate the RDP window
SetTitleMatchMode(2)
try {
    WinActivate("92.246.128.240")
    WinWaitActive("92.246.128.240",, 5)
} catch {
    try {
        WinActivate("Conexao de Area de Trabalho Remota")
        WinWaitActive("Conexao de Area de Trabalho Remota",, 5)
    } catch {
        try {
            WinActivate("Remote Desktop")
            WinWaitActive("Remote Desktop",, 5)
        }
    }
}
Sleep(2000)

; Click in the center to make sure we're focused inside RDP
Click(640, 400)
Sleep(1000)

; Download script first
SendInput("iwr 'https://raw.githubusercontent.com/lucasaugustodev/claude-launcher-web/main/provision-remote.ps1' -OutFile C:\p.ps1")
Sleep(500)
SendInput("{Enter}")
Sleep(10000)

; Run it
SendInput("C:\p.ps1")
Sleep(500)
SendInput("{Enter}")

Sleep(2000)
ExitApp()
