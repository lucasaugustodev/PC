import pyautogui, time, ctypes, subprocess, cv2, numpy as np
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

# Activate window
r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(1)

# Fresh screenshot
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\screen_mesa.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\screen_mesa.png')

# Load reference mesa image
ref = cv2.imread(r'C:\Users\PC\Downloads\SELECIONARU MA MESA .png')
print(f"Reference: {ref.shape}")

# Crop the "Mini" text from reference - this is a small distinctive text
# In reference, "Mini + SPI" text is around y=218-235, x=170-250
mini_tmpl = ref[215:240, 165:260]
cv2.imwrite(r'C:\Users\PC\Downloads\mini_tmpl.png', mini_tmpl)
print(f"Mini template: {mini_tmpl.shape}")

# Search on screen
result = cv2.matchTemplate(screen, mini_tmpl, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)
h, w = mini_tmpl.shape[:2]
cx = max_loc[0] + w // 2
cy = max_loc[1] + h // 2
print(f"Mini match: {max_val:.3f} at center ({cx},{cy})")

if max_val > 0.5:
    pyautogui.moveTo(cx, cy, duration=0.2)
    time.sleep(0.3)
    pyautogui.click()
    print(f"CLICKED at ({cx},{cy})")
else:
    # Try broader search - the "Buy-in" text or number "10"
    # Or try the whole card area
    print("Mini text not found. Trying card area...")
    card_tmpl = ref[190:280, 155:300]
    cv2.imwrite(r'C:\Users\PC\Downloads\card_tmpl.png', card_tmpl)
    result2 = cv2.matchTemplate(screen, card_tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val2, _, max_loc2 = cv2.minMaxLoc(result2)
    h2, w2 = card_tmpl.shape[:2]
    cx2 = max_loc2[0] + w2 // 2
    cy2 = max_loc2[1] + h2 // 2
    print(f"Card match: {max_val2:.3f} at center ({cx2},{cy2})")
    if max_val2 > 0.4:
        pyautogui.moveTo(cx2, cy2, duration=0.2)
        time.sleep(0.3)
        pyautogui.click()
        print(f"CLICKED at ({cx2},{cy2})")

time.sleep(5)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_mesa_tmpl.png')

# Also crop window
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
ascreen = cv2.imread(r'C:\Users\PC\Downloads\after_mesa_tmpl.png')
win = ascreen[rect.top:rect.bottom, rect.left:rect.right]
cv2.imwrite(r'C:\Users\PC\Downloads\after_mesa_win.png', win)
print("Done")
