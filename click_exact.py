import pyautogui, time, ctypes, subprocess, cv2
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

# Close browser first
pyautogui.hotkey('alt', 'F4')
time.sleep(1)

# Activate SupremaPoker
r = subprocess.run(['powershell', '-Command', 
    '(Get-Process -Name SupremaPoker).MainWindowHandle'], 
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(1.5)

# Fresh screenshot
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\fresh.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\fresh.png')

# Load reference and crop JUST the "FichasNet" text  
ref = cv2.imread(r'C:\Users\PC\Downloads\SELECIONAR CLUBE FICHAS NET.png')
# In reference image, "FichasNet" text is white on dark background
# Looking at reference: the text is around y=255-270, x=130-220
# Let me try a tight crop of just the word
text_tmpl = ref[252:270, 125:225]
cv2.imwrite(r'C:\Users\PC\Downloads\tmpl_fichas.png', text_tmpl)
print(f"Template: {text_tmpl.shape}")

# Find on screen
result = cv2.matchTemplate(screen, text_tmpl, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)
h, w = text_tmpl.shape[:2]
cx = max_loc[0] + w // 2
cy = max_loc[1] + h // 2
print(f"Match: {max_val:.3f} at top-left={max_loc}, center=({cx},{cy})")

if max_val > 0.6:
    # Move and click EXACTLY there
    pyautogui.moveTo(cx, cy, duration=0.2)
    time.sleep(0.3)
    
    # Verify mouse is over the right spot - take screenshot with cursor
    verify = pyautogui.screenshot()
    verify.save(r'C:\Users\PC\Downloads\verify_pos.png')
    
    pyautogui.click()
    print(f"CLICKED at ({cx},{cy})")
else:
    print("No good match!")

time.sleep(4)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_exact.png')
print("Done")
