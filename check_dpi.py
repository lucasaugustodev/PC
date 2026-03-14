import ctypes

# Check DPI scaling
user32 = ctypes.windll.user32
# Get DPI for primary monitor
hdc = user32.GetDC(0)
gdi32 = ctypes.windll.gdi32
dpi_x = gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
dpi_y = gdi32.GetDeviceCaps(hdc, 90)  # LOGPIXELSY
user32.ReleaseDC(0, hdc)
print(f"DPI: {dpi_x}x{dpi_y}")
print(f"Scale factor: {dpi_x/96:.0%}")

# Check DPI awareness
try:
    awareness = ctypes.c_int()
    ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
    print(f"DPI awareness: {awareness.value} (0=unaware, 1=system, 2=per-monitor)")
except:
    print("Could not get DPI awareness")

# Get actual vs logical screen size
sm_cxscreen = user32.GetSystemMetrics(0)
sm_cyscreen = user32.GetSystemMetrics(1)
print(f"Logical screen: {sm_cxscreen}x{sm_cyscreen}")

# Try with DPI awareness set
ctypes.windll.shcore.SetProcessDpiAwareness(2)
sm_cx2 = user32.GetSystemMetrics(0)
sm_cy2 = user32.GetSystemMetrics(1)
print(f"Physical screen: {sm_cx2}x{sm_cy2}")

if sm_cxscreen != sm_cx2:
    print(f"!!! DPI SCALING DETECTED! Logical={sm_cxscreen}x{sm_cyscreen}, Physical={sm_cx2}x{sm_cy2}")
    print(f"Scale ratio: {sm_cx2/sm_cxscreen:.3f}")
