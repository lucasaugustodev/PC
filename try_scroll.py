import pyautogui, time, ctypes, subprocess, cv2
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

# Move mouse to center of window and scroll down
center_x = L + 210
center_y = T + 450
pyautogui.moveTo(center_x, center_y)
time.sleep(0.3)

# Scroll down
pyautogui.scroll(-5)
time.sleep(2)

# Screenshot
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\scrolled.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\scrolled.png')
win = screen[T:rect.bottom, L:rect.right]
cv2.imwrite(r'C:\Users\PC\Downloads\scrolled_win.png', win)
print("Scrolled down, check screenshot")
