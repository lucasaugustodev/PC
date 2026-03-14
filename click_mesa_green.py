import pyautogui, time, ctypes, subprocess, cv2, numpy as np
pyautogui.FAILSAFE = False

user32 = ctypes.windll.user32
r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# Click mesa #1 directly - the one at (484, 535)
print("Clicking green mesa at (484, 535)")
pyautogui.click(484, 535)
print("CLICKED!")

time.sleep(5)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_mesa_green.png')
DWMWA = 9
dwm_rect = (ctypes.c_long * 4)()
ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA, ctypes.byref(dwm_rect), ctypes.sizeof(dwm_rect))
L, T, R, B = dwm_rect[0], dwm_rect[1], dwm_rect[2], dwm_rect[3]
ascreen = cv2.cvtColor(np.array(after), cv2.COLOR_RGB2BGR)
win = ascreen[T:B, L:R]
cv2.imwrite(r'C:\Users\PC\Downloads\after_mesa_green_win.png', win)
print("Done")
