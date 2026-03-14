import pyautogui, cv2, ctypes, subprocess
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))

img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\full_now.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\full_now.png')
win = screen[rect.top:rect.bottom, rect.left:rect.right]
cv2.imwrite(r'C:\Users\PC\Downloads\win_mesas.png', win)
print(f"Window at ({rect.left},{rect.top}), crop saved")
