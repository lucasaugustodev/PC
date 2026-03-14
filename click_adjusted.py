import pyautogui, time, ctypes, subprocess, cv2
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# Get window rect WITH and WITHOUT extended frame
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

# Standard GetWindowRect (includes shadow)
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"GetWindowRect: ({rect.left},{rect.top}) -> ({rect.right},{rect.bottom})")

# DwmGetWindowAttribute to get rect WITHOUT shadow
import ctypes.wintypes
dwm_rect = RECT()
DWMWA_EXTENDED_FRAME_BOUNDS = 9
ctypes.windll.dwmapi.DwmGetWindowAttribute(
    hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, 
    ctypes.byref(dwm_rect), ctypes.sizeof(dwm_rect))
print(f"DwmExtendedFrame: ({dwm_rect.left},{dwm_rect.top}) -> ({dwm_rect.right},{dwm_rect.bottom})")

# The REAL window position (without shadow)
L, T = dwm_rect.left, dwm_rect.top
R, B = dwm_rect.right, dwm_rect.bottom
print(f"Real window: ({L},{T}), size {R-L}x{B-T}")
print(f"Shadow offset: left={dwm_rect.left-rect.left}, top={dwm_rect.top-rect.top}")

# Now click Mini+SPT card center using REAL coordinates
# From crop image: card center at rel (150, 330)
abs_x = L + 150
abs_y = T + 330
print(f"Clicking at ({abs_x},{abs_y})")
pyautogui.moveTo(abs_x, abs_y, duration=0.2)
time.sleep(0.5)
pyautogui.click()
print("CLICKED!")

time.sleep(5)
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\after_adjusted.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\after_adjusted.png')
win = screen[T:B, L:R]
cv2.imwrite(r'C:\Users\PC\Downloads\after_adj_win.png', win)
print("Done")
