import pyautogui, time, ctypes, subprocess, cv2, numpy as np
pyautogui.FAILSAFE = False

# Press Escape to close notification
pyautogui.press('escape')
time.sleep(1)

user32 = ctypes.windll.user32
r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(1)

# Screenshot
pil = pyautogui.screenshot()
pil.save(r'C:\Users\PC\Downloads\state_now.png')
screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

# Get DWM rect
DWMWA = 9
dwm_rect = (ctypes.c_long * 4)()
ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA, ctypes.byref(dwm_rect), ctypes.sizeof(dwm_rect))
L, T, R, B = dwm_rect[0], dwm_rect[1], dwm_rect[2], dwm_rect[3]
win = screen[T:B, L:R]
cv2.imwrite(r'C:\Users\PC\Downloads\state_win.png', win)
print("State captured")
