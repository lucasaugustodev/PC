import pyautogui, time, ctypes, subprocess, cv2
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

# Close browser windows
import os
os.system('powershell -Command "Get-Process -Name msedge,chrome -EA SilentlyContinue | Where-Object {$_.MainWindowTitle -like \"*Suprema*\"} | Stop-Process -Force" 2>nul')
# Just close the frontmost browser tab
pyautogui.hotkey('ctrl', 'w')
time.sleep(1)

# Activate SupremaPoker
r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.ShowWindow(hwnd, 9)
time.sleep(0.3)
user32.SetForegroundWindow(hwnd)
time.sleep(1)

# Get window rect
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
L, T = rect.left, rect.top
print(f"Window at ({L},{T})")

# Screenshot
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\mesa_screen.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\mesa_screen.png')
win = screen[rect.top:rect.bottom, rect.left:rect.right]
cv2.imwrite(r'C:\Users\PC\Downloads\mesa_win.png', win)
print(f"Window crop saved")

# Now find a mesa to click using reference image
ref = cv2.imread(r'C:\Users\PC\Downloads\SELECIONARU MA MESA .png')
if ref is not None:
    print(f"Reference mesa image: {ref.shape}")
    # Try to find the first table entry - crop a table row from reference
    # In the reference, first table "Battle+232" is around y=150-200
    table_tmpl = ref[150:200, 30:370]
    cv2.imwrite(r'C:\Users\PC\Downloads\table_tmpl.png', table_tmpl)
    
    result = cv2.matchTemplate(win, table_tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    print(f"Table match: {max_val:.3f} at {max_loc}")
    
    if max_val > 0.4:
        h, w = table_tmpl.shape[:2]
        rel_cx = max_loc[0] + w // 2
        rel_cy = max_loc[1] + h // 2
        abs_cx = L + rel_cx
        abs_cy = T + rel_cy
        print(f"Clicking table at ({abs_cx},{abs_cy})")
        pyautogui.moveTo(abs_cx, abs_cy, duration=0.2)
        time.sleep(0.3)
        pyautogui.click()
        print("CLICKED TABLE!")
    else:
        print("No table match, showing window for analysis")
else:
    print("Reference image not found")

time.sleep(3)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_mesa.png')
print("Done")
