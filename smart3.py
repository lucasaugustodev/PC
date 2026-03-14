"""Approach: find window by unique text, then click relative to that anchor."""
import pyautogui, time, ctypes, subprocess, cv2, numpy as np
from PIL import Image
pyautogui.FAILSAFE = False

user32 = ctypes.windll.user32
r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(1)

# Take pyautogui screenshot - ALL coordinates will be in pyautogui space
pil = pyautogui.screenshot()
screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

# Find "TODOS" tab text as anchor - it's unique and always visible above cards
# Crop from current window crop we already have
win_crop = cv2.imread(r'C:\Users\PC\Downloads\win_mesas.png')
# "TODOS" tab in the crop is at approximately y=197-215, x=10-60
todos_tmpl = win_crop[197:215, 10:65]
cv2.imwrite(r'C:\Users\PC\Downloads\todos_tmpl.png', todos_tmpl)

# Find TODOS on full pyautogui screenshot
result = cv2.matchTemplate(screen, todos_tmpl, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)
print(f"TODOS anchor: {max_val:.3f} at {max_loc}")

if max_val > 0.8:
    # TODOS tab position found. In the window crop:
    # TODOS is at y=206, Mini+SPT card center is at approximately y=320
    # So card center is about 114px below TODOS
    # And Mini+SPT (LEFT card) center x is about 100px from window left
    # TODOS left edge is at x=10, so card center x is about 90px to the right of TODOS
    
    todos_x = max_loc[0]
    todos_y = max_loc[1]
    
    # Card center relative to TODOS anchor
    card_x = todos_x + 90   # 90px right of TODOS left edge
    card_y = todos_y + 114   # 114px below TODOS
    
    print(f"TODOS at ({todos_x},{todos_y})")
    print(f"Card target: ({card_x},{card_y})")
    
    # Draw debug
    debug = screen.copy()
    cv2.circle(debug, (card_x, card_y), 15, (0, 255, 0), 3)
    cv2.putText(debug, "TARGET", (card_x+20, card_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
    cv2.circle(debug, (todos_x+27, todos_y+9), 10, (255, 0, 0), 2)
    cv2.putText(debug, "ANCHOR", (todos_x+40, todos_y+9), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)
    cv2.imwrite(r'C:\Users\PC\Downloads\smart3_debug.png', debug)
    
    # Click!
    pyautogui.click(card_x, card_y)
    print(f"CLICKED at ({card_x},{card_y})")
else:
    print("TODOS not found!")

time.sleep(5)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_smart3.png')
print("Done")
