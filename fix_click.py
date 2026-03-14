import pyautogui, time, ctypes, subprocess
from ctypes import wintypes

pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

# Activate SupremaPoker
r = subprocess.run(['powershell', '-Command', 
    '(Get-Process -Name SupremaPoker).MainWindowHandle'], 
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(1)

# Get ACTUAL window rect after activation
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), 
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"Window: left={rect.left} top={rect.top} right={rect.right} bottom={rect.bottom}")
print(f"Size: {rect.right-rect.left}x{rect.bottom-rect.top}")

# Screenshot to see current state
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\before_click.png')

# Now use template matching on FRESH screenshot with FRESH window position
import cv2
screen = cv2.imread(r'C:\Users\PC\Downloads\before_click.png')

# Crop window area
win = screen[rect.top:rect.bottom, rect.left:rect.right]
cv2.imwrite(r'C:\Users\PC\Downloads\win_now.png', win)
print(f"Window crop: {win.shape}")

# In the window crop, FichasNet is around y=175-210
# Click center of FichasNet entry
# Use SendMessage instead of mouse_event for accuracy
import win32gui, win32con, win32api

# Click relative to window using PostMessage
# FichasNet in crop: x~200, y~190
click_x = 200
click_y = 190
lParam = win32api.MAKELONG(click_x, click_y)

print(f"Sending click to window at relative ({click_x}, {click_y})")
win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
time.sleep(0.1)
win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
print("Message sent!")

time.sleep(3)
img2 = pyautogui.screenshot()
img2.save(r'C:\Users\PC\Downloads\after_msg_click.png')
print("Done")
