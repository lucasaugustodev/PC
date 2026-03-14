import pyautogui, time, ctypes, subprocess
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
L, T = rect.left, rect.top

# Position E: rel (150, 330) = center of Mini+SPT card
abs_x = L + 150
abs_y = T + 330
print(f"Moving to ({abs_x},{abs_y})")

# Move mouse and WAIT - don't click yet, just screenshot to verify position
pyautogui.moveTo(abs_x, abs_y, duration=0.3)
time.sleep(1)

# Screenshot with cursor visible
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\cursor_pos.png')

# NOW click
pyautogui.click()
print(f"CLICKED at ({abs_x},{abs_y})")

time.sleep(5)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_e.png')
import cv2
ascreen = cv2.imread(r'C:\Users\PC\Downloads\after_e.png')
awin = ascreen[T:rect.bottom, L:rect.right]
cv2.imwrite(r'C:\Users\PC\Downloads\after_e_win.png', awin)
print("Done")
