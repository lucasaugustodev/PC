import pyautogui, time, ctypes, subprocess, cv2, numpy as np
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

# Close ALL browser windows
import os
os.system('taskkill /F /FI "WINDOWTITLE eq *raw.githack*" 2>nul')
os.system('taskkill /F /FI "WINDOWTITLE eq *Suprema Poker*" 2>nul')
os.system('taskkill /F /FI "WINDOWTITLE eq *One more*" 2>nul')
time.sleep(1)

# Close any remaining browser by pressing Alt+F4 a few times
for _ in range(3):
    pyautogui.hotkey('alt', 'F4')
    time.sleep(0.5)

# Activate SupremaPoker
r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker -EA SilentlyContinue | Select-Object -First 1).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip()) if r.stdout.strip() and r.stdout.strip() != '0' else None
if hwnd:
    user32.ShowWindow(hwnd, 9)
    time.sleep(0.3)
    user32.SetForegroundWindow(hwnd)
    time.sleep(1)
    print(f"SupremaPoker activated (hwnd={hwnd})")
else:
    print("No SupremaPoker!")
    exit()

# Screenshot and check state
pil = pyautogui.screenshot()
screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

# Check if login screen (golden pixels)
mask = (screen[:,:,2] > 180) & (screen[:,:,1] > 120) & (screen[:,:,1] < 210) & (screen[:,:,0] < 80)
golden_count = np.sum(mask)
print(f"Golden pixels: {golden_count}")

# Check for TODOS tab
todos_tmpl = cv2.imread(r'C:\Users\PC\Downloads\todos_tmpl.png')
result = cv2.matchTemplate(screen, todos_tmpl, cv2.TM_CCOEFF_NORMED)
_, todos_val, _, _ = cv2.minMaxLoc(result)
print(f"TODOS match: {todos_val:.3f}")

# Save current window crop  
DWMWA = 9
dwm_rect = (ctypes.c_long * 4)()
ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA, ctypes.byref(dwm_rect), ctypes.sizeof(dwm_rect))
L, T, R, B = dwm_rect[0], dwm_rect[1], dwm_rect[2], dwm_rect[3]
win = screen[T:B, L:R]
cv2.imwrite(r'C:\Users\PC\Downloads\current_state.png', win)
print(f"Window at ({L},{T}), saved state")

if golden_count > 500 and todos_val < 0.7:
    # Login screen - click Login
    coords = np.where(mask)
    ys, xs = coords[0], coords[1]
    btn_mask = (ys > 400) & (ys < 600)
    if btn_mask.any():
        cy = int(np.mean(ys[btn_mask]))
        cx = int(np.mean(xs[btn_mask]))
        print(f"Clicking Login at ({cx},{cy})")
        pyautogui.click(cx, cy)
        time.sleep(8)
        pil = pyautogui.screenshot()
        screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        win = screen[T:B, L:R]
        cv2.imwrite(r'C:\Users\PC\Downloads\after_login.png', win)

# Check for FichasNet
ref_club = cv2.imread(r'C:\Users\PC\Downloads\SELECIONAR CLUBE FICHAS NET.png')
if ref_club is not None:
    text_tmpl = ref_club[252:270, 125:225]
    result = cv2.matchTemplate(screen, text_tmpl, cv2.TM_CCOEFF_NORMED)
    _, fval, _, floc = cv2.minMaxLoc(result)
    if fval > 0.7:
        h, w = text_tmpl.shape[:2]
        cx = floc[0] + w // 2
        cy = floc[1] + h // 2
        print(f"FichasNet at ({cx},{cy}), clicking...")
        pyautogui.click(cx, cy)
        time.sleep(5)
        pil = pyautogui.screenshot()
        screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

# Check for TODOS (table list)
result = cv2.matchTemplate(screen, todos_tmpl, cv2.TM_CCOEFF_NORMED)
_, tval, _, tloc = cv2.minMaxLoc(result)
if tval > 0.7:
    print(f"Table list! TODOS at {tloc}")
    # Click NLH tab
    nlh_x = tloc[0] + 80
    nlh_y = tloc[1] + 9
    pyautogui.click(nlh_x, nlh_y)
    time.sleep(2)
    pil = pyautogui.screenshot()
    screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    
    # Find green mesas
    hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
    gmask = cv2.inRange(hsv, np.array([35,40,40]), np.array([85,255,255]))
    gcoords = np.where(gmask > 0)
    gys, gxs = gcoords[0], gcoords[1]
    win_mask = (gxs >= L) & (gxs <= R)
    gys, gxs = gys[win_mask], gxs[win_mask]
    
    if len(gys) > 0:
        unique_ys = np.unique(gys)
        clusters = []
        current = [unique_ys[0]]
        for i in range(1, len(unique_ys)):
            if unique_ys[i] - unique_ys[i-1] <= 5:
                current.append(unique_ys[i])
            else:
                if len(current) >= 20:
                    cy = int(np.mean(current))
                    cmask = (gys >= current[0]) & (gys <= current[-1])
                    cx = int(np.mean(gxs[cmask]))
                    clusters.append((cx, cy))
                current = [unique_ys[i]]
        if len(current) >= 20:
            cy = int(np.mean(current))
            cmask = (gys >= current[0]) & (gys <= current[-1])
            cx = int(np.mean(gxs[cmask]))
            clusters.append((cx, cy))
        
        print(f"Green mesas: {len(clusters)}")
        for i, (cx, cy) in enumerate(clusters):
            print(f"  Mesa {i}: ({cx},{cy})")
        
        if clusters:
            cx, cy = clusters[0]
            print(f"Clicking first mesa at ({cx},{cy})")
            pyautogui.click(cx, cy)
            time.sleep(5)

# Final state
pil = pyautogui.screenshot()
screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
win = screen[T:B, L:R]
cv2.imwrite(r'C:\Users\PC\Downloads\final_state.png', win)
print("Done!")
