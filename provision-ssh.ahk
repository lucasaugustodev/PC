#Requires AutoHotkey v2.0
#SingleInstance Force

; Step 1: Launch RDP with keyboard redirect
Run('mstsc "C:\Users\PC\hiveclip-auto.rdp"')
Sleep(8000)

; Step 2: Accept certificate warning if any
Loop 3 {
    Send("{Enter}")
    Sleep(1000)
}

; Step 3: Wait for remote desktop to fully load
Sleep(18000)

; Step 4: Win+R goes to REMOTE now (keyboardhook:i:2)
Send("#r")
Sleep(2500)

; Step 5: Type powershell and run
Send("powershell")
Sleep(500)
Send("{Enter}")
Sleep(5000)

; Step 6: Enable SSH - short command via clipboard
sshCmd := "Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0; Start-Service sshd; Set-Service sshd -StartupType Automatic; New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH SSH' -Enabled True -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow"
A_Clipboard := sshCmd
Sleep(500)
Send("^v")
Sleep(1000)
Send("{Enter}")

Sleep(3000)
ExitApp()
