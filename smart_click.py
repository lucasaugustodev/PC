"""Smart clicker using pyautogui.locateOnScreen - no manual coordinate math."""
import pyautogui, time, ctypes, subprocess, cv2, sys
pyautogui.FAILSAFE = False

user32 = ctypes.windll.user32
r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(1)

# Step 1: Take a screenshot and crop a TINY unique piece from the card we want
# Use the CURRENT screen to create the template (not the reference image)
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\current.png')

# Step 2: Use locateOnScreen with the reference
# First, let me crop "Mini+SPT" text from the CURRENT screenshot
# by finding it via the window crop
screen = cv2.imread(r'C:\Users\PC\Downloads\current.png')

# Find the text "Mini" in the current screenshot by color/pattern
# The cards have distinctive "Buy-in" + number pattern
# Let me create templates from the current screen

# Use locateAllOnScreen with confidence parameter
# First save a small template of the "Mini+SPT" text from current screen
# I know from the window crop that this text is in the Suprema window

# Actually, the SIMPLEST smart approach: 
# Use pyautogui.locateCenterOnScreen with the reference template
from PIL import Image
ref = Image.open(r'C:\Users\PC\Downloads\SELECIONARU MA MESA .png')

# Crop just "Mini" text from reference - very small, distinctive
# In reference: Mini+SPI text at approximately y=218-232, x=173-215
mini_text = ref.crop((173, 218, 240, 235))
mini_text.save(r'C:\Users\PC\Downloads\mini_text_tmpl.png')
print(f"Template size: {mini_text.size}")

# Use locateCenterOnScreen - this handles EVERYTHING
try:
    pos = pyautogui.locateCenterOnScreen(r'C:\Users\PC\Downloads\mini_text_tmpl.png', confidence=0.7)
    if pos:
        print(f"Found at: {pos}")
        pyautogui.click(pos)
        print("CLICKED!")
    else:
        print("Not found with locateCenterOnScreen")
except Exception as e:
    print(f"Error: {e}")
    # Fallback: manual locate with opencv but use pyautogui coordinates
    print("Trying manual opencv match...")
    
    import numpy as np
    template = cv2.imread(r'C:\Users\PC\Downloads\mini_text_tmpl.png')
    
    # Take screenshot via pyautogui (coordinates match pyautogui.click)
    pil_screen = pyautogui.screenshot()
    screen_arr = cv2.cvtColor(np.array(pil_screen), cv2.COLOR_RGB2BGR)
    
    result = cv2.matchTemplate(screen_arr, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    h, w = template.shape[:2]
    cx = max_loc[0] + w // 2
    cy = max_loc[1] + h // 2
    print(f"OpenCV match: {max_val:.3f} at ({cx},{cy})")
    
    # These coordinates should DIRECTLY work with pyautogui
    # because the screenshot was taken by pyautogui
    pyautogui.click(cx, cy)
    print(f"CLICKED at ({cx},{cy})")

time.sleep(5)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_smart.png')
print("Done")
