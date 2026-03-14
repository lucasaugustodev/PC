"""Use pyautogui screenshot + opencv, but keep coordinates in pyautogui space."""
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

# Take screenshot using pyautogui - coordinates will match pyautogui.click()
pil_screen = pyautogui.screenshot()
screen = cv2.cvtColor(np.array(pil_screen), cv2.COLOR_RGB2BGR)

# Create a LARGE, DISTINCTIVE template from the current screen itself
# First, find the Suprema window in the screenshot
# The window has "Clube dos Vaqueiros" text which is unique

# Let me crop a larger area of the Mini+SPT card from reference
ref = cv2.imread(r'C:\Users\PC\Downloads\SELECIONARU MA MESA .png')
# The whole Mini+SPI card in reference: y=195-280, x=155-295
card_tmpl = ref[195:280, 155:295]
cv2.imwrite(r'C:\Users\PC\Downloads\card_big_tmpl.png', card_tmpl)
print(f"Card template: {card_tmpl.shape}")

result = cv2.matchTemplate(screen, card_tmpl, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)
h, w = card_tmpl.shape[:2]
cx = max_loc[0] + w // 2
cy = max_loc[1] + h // 2
print(f"Card match: {max_val:.3f} at ({cx},{cy})")

# Mark and verify
debug = screen.copy()
cv2.circle(debug, (cx, cy), 20, (0, 255, 0), 3)
cv2.rectangle(debug, max_loc, (max_loc[0]+w, max_loc[1]+h), (0, 255, 0), 2)
cv2.imwrite(r'C:\Users\PC\Downloads\smart_debug.png', debug)

if max_val > 0.5:
    print(f"Clicking at ({cx},{cy})")
    pyautogui.click(cx, cy)
    print("CLICKED!")
else:
    # Try the "Buy-in" + "10" text which is very distinctive
    # Use a different part of the reference
    buyin_tmpl = ref[230:260, 160:220]
    cv2.imwrite(r'C:\Users\PC\Downloads\buyin_tmpl.png', buyin_tmpl)
    result2 = cv2.matchTemplate(screen, buyin_tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val2, _, max_loc2 = cv2.minMaxLoc(result2)
    h2, w2 = buyin_tmpl.shape[:2]
    cx2 = max_loc2[0] + w2 // 2
    cy2 = max_loc2[1] + h2 // 2
    print(f"Buyin match: {max_val2:.3f} at ({cx2},{cy2})")
    pyautogui.click(cx2, cy2)
    print(f"CLICKED at ({cx2},{cy2})")

time.sleep(5)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_smart2.png')
# Crop window
DWMWA = 9
dwm_rect = (ctypes.c_long * 4)()
ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA, ctypes.byref(dwm_rect), ctypes.sizeof(dwm_rect))
L, T, R, B = dwm_rect[0], dwm_rect[1], dwm_rect[2], dwm_rect[3]
ascreen = cv2.cvtColor(np.array(after), cv2.COLOR_RGB2BGR)
win = ascreen[T:B, L:R]
cv2.imwrite(r'C:\Users\PC\Downloads\after_smart2_win.png', win)
print(f"DWM rect: ({L},{T}) -> ({R},{B})")
print("Done")
