"""
Fix PostgreSQL permissions issue and start HiveClip Control Plane.
Creates a non-admin local user and runs the server under it.
"""
import winrm
import time

ip = "216.238.108.202"
pw = "zR9=u}Z8{H@FAhk)"

s = winrm.Session(ip, auth=("Administrator", pw), transport="ntlm",
                   read_timeout_sec=600, operation_timeout_sec=540)

PATH_PREFIX = (
    r"C:\Program Files\nodejs;"
    r"C:\Program Files\Git\cmd;"
    r"C:\Users\Administrator\AppData\Roaming\npm;"
    r"C:\Python312;C:\Python312\Scripts"
)

# Kill old stuff
print("Cleaning up...")
s.run_cmd("taskkill /f /im node.exe 2>nul")
time.sleep(2)
s.run_cmd(r"rmdir /s /q C:\hiveclip\.pgdata 2>nul")

# Step 1: Create local user via PowerShell
print("\n=== Creating local user 'hvsvc' ===")
ps_create_user = """
$pass = ConvertTo-SecureString 'Hv!3Cl1p26' -AsPlainText -Force
try {
    New-LocalUser -Name 'hvsvc' -Password $pass -FullName 'HiveClip SVC' -PasswordNeverExpires -ErrorAction Stop
    Write-Output "CREATED"
} catch {
    if ($_.Exception.Message -match 'already exists') {
        Write-Output "EXISTS"
    } else {
        Write-Output "ERROR: $($_.Exception.Message)"
    }
}
"""
r = s.run_ps(ps_create_user)
out = r.std_out.decode("utf-8", errors="replace").strip()
err = r.std_err.decode("utf-8", errors="replace").strip()
print(f"  Result: {out}")
if err and "CLIXML" not in err:
    print(f"  Stderr: {err[:300]}")

# Verify user
r = s.run_ps("Get-LocalUser | Select-Object Name, Enabled | Format-Table")
print(f"  Users: {r.std_out.decode('utf-8', errors='replace').strip()}")

# Step 2: Grant permissions
print("\n=== Granting permissions ===")
ps_perms = r"""
icacls 'C:\hiveclip' /grant 'hvsvc:(OI)(CI)F' /T /Q 2>&1
icacls 'C:\Program Files\nodejs' /grant 'hvsvc:(OI)(CI)RX' /T /Q 2>&1
icacls 'C:\Program Files\Git' /grant 'hvsvc:(OI)(CI)RX' /T /Q 2>&1
# Create npm dir for hvsvc user
New-Item -ItemType Directory -Force -Path 'C:\Users\hvsvc\AppData\Roaming\npm' 2>$null
# Copy npm global modules
Copy-Item -Path 'C:\Users\Administrator\AppData\Roaming\npm\*' -Destination 'C:\Users\hvsvc\AppData\Roaming\npm\' -Recurse -Force 2>$null
icacls 'C:\Users\Administrator\AppData\Roaming\npm' /grant 'hvsvc:(OI)(CI)RX' /T /Q 2>&1
"""
r = s.run_ps(ps_perms)
print(f"  RC={r.status_code}")

# Step 3: Delete old task, create new one as hvsvc
print("\n=== Creating scheduled task ===")
s.run_cmd('schtasks /delete /tn "HiveClipServer" /f 2>nul')

ps_task = """
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c C:\\hiveclip\\start-server.bat > C:\\hiveclip\\server.log 2>&1'
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365)
Register-ScheduledTask -TaskName 'HiveClipServer' -Action $action -Trigger $trigger -Settings $settings -User 'hvsvc' -Password 'Hv!3Cl1p26' -RunLevel Limited -Force
"""
r = s.run_ps(ps_task)
out = r.std_out.decode("utf-8", errors="replace").strip()
err = r.std_err.decode("utf-8", errors="replace").strip()
print(f"  Task: {out[:200]}")
if err and "CLIXML" not in err:
    print(f"  Err: {err[:300]}")

# Step 4: Start the task
print("\n=== Starting HiveClip ===")
r = s.run_cmd('schtasks /run /tn "HiveClipServer"')
print(f"  Run RC={r.status_code}")

# Step 5: Wait for port 3100
print("Waiting for port 3100...")
port_ok = False
for i in range(30):
    time.sleep(8)
    r = s.run_cmd(
        'powershell -c "Test-NetConnection -ComputerName localhost -Port 3100 '
        '| Select-Object -ExpandProperty TcpTestSucceeded"'
    )
    result = r.std_out.decode().strip()
    if "True" in result:
        port_ok = True
        print(f"  PORT 3100 LISTENING! (attempt {i+1})")
        break
    if i % 5 == 0:
        print(f"  attempt {i+1}: not yet")

if port_ok:
    print(f"\n{'='*50}")
    print(f"  HIVECLIP CONTROL PLANE RUNNING!")
    print(f"  URL:    http://{ip}:3100")
    print(f"  Health: http://{ip}:3100/api/health")
    print(f"{'='*50}")
else:
    print("\nChecking logs...")
    r = s.run_cmd(r"type C:\hiveclip\server.log")
    out = r.std_out.decode("utf-8", errors="replace")
    print(f"LOG:\n{out[-2000:]}")
