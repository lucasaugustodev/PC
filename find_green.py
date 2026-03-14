import pyautogui, time, ctypes, subprocess, cv2, numpy as np
pyautogui.FAILSAFE = False

user32 = ctypes.windll.user32
r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(1)

# First close the RODEO popup by clicking X
# The X button is at top-right of the popup
pil = pyautogui.screenshot()
screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

# Find the X button (white circle with X) 
# Let me press Escape or click the X to close popup first
pyautogui.press('escape')
time.sleep(1)

# Take fresh screenshot
pil = pyautogui.screenshot()
screen = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

# Convert to HSV to find green color
hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

# Green felt color range in HSV
# Hue: 35-85 (green range), Saturation: 30-255, Value: 30-255
lower_green = np.array([35, 40, 40])
upper_green = np.array([85, 255, 255])
mask = cv2.inRange(hsv, lower_green, upper_green)

# Find green pixel clusters
coords = np.where(mask > 0)
if len(coords[0]) > 0:
    print(f"Found {len(coords[0])} green pixels")
    
    # Get all green pixel positions
    ys = coords[0]
    xs = coords[1]
    
    # Filter to Suprema window area (roughly x=280-700)
    win_mask = (xs >= 250) & (xs <= 720)
    ys = ys[win_mask]
    xs = xs[win_mask]
    
    if len(ys) > 0:
        print(f"Green pixels in window area: {len(ys)}")
        print(f"X range: {xs.min()}-{xs.max()}")
        print(f"Y range: {ys.min()}-{ys.max()}")
        
        # Find clusters using connected components or just group by Y ranges
        # Each table entry has a green icon/indicator
        # Let's find distinct Y clusters
        unique_ys = np.unique(ys)
        clusters = []
        current_cluster = [unique_ys[0]]
        for i in range(1, len(unique_ys)):
            if unique_ys[i] - unique_ys[i-1] <= 5:
                current_cluster.append(unique_ys[i])
            else:
                if len(current_cluster) >= 3:
                    clusters.append(current_cluster)
                current_cluster = [unique_ys[i]]
        if len(current_cluster) >= 3:
            clusters.append(current_cluster)
        
        print(f"\nFound {len(clusters)} green clusters:")
        for i, c in enumerate(clusters):
            cy = int(np.mean(c))
            # Get x range for this cluster
            cluster_mask = (ys >= c[0]) & (ys <= c[-1])
            cx = int(np.mean(xs[cluster_mask]))
            print(f"  Cluster {i}: center=({cx},{cy}), y_range={c[0]}-{c[-1]}, size={len(c)}px")
        
        # Draw all green pixels and clusters on debug image
        debug = screen.copy()
        debug[mask > 0] = [0, 255, 0]  # Highlight green pixels
        for i, c in enumerate(clusters):
            cy = int(np.mean(c))
            cluster_mask = (ys >= c[0]) & (ys <= c[-1])
            cx = int(np.mean(xs[cluster_mask]))
            cv2.circle(debug, (cx, cy), 12, (0, 0, 255), 2)
            cv2.putText(debug, f"#{i}", (cx+15, cy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
        
        cv2.imwrite(r'C:\Users\PC\Downloads\green_debug.png', debug)
        print("\nDebug image saved")
        
        # Click the FIRST green cluster (first mesa)
        if clusters:
            first = clusters[0]
            cy = int(np.mean(first))
            cluster_mask = (ys >= first[0]) & (ys <= first[-1])
            cx = int(np.mean(xs[cluster_mask]))
            print(f"\nClicking first green cluster at ({cx},{cy})")
            pyautogui.click(cx, cy)
            print("CLICKED!")
    else:
        print("No green pixels in window area")
else:
    print("No green pixels found")

time.sleep(4)
after = pyautogui.screenshot()
after.save(r'C:\Users\PC\Downloads\after_green.png')

DWMWA = 9
dwm_rect = (ctypes.c_long * 4)()
ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA, ctypes.byref(dwm_rect), ctypes.sizeof(dwm_rect))
L, T, R, B = dwm_rect[0], dwm_rect[1], dwm_rect[2], dwm_rect[3]
ascreen = cv2.cvtColor(np.array(after), cv2.COLOR_RGB2BGR)
win = ascreen[T:B, L:R]
cv2.imwrite(r'C:\Users\PC\Downloads\after_green_win.png', win)
print("Done")
