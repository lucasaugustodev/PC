import pyautogui, time, ctypes, subprocess
pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

# Activate window
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

# From the crop image, "Mini+SPT" mesa is at approximately:
# y = 310-370 from window top (the first table entry below "Mesas Abertas")
# x = center of window ~210
# Let's click center of the Mini+SPT entry
abs_x = L + 130
abs_y = T + 345

print(f"Clicking Mini+SPT at ({abs_x},{abs_y})")
pyautogui.moveTo(abs_x, abs_y, duration=0.2)
time.sleep(0.3)
pyautogui.click()
print("CLICKED!")

time.sleep(4)
img = pyautogui.screenshot()
img.save(r'C:\Users\PC\Downloads\after_mesa.png')
print("Done")
