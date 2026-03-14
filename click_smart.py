import pyautogui, time, ctypes, subprocess
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

# Close the browser tab that opened
import pyautogui
pyautogui.hotkey('alt', 'F4')
time.sleep(1)

# Activate SupremaPoker
r = subprocess.run(['powershell', '-Command', 
    '(Get-Process -Name SupremaPoker).MainWindowHandle'], 
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(1)

# Get fresh window position
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), 
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
L, T = rect.left, rect.top
print(f"Window at ({L}, {T})")

# From the crop image we can see:
# Title bar: ~30px
# "Augustolucas | Reportar" bar: ~25px  (y~30-55)
# Banner "CONTA VERIFICADA": ~65px (y~55-120)
# "Buscar Clube | Criar Clube" bar: ~25px (y~120-145)
# FichasNet entry: ~45px (y~145-190)
# 
# FichasNet center is approximately at y=167 from window top
# and x=center of window = 210

click_x = L + 210
click_y = T + 167
print(f"Moving mouse to ({click_x}, {click_y}) and clicking...")

# Move mouse slowly so we can verify position
pyautogui.moveTo(click_x, click_y, duration=0.3)
time.sleep(0.5)

# Take screenshot to verify mouse position before clicking
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\mouse_position.png')

# Now click
pyautogui.click()
print("CLICKED!")

time.sleep(3)
img2 = pyautogui.screenshot()
img2.save(r'C:\Users\PC\Downloads\after_fichas.png')
print("Done")
