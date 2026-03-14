"""Find and click FichasNet club in Suprema lobby."""
import pyautogui
import numpy as np
from PIL import Image
import time

pyautogui.FAILSAFE = False

# Take fresh screenshot
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\lobby_screen.png')

# Try to use the reference image to find FichasNet
# But first, let's try locateOnScreen with the reference screenshot
# We need to crop the FichasNet part from the reference image

# Alternative: use template matching with the reference
# Let's crop "FichasNet" text area from SELECIONAR CLUBE reference
ref = Image.open(r'C:\Users\PC\Downloads\SELECIONAR CLUBE FICHAS NET.png')
# In the reference, FichasNet is visible as a club entry
# Let's try to find it by looking for the text pattern on screen

# Simpler approach: look at the current lobby screenshot
# FichasNet should be one of the club entries visible
# Let's try to locate the reference club image on screen
import cv2

screen = cv2.imread(r'C:\Users\PC\Downloads\lobby_screen.png')
reference = cv2.imread(r'C:\Users\PC\Downloads\SELECIONAR CLUBE FICHAS NET.png')

# The reference shows the full club selection screen
# FichasNet entry would be a horizontal bar - let's crop just that part
# In the reference image, FichasNet appears around y=245-295
# Reference image is 407x700
ref_h, ref_w = reference.shape[:2]
print(f"Reference image: {ref_w}x{ref_h}")

# Crop the FichasNet club entry from reference (approximate area)
# It's around y=245 to y=295 in the 700-pixel-high reference
fichasnet_crop = reference[240:300, 30:380]
cv2.imwrite(r'C:\Users\PC\Downloads\fichasnet_template.png', fichasnet_crop)
print(f"Template size: {fichasnet_crop.shape}")

# Now search for this template on the current screen
result = cv2.matchTemplate(screen, fichasnet_crop, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
print(f"Best match: confidence={max_val:.3f} at {max_loc}")

if max_val > 0.5:
    # Click the center of the match
    h, w = fichasnet_crop.shape[:2]
    cx = max_loc[0] + w // 2
    cy = max_loc[1] + h // 2
    print(f"Clicking FichasNet at ({cx}, {cy})")
    pyautogui.click(cx, cy)
    print("CLICKED!")
else:
    print(f"Match confidence too low ({max_val:.3f}), trying alternative...")
    # Just list all matches above 0.3
    locs = np.where(result > 0.3)
    if len(locs[0]) > 0:
        print(f"Found {len(locs[0])} matches above 0.3")
        cy = int(np.mean(locs[0]))
        cx = int(np.mean(locs[1]))
        print(f"Average position: ({cx}, {cy})")
