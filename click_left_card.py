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

# From the debug_win_marked.png I can see the Mini+SPT card is the LEFT card
# It's at approximately x=10-200, y=260-380 in window coords
# Center of the card: x=105, y=320
# But SCP Plus (RIGHT card) is at x=210-410, y=260-380

# The "Mini+SPT" text specifically is at about:
# x=50-150, y=275-295 in window coords

# Let me click the center of the LEFT card text area
rel_x = 100
rel_y = 285
abs_x = L + rel_x
abs_y = T + rel_y

# Draw debug circle first
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\pre_click.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\pre_click.png')
win = screen[T:rect.bottom, L:rect.right]
cv2.circle(win, (rel_x, rel_y), 10, (0, 255, 0), 2)
cv2.imwrite(r'C:\Users\PC\Downloads\click_target.png', win)

print(f"Clicking LEFT card Mini+SPT at abs ({abs_x},{abs_y}), rel ({rel_x},{rel_y})")
pyautogui.moveTo(abs_x, abs_y, duration=0.2)
time.sleep(0.3)
pyautogui.click()
print("CLICKED!")

time.sleep(5)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_left.png')
ascreen = cv2.imread(r'C:\Users\PC\Downloads\after_left.png')
awin = ascreen[T:rect.bottom, L:rect.right]
cv2.imwrite(r'C:\Users\PC\Downloads\after_left_win.png', awin)
print("Done")
