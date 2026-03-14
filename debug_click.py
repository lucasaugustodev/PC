import pyautogui, time, ctypes, subprocess, cv2, numpy as np
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(1)

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
L, T, R, B = rect.left, rect.top, rect.right, rect.bottom

# Screenshot
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\debug.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\debug.png')

# Crop window
win = screen[T:B, L:R]

# Template match "Mini+SPT" in the WINDOW crop
ref = cv2.imread(r'C:\Users\PC\Downloads\SELECIONARU MA MESA .png')
mini_tmpl = ref[215:240, 165:260]

result = cv2.matchTemplate(win, mini_tmpl, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)
h, w = mini_tmpl.shape[:2]
rel_cx = max_loc[0] + w // 2
rel_cy = max_loc[1] + h // 2
abs_cx = L + rel_cx
abs_cy = T + rel_cy

print(f"Window: ({L},{T}) -> ({R},{B})")
print(f"Match in window crop: ({rel_cx},{rel_cy}), confidence={max_val:.3f}")
print(f"Absolute: ({abs_cx},{abs_cy})")

# Draw circle on the screenshot to show where click would land
debug_img = screen.copy()
cv2.circle(debug_img, (abs_cx, abs_cy), 15, (0, 0, 255), 3)
cv2.putText(debug_img, f"CLICK HERE ({abs_cx},{abs_cy})", (abs_cx+20, abs_cy), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

# Also draw on window crop
win_debug = win.copy()
cv2.circle(win_debug, (rel_cx, rel_cy), 15, (0, 0, 255), 3)
cv2.imwrite(r'C:\Users\PC\Downloads\debug_marked.png', debug_img)
cv2.imwrite(r'C:\Users\PC\Downloads\debug_win_marked.png', win_debug)
print("Debug images saved")

# Also get mouse position right now
mx, my = pyautogui.position()
print(f"Current mouse: ({mx},{my})")
