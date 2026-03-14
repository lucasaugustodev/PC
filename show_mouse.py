import pyautogui, time, ctypes, subprocess, cv2
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(1)

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
L, T = rect.left, rect.top
W = rect.right - rect.left
H = rect.bottom - rect.top

# Move mouse to where I THINK Mini+SPT is and take screenshot
# Try several positions and mark all of them
positions = [
    (100, 285, "A"),
    (100, 320, "B"),
    (100, 350, "C"),
    (150, 300, "D"),
    (150, 330, "E"),
]

img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\positions.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\positions.png')
win = screen[T:rect.bottom, L:rect.right].copy()

for x, y, label in positions:
    cv2.circle(win, (x, y), 8, (0, 0, 255), 2)
    cv2.putText(win, label, (x+12, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

cv2.imwrite(r'C:\Users\PC\Downloads\positions_marked.png', win)
print("Positions marked - check positions_marked.png")
print(f"Window: {L},{T} size {W}x{H}")
