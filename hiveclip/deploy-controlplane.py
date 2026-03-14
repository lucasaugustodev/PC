"""
Deploy HiveClip Control Plane on a Windows VM.
Creates a non-admin user so embedded PostgreSQL can run.
"""
import winrm
import time
import sys

ip = "216.238.108.202"
pw = r"zR9=u}Z8{H@FAhk)"

s = winrm.Session(ip, auth=("Administrator", pw), transport="ntlm",
                   read_timeout_sec=600, operation_timeout_sec=540)

PATH_PREFIX = r"C:\Program Files\nodejs;C:\Program Files\Git\cmd;C:\Users\Administrator\AppData\Roaming\npm;C:\Python312;C:\Python312\Scripts"


def run(cmd, label=""):
    wrapped = f'cmd /c "set PATH={PATH_PREFIX};%PATH% && {cmd}"'
    r = s.run_cmd(wrapped)
    out = r.std_out.decode("utf-8", errors="replace").strip()
    err = r.std_err.decode("utf-8", errors="replace").strip()
    if label:
        status = "OK" if r.status_code == 0 else f"FAIL(RC={r.status_code})"
        detail = out[-200:] if r.status_code == 0 else (err or out)[-300:]
        safe = detail.encode("ascii", errors="replace").decode("ascii")
        print(f"  {label}: {status} - {safe}")
    return r


# Kill old processes
s.run_cmd("taskkill /f /im node.exe 2>nul")
time.sleep(2)
s.run_cmd(r"rmdir /s /q C:\hiveclip\.pgdata 2>nul")

# Create non-admin user for PostgreSQL
print("=== Creating hiveclip user ===")
r = s.run_cmd("net user hiveclip Hive2026!Pass /add")
print(f"  User: RC={r.status_code} {r.std_out.decode('utf-8', errors='replace').strip()[:100]}")

# Give permissions
r = s.run_cmd(r"icacls C:\hiveclip /grant hiveclip:(OI)(CI)F /T /Q")
print(f"  icacls: RC={r.status_code}")

# Also grant access to npm global + node
s.run_cmd(r'icacls "C:\Program Files\nodejs" /grant hiveclip:(OI)(CI)RX /T /Q')
s.run_cmd(r'icacls "C:\Users\Administrator\AppData\Roaming\npm" /grant hiveclip:(OI)(CI)RX /T /Q')
s.run_cmd(r'icacls "C:\Program Files\Git" /grant hiveclip:(OI)(CI)RX /T /Q')

# Delete old task
s.run_cmd('schtasks /delete /tn "HiveClipServer" /f 2>nul')

# Create task as hiveclip user
print("=== Creating scheduled task ===")
r = s.run_ps(
    "schtasks /create /tn 'HiveClipServer' "
    "/tr 'cmd /c C:\\hiveclip\\start-server.bat > C:\\hiveclip\\server.log 2>&1' "
    "/sc onstart /ru hiveclip /rp 'Hive2026!Pass' /rl LIMITED /f"
)
out = r.std_out.decode("utf-8", errors="replace").strip()
err = r.std_err.decode("utf-8", errors="replace").strip()
print(f"  Task: {out} {err}")

# Start the task
print("=== Starting server ===")
r = s.run_cmd('schtasks /run /tn "HiveClipServer"')
print(f"  Run: RC={r.status_code}")

# Wait for port 3100
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
        print(f"  Port 3100: LISTENING! (attempt {i+1})")
        break
    print(f"  attempt {i+1}: not yet")

if port_ok:
    print(f"\n{'='*50}")
    print(f"  HIVECLIP CONTROL PLANE RUNNING!")
    print(f"  URL:    http://{ip}:3100")
    print(f"  Health: http://{ip}:3100/api/health")
    print(f"{'='*50}")
else:
    print("Checking logs...")
    r = s.run_cmd(r"type C:\hiveclip\server.log")
    out = r.std_out.decode("utf-8", errors="replace")
    print(f"LOG:\n{out[-2000:]}")
