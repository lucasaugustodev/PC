import pyautogui, time, ctypes, subprocess
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

r = subprocess.run(['powershell', '-Command',
    '(Get-Process -Name SupremaPoker).MainWindowHandle'],
    capture_output=True, text=True)
hwnd = int(r.stdout.strip())
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
L, T = rect.left, rect.top

# The Mini+SPT card in crop is approximately:
# Top-left corner: (15, 295), bottom-right: (205, 380)
# Center: (110, 337)
abs_x = L + 110
abs_y = T + 337

print(f"Clicking center of Mini+SPT card at ({abs_x},{abs_y})")
pyautogui.moveTo(abs_x, abs_y, duration=0.2)
time.sleep(0.3)
pyautogui.click()
print("CLICKED!")

time.sleep(5)
# Crop to check
img = pyautogui.screenshot()
import cv2
screen = cv2.imread(r'C:\Users\PC\Downloads\full_now.png')  
img.save(r'C:\Users\PC\Downloads\full_now.png')
screen = cv2.imread(r'C:\Users\PC\Downloads\full_now.png')
win = screen[rect.top:rect.bottom, rect.left:rect.right]
cv2.imwrite(r'C:\Users\PC\Downloads\after_mesa_crop.png', win)
print("Done")
