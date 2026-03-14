import pyautogui, time
pyautogui.FAILSAFE = False

# From window crop analysis:
# Window: Left=278, Top=111
# FichasNet entry in crop: approximately y=175-210, x=50-350
# Absolute: x=278+200=478, y=111+190=301

# First activate the window
import ctypes
from ctypes import wintypes
user32 = ctypes.windll.user32

# Find SupremaPoker window
import subprocess
r = subprocess.run(['powershell', '-Command', 
    '(Get-Process -Name SupremaPoker).MainWindowHandle'], 
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
print(f"Window handle: {hwnd}")

# Activate it
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# Click on FichasNet - in the crop it's around y=185 from window top, x=200 from window left
# Let me click at multiple vertical positions to find the right one
# FichasNet text is at about y=180 in the crop
target_x = 278 + 150  # 428 - center-left of the entry
target_y = 111 + 185  # 296

print(f"Clicking at ({target_x}, {target_y})")
pyautogui.click(target_x, target_y)
time.sleep(0.3)
print("Single click done")

# Take screenshot to verify
time.sleep(2)
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\after_fichas_click.png')
print("Screenshot saved")
