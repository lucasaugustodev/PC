"""Full automation: login -> club -> table, then launch spy."""
import pyautogui, time, ctypes, subprocess, cv2, numpy as np
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

def get_hwnd():
    r = subprocess.run(['powershell', '-Command',
        '(Get-Process -Name SupremaPoker -EA SilentlyContinue).MainWindowHandle'],
        capture_output=True, text=True)
    h = r.stdout.strip()
    lines = [l.strip() for l in h.strip().splitlines() if l.strip() and l.strip() != "0"]; return int(lines[0]) if lines else None

def activate():
    hwnd = get_hwnd()
    if hwnd:
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.5)
    return hwnd

def screenshot():
    pil = pyautogui.screenshot()
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

def find_green_mesas(screen):
    hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([35,40,40]), np.array([85,255,255]))
    coords = np.where(mask > 0)
    ys, xs = coords[0], coords[1]
    win_mask = (xs >= 250) & (xs <= 720)
    ys, xs = ys[win_mask], xs[win_mask]
    if len(ys) == 0: return []
    unique_ys = np.unique(ys)
    clusters = []
    current = [unique_ys[0]]
    for i in range(1, len(unique_ys)):
        if unique_ys[i] - unique_ys[i-1] <= 5:
            current.append(unique_ys[i])
        else:
            if len(current) >= 20:
                cy = int(np.mean(current))
                cmask = (ys >= current[0]) & (ys <= current[-1])
                cx = int(np.mean(xs[cmask]))
                clusters.append((cx, cy))
            current = [unique_ys[i]]
    if len(current) >= 20:
        cy = int(np.mean(current))
        cmask = (ys >= current[0]) & (ys <= current[-1])
        cx = int(np.mean(xs[cmask]))
        clusters.append((cx, cy))
    return clusters

# Step 0: Close browser popups
pyautogui.hotkey('alt', 'F4')
time.sleep(1)

# Step 1: Activate SupremaPoker and check state
print("Step 1: Activating SupremaPoker...")
hwnd = activate()
if not hwnd:
    print("SupremaPoker not found! Waiting...")
    time.sleep(10)
    hwnd = activate()

time.sleep(1)
screen = screenshot()

# Check for Login button using golden color detection (worked before)
mask = (screen[:,:,2] > 180) & (screen[:,:,1] > 120) & (screen[:,:,1] < 210) & (screen[:,:,0] < 80)
coords = np.where(mask)
if len(coords[0]) > 100:
    print("Step 2: Login screen detected, clicking Login...")
    ys, xs = coords[0], coords[1]
    btn_mask = (ys > 400) & (ys < 600)
    if btn_mask.any():
        cy = int(np.mean(ys[btn_mask]))
        cx = int(np.mean(xs[btn_mask]))
        pyautogui.click(cx, cy)
        print(f"  Clicked Login at ({cx},{cy})")
        time.sleep(8)
        screen = screenshot()

# Check for FichasNet (club selection)
ref_club = cv2.imread(r'C:\Users\PC\Downloads\SELECIONAR CLUBE FICHAS NET.png')
if ref_club is not None:
    text_tmpl = ref_club[252:270, 125:225]
    result = cv2.matchTemplate(screen, text_tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val > 0.7:
        h, w = text_tmpl.shape[:2]
        cx = max_loc[0] + w // 2
        cy = max_loc[1] + h // 2
        print(f"Step 3: Found FichasNet at ({cx},{cy}), clicking...")
        pyautogui.click(cx, cy)
        time.sleep(5)
        screen = screenshot()

# Check for TODOS tab (table list)
todos_tmpl = cv2.imread(r'C:\Users\PC\Downloads\todos_tmpl.png')
if todos_tmpl is not None:
    result = cv2.matchTemplate(screen, todos_tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    if max_val > 0.7:
        print("Step 4: Table list found, looking for NLH tab...")
        # Click NLH tab (right of TODOS)
        _, _, _, max_loc = cv2.minMaxLoc(result)
        nlh_x = max_loc[0] + 80  # NLH is about 80px right of TODOS
        nlh_y = max_loc[1] + 9
        pyautogui.click(nlh_x, nlh_y)
        time.sleep(2)
        screen = screenshot()

        # Find green mesas
        mesas = find_green_mesas(screen)
        print(f"  Found {len(mesas)} green mesas")
        if mesas:
            cx, cy = mesas[0]
            print(f"Step 5: Clicking mesa at ({cx},{cy})")
            pyautogui.click(cx, cy)
            time.sleep(5)
            screen = screenshot()

# Save final state
cv2.imwrite(r'C:\Users\PC\Downloads\auto_final.png', screen)
print("Automation complete!")

# Check if we're in a table
if todos_tmpl is not None:
    result = cv2.matchTemplate(screen, todos_tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    if max_val < 0.7:
        print("IN TABLE! Ready for spy.")
    else:
        print("Still in table list.")
