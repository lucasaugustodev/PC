"""Smart clicker - uses OCR-like text finding to click buttons."""
import pyautogui
import time, sys

pyautogui.FAILSAFE = False

# Take screenshot and find the Login button
# First, let's just get the screen and look for the button
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\full_screen.png')

# Get window info
import subprocess
result = subprocess.run(
    ['powershell', '-Command', 
     'Get-Process -Name SupremaPoker -EA SilentlyContinue | Select-Object MainWindowHandle | Format-List'],
    capture_output=True, text=True
)
print(f"Process info: {result.stdout.strip()}")

# Try locating by color - the Login button is a bordered/outlined button
# Let's use pyautogui's pixel color scanning
# The Login button has a golden/orange border on dark background

# Alternative: just use pyautogui to locate text on screen
# For now, let's try clicking using pyautogui which handles DPI correctly
# The key insight: pyautogui handles DPI scaling automatically!

# From our window rect: Left=278, Top=111, Width=421, Height=759
# Reference image Login button at roughly 80% from left, 52% from top of client area
# But let's be smarter - scan for the button color

from PIL import Image
import numpy as np

screen = np.array(img)
# The Login button border is golden/orange - RGB roughly (200-255, 150-200, 0-80)
# Let's find it
mask = (screen[:,:,0] > 180) & (screen[:,:,1] > 120) & (screen[:,:,1] < 210) & (screen[:,:,2] < 80)

# Find clusters of golden pixels (the Login button border)
coords = np.where(mask)
if len(coords[0]) > 0:
    # Get bounding box of golden pixels in the right area (where Suprema window is)
    # Filter to window area: x between 278 and 699
    valid = (coords[1] >= 278) & (coords[1] <= 699) & (coords[0] >= 111) & (coords[0] <= 870)
    if valid.any():
        ys = coords[0][valid]
        xs = coords[1][valid]
        # The Login button should be a small cluster, find the rightmost cluster
        # around y=400-550
        btn_mask = (ys > 400) & (ys < 600)
        if btn_mask.any():
            btn_ys = ys[btn_mask]
            btn_xs = xs[btn_mask]
            center_x = int(np.mean(btn_xs))
            center_y = int(np.mean(btn_ys))
            print(f"Found Login button area at ({center_x}, {center_y})")
            print(f"  X range: {btn_xs.min()}-{btn_xs.max()}")
            print(f"  Y range: {btn_ys.min()}-{btn_ys.max()}")
            
            # Click it!
            pyautogui.click(center_x, center_y)
            print(f"CLICKED at ({center_x}, {center_y})")
        else:
            print(f"No golden pixels in button Y range. Y range found: {ys.min()}-{ys.max()}")
            # Try the whole golden area
            center_x = int(np.mean(xs))
            center_y = int(np.mean(ys))
            print(f"Golden pixel center: ({center_x}, {center_y})")
    else:
        print("No golden pixels in window area")
else:
    print("No golden pixels found on screen")
