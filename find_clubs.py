"""Analyze current lobby to find clickable clubs."""
import pyautogui
import numpy as np
from PIL import Image
import cv2

pyautogui.FAILSAFE = False

# Fresh screenshot
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\lobby_now.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\lobby_now.png')

# Let's look at the actual lobby screen more carefully
# Crop just the Suprema window area (Left=278, Top=111, Width=421, Height=759)
window = screen[111:870, 278:699]
cv2.imwrite(r'C:\Users\PC\Downloads\window_crop.png', window)
print(f"Window crop: {window.shape}")

# The lobby shows clubs as entries. Let's look for "FichasNet" text
# by trying to find it via template from the reference
ref = cv2.imread(r'C:\Users\PC\Downloads\SELECIONAR CLUBE FICHAS NET.png')

# Let's try smaller templates - just the "FichasNet" text
# In the reference, the text "FichasNet" is around x=110-220, y=250-270
text_crop = ref[248:272, 100:230]
cv2.imwrite(r'C:\Users\PC\Downloads\fichasnet_text.png', text_crop)
print(f"Text template: {text_crop.shape}")

# Search on full screen
result = cv2.matchTemplate(screen, text_crop, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
print(f"Text match: confidence={max_val:.3f} at {max_loc}")

# Also try the club icon+text area - a narrower horizontal strip
club_strip = ref[240:300, 50:350]
cv2.imwrite(r'C:\Users\PC\Downloads\club_strip.png', club_strip)
result2 = cv2.matchTemplate(screen, club_strip, cv2.TM_CCOEFF_NORMED)
min_val2, max_val2, min_loc2, max_loc2 = cv2.minMaxLoc(result2)
print(f"Strip match: confidence={max_val2:.3f} at {max_loc2}")

# Try matching on the window crop instead
result3 = cv2.matchTemplate(window, text_crop, cv2.TM_CCOEFF_NORMED)
min_val3, max_val3, min_loc3, max_loc3 = cv2.minMaxLoc(result3)
print(f"Window text match: confidence={max_val3:.3f} at {max_loc3}")

# Click the best match
if max_val > 0.5:
    h, w = text_crop.shape[:2]
    cx = max_loc[0] + w // 2
    cy = max_loc[1] + h // 2
    print(f"Clicking text match at ({cx}, {cy})")
    pyautogui.click(cx, cy)
    print("CLICKED!")
elif max_val2 > 0.5:
    h, w = club_strip.shape[:2]
    cx = max_loc2[0] + w // 2
    cy = max_loc2[1] + h // 2
    print(f"Clicking strip match at ({cx}, {cy})")
    pyautogui.click(cx, cy)
    print("CLICKED!")
else:
    print("No good match found. Let me check what's on screen...")
    # Maybe we need to scroll or the layout is different
    # Let's check the window crop
