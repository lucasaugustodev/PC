import pyautogui, time, ctypes, subprocess, cv2
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

# Kill browser tabs with Suprema Poker site
# Close ALL chrome/edge windows showing suprema
import os
os.system('taskkill /FI "WINDOWTITLE eq *Suprema Poker*" /F 2>nul')
os.system('taskkill /FI "WINDOWTITLE eq *supremapoker*" /F 2>nul')
time.sleep(1)

# Activate SupremaPoker app
r = subprocess.run(['powershell', '-Command', 
    '(Get-Process -Name SupremaPoker).MainWindowHandle'], 
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.ShowWindow(hwnd, 9)  # SW_RESTORE
time.sleep(0.5)
user32.SetForegroundWindow(hwnd)
time.sleep(1)

# Get window rect
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), 
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
L, T, R, B = rect.left, rect.top, rect.right, rect.bottom
print(f"Window: ({L},{T}) to ({R},{B}), size {R-L}x{B-T}")

# Screenshot AFTER bringing to front
time.sleep(0.5)
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\clean.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\clean.png')

# Crop just the window
win = screen[T:B, L:R]
cv2.imwrite(r'C:\Users\PC\Downloads\win_clean.png', win)

# Template match within the WINDOW CROP only
ref = cv2.imread(r'C:\Users\PC\Downloads\SELECIONAR CLUBE FICHAS NET.png')
text_tmpl = ref[252:270, 125:225]

result = cv2.matchTemplate(win, text_tmpl, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)
h, w = text_tmpl.shape[:2]

# These are coordinates RELATIVE TO WINDOW
rel_cx = max_loc[0] + w // 2
rel_cy = max_loc[1] + h // 2

# Convert to ABSOLUTE screen coordinates
abs_cx = L + rel_cx
abs_cy = T + rel_cy
print(f"Match in window: ({rel_cx},{rel_cy}), confidence={max_val:.3f}")
print(f"Absolute click: ({abs_cx},{abs_cy})")

# Click
pyautogui.moveTo(abs_cx, abs_cy, duration=0.2)
time.sleep(0.3)
pyautogui.click()
print("CLICKED!")

time.sleep(4)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_final.png')
print("Done")
