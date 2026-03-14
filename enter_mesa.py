import pyautogui, time, ctypes, subprocess, cv2, numpy as np
pyautogui.FAILSAFE = False

user32 = ctypes.windll.user32
r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# Screenshot in pyautogui coordinates
pil = pyautogui.screenshot()
screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

# Find TODOS anchor again
todos_tmpl = cv2.imread(r'C:\Users\PC\Downloads\todos_tmpl.png')
result = cv2.matchTemplate(screen, todos_tmpl, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)
print(f"TODOS anchor: {max_val:.3f} at {max_loc}")

todos_x, todos_y = max_loc

# From the crop, "Starter HU(1)" first entry is about:
# y = 85px below TODOS (the first row of cash tables)
# x = 100px right of TODOS left edge (center of left card)
card_x = todos_x + 100
card_y = todos_y + 85

print(f"Clicking Starter HU(1) at ({card_x},{card_y})")

debug = screen.copy()
cv2.circle(debug, (card_x, card_y), 15, (0, 255, 0), 3)
cv2.imwrite(r'C:\Users\PC\Downloads\enter_debug.png', debug)

pyautogui.click(card_x, card_y)
print("CLICKED!")

time.sleep(5)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_enter.png')

# Crop window
DWMWA = 9
dwm_rect = (ctypes.c_long * 4)()
ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA, ctypes.byref(dwm_rect), ctypes.sizeof(dwm_rect))
L, T, R, B = dwm_rect[0], dwm_rect[1], dwm_rect[2], dwm_rect[3]
ascreen = cv2.cvtColor(np.array(after), cv2.COLOR_RGB2BGR)
win = ascreen[T:B, L:R]
cv2.imwrite(r'C:\Users\PC\Downloads\after_enter_win.png', win)
print("Done")
