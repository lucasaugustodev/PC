#Requires AutoHotkey v2.0
#SingleInstance Force

; PowerShell is already open in the RDP session
; Just type the command using SendInput (character by character, reliable)
Sleep(1000)

; Use a two-step approach: download then run
SendInput("iwr 'https://raw.githubusercontent.com/lucasaugustodev/claude-launcher-web/main/provision-remote.ps1' -OutFile C:\p.ps1")
Sleep(500)
SendInput("{Enter}")
Sleep(8000)

; Now run it
SendInput("C:\p.ps1")
Sleep(500)
SendInput("{Enter}")

Sleep(3000)
ExitApp()
