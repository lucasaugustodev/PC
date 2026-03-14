"""Navigate out and back into a table to capture client requests."""
import pyautogui, time, ctypes, subprocess, cv2, numpy as np
pyautogui.FAILSAFE = False

user32 = ctypes.windll.user32
r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(1)

# Screenshot to see current state
pil = pyautogui.screenshot()
screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

# Get DWM rect for window position
DWMWA = 9
dwm_rect = (ctypes.c_long * 4)()
ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA, ctypes.byref(dwm_rect), ctypes.sizeof(dwm_rect))
L, T, R, B = dwm_rect[0], dwm_rect[1], dwm_rect[2], dwm_rect[3]
win = screen[T:B, L:R]
cv2.imwrite(r'C:\Users\PC\Downloads\nav_state.png', win)
print(f"Window at ({L},{T})-({R},{B})")

# Find the back arrow (<-) to exit the table
# The back arrow is in the top-left of the window, around y=55, x=30
# Use anchor-based approach: find "TODOS" or back arrow

# First check if we're in a table or in the list
# In table view there's no "TODOS" tab
todos_tmpl = cv2.imread(r'C:\Users\PC\Downloads\todos_tmpl.png')
result = cv2.matchTemplate(screen, todos_tmpl, cv2.TM_CCOEFF_NORMED)
_, max_val, _, _ = cv2.minMaxLoc(result)
print(f"TODOS match: {max_val:.3f}")

if max_val < 0.7:
    # We're in a table view - need to click back arrow
    # Back arrow is a "<" icon at top-left of window
    # In the table view, it's approximately at x=25, y=55 from window top
    back_x = L + 25
    back_y = T + 55
    print(f"In table view. Clicking back at ({back_x},{back_y})")
    pyautogui.click(back_x, back_y)
    time.sleep(3)
    
    # Check state again
    pil2 = pyautogui.screenshot()
    screen2 = cv2.cvtColor(np.array(pil2), cv2.COLOR_RGB2BGR)
    win2 = screen2[T:B, L:R]
    cv2.imwrite(r'C:\Users\PC\Downloads\after_back.png', win2)
    
    result2 = cv2.matchTemplate(screen2, todos_tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val2, _, max_loc2 = cv2.minMaxLoc(result2)
    print(f"TODOS match after back: {max_val2:.3f}")
    
    if max_val2 > 0.7:
        print("Back to table list!")
        # Now find green mesa and click it
        hsv = cv2.cvtColor(screen2, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        coords = np.where(mask > 0)
        ys, xs = coords[0], coords[1]
        win_mask = (xs >= 250) & (xs <= 720)
        ys, xs = ys[win_mask], xs[win_mask]
        
        # Find big green clusters
        unique_ys = np.unique(ys)
        clusters = []
        current = [unique_ys[0]]
        for i in range(1, len(unique_ys)):
            if unique_ys[i] - unique_ys[i-1] <= 5:
                current.append(unique_ys[i])
            else:
                if len(current) >= 20:
                    clusters.append(current)
                current = [unique_ys[i]]
        if len(current) >= 20:
            clusters.append(current)
        
        print(f"Found {len(clusters)} green mesas")
        for i, c in enumerate(clusters):
            cy = int(np.mean(c))
            cmask = (ys >= c[0]) & (ys <= c[-1])
            cx = int(np.mean(xs[cmask]))
            print(f"  Mesa {i}: ({cx},{cy})")
        
        # Click first green mesa
        if clusters:
            c = clusters[0]
            cy = int(np.mean(c))
            cmask = (ys >= c[0]) & (ys <= c[-1])
            cx = int(np.mean(xs[cmask]))
            print(f"Clicking mesa at ({cx},{cy})")
            pyautogui.click(cx, cy)
            print("CLICKED MESA!")
            time.sleep(5)
            
            # Final screenshot
            pil3 = pyautogui.screenshot()
            screen3 = cv2.cvtColor(np.array(pil3), cv2.COLOR_RGB2BGR)
            win3 = screen3[T:B, L:R]
            cv2.imwrite(r'C:\Users\PC\Downloads\after_enter_mesa.png', win3)
            print("Done - check spy log for captured requests!")
else:
    print("Already in table list!")
    # Find and click green mesa
    hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    coords = np.where(mask > 0)
    ys, xs = coords[0], coords[1]
    win_mask = (xs >= 250) & (xs <= 720)
    ys, xs = ys[win_mask], xs[win_mask]
    unique_ys = np.unique(ys)
    clusters = []
    current = [unique_ys[0]]
    for i in range(1, len(unique_ys)):
        if unique_ys[i] - unique_ys[i-1] <= 5:
            current.append(unique_ys[i])
        else:
            if len(current) >= 20:
                clusters.append(current)
            current = [unique_ys[i]]
    if len(current) >= 20:
        clusters.append(current)
    
    if clusters:
        c = clusters[0]
        cy = int(np.mean(c))
        cmask = (ys >= c[0]) & (ys <= c[-1])
        cx = int(np.mean(xs[cmask]))
        print(f"Clicking mesa at ({cx},{cy})")
        pyautogui.click(cx, cy)
        time.sleep(5)
        pil3 = pyautogui.screenshot()
        screen3 = cv2.cvtColor(np.array(pil3), cv2.COLOR_RGB2BGR)
        win3 = screen3[T:B, L:R]
        cv2.imwrite(r'C:\Users\PC\Downloads\after_enter_mesa.png', win3)
        print("Done!")
