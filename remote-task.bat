@echo off
schtasks /create /s 92.246.128.233 /u Administrator /p AEyMT716EimszFFB /tn "HiveProvision" /tr "powershell.exe -ExecutionPolicy Bypass -Command Invoke-WebRequest -Uri https://raw.githubusercontent.com/lucasaugustodev/claude-launcher-web/main/provision-remote.ps1 -OutFile C:\provision.ps1; C:\provision.ps1" /sc once /st 00:00 /ru Administrator /rp AEyMT716EimszFFB /f
if %ERRORLEVEL% EQU 0 (
echo TASK_CREATED
schtasks /run /s 92.246.128.233 /u Administrator /p AEyMT716EimszFFB /tn "HiveProvision"
)
