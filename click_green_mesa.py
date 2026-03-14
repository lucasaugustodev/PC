import pyautogui, time, ctypes, subprocess, cv2, numpy as np
pyautogui.FAILSAFE = False

user32 = ctypes.windll.user32
r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# Close any popup first
pyautogui.press('escape')
time.sleep(0.5)

# Take screenshot and find green mesas
pil = pyautogui.screenshot()
screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

lower_green = np.array([35, 40, 40])
upper_green = np.array([85, 255, 255])
mask = cv2.inRange(hsv, lower_green, upper_green)

coords = np.where(mask > 0)
ys, xs = coords[0], coords[1]

# Filter to window area
win_mask = (xs >= 250) & (xs <= 720)
ys, xs = ys[win_mask], xs[win_mask]

# Find clusters with minimum size (real mesa icons are bigger)
unique_ys = np.unique(ys)
clusters = []
current = [unique_ys[0]]
for i in range(1, len(unique_ys)):
    if unique_ys[i] - unique_ys[i-1] <= 5:
        current.append(unique_ys[i])
    else:
        if len(current) >= 20:  # Only big clusters = real mesas
            clusters.append(current)
        current = [unique_ys[i]]
if len(current) >= 20:
    clusters.append(current)

print(f"Big green clusters (mesas): {len(clusters)}")
for i, c in enumerate(clusters):
    cy = int(np.mean(c))
    cmask = (ys >= c[0]) & (ys <= c[-1])
    cx = int(np.mean(xs[cmask]))
    print(f"  Mesa {i}: ({cx},{cy}), y={c[0]}-{c[-1]}, size={len(c)}px")

# Click the FIRST big green cluster
if clusters:
    first = clusters[0]
    cy = int(np.mean(first))
    cmask = (ys >= first[0]) & (ys <= first[-1])
    cx = int(np.mean(xs[cmask]))
    print(f"\nClicking mesa at ({cx},{cy})")
    pyautogui.click(cx, cy)
    print("CLICKED!")

time.sleep(5)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_green2.png')
DWMWA = 9
dwm_rect = (ctypes.c_long * 4)()
ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA, ctypes.byref(dwm_rect), ctypes.sizeof(dwm_rect))
L, T, R, B = dwm_rect[0], dwm_rect[1], dwm_rect[2], dwm_rect[3]
ascreen = cv2.cvtColor(np.array(after), cv2.COLOR_RGB2BGR)
win = ascreen[T:B, L:R]
cv2.imwrite(r'C:\Users\PC\Downloads\after_green2_win.png', win)
print("Done")
