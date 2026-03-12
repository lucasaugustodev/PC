import time
import ctypes
import ctypes.wintypes
from PIL import ImageGrab, Image
import pytesseract
import sys
import os
from datetime import datetime

# Config
INTERVAL = 1.0
LOG_FILE = r"C:\Users\PC\suprema_hands.log"
TESSERACT_CMD = os.path.expanduser(r"~\scoop\shims\tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Win32 API
user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                 ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))

def get_window_text(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    return buf.value

def find_suprema_window():
    """Find Suprema/poker window handle"""
    found = [None]
    keywords = ["suprema", "fichanet", "b2xgroup", "poker", "pppoker"]

    def callback(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            title = get_window_text(hwnd).lower()
            for kw in keywords:
                if kw in title:
                    found[0] = hwnd
                    return False
        return True

    user32.EnumWindows(EnumWindowsProc(callback), None)
    return found[0]

def capture_window(hwnd):
    """Capture window region as PIL Image"""
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    bbox = (rect.left, rect.top, rect.right, rect.bottom)
    if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
        return None
    return ImageGrab.grab(bbox)

def ocr_image(img):
    """Run OCR on image, return text"""
    # Convert to grayscale for faster OCR
    gray = img.convert('L')
    # Threshold for cleaner text
    gray = gray.point(lambda x: 0 if x < 128 else 255)
    text = pytesseract.image_to_string(gray, lang='eng', config='--psm 6')
    return text.strip()

def main():
    print("=== SUPREMA HAND MONITOR ===")
    print(f"Log: {LOG_FILE}")
    print(f"Interval: {INTERVAL}s")
    print("Ctrl+C to stop\n")

    hwnd = find_suprema_window()
    if hwnd:
        title = get_window_text(hwnd)
        print(f"Window found: '{title}'")
    else:
        print("WARNING: Suprema window not found, using full screen")

    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"\n=== SESSION {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")

    last_text = ""
    frame = 0

    try:
        while True:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            # Re-find window every 10 frames
            if frame % 10 == 0:
                new_hwnd = find_suprema_window()
                if new_hwnd:
                    hwnd = new_hwnd

            # Capture
            if hwnd:
                img = capture_window(hwnd)
            else:
                img = ImageGrab.grab()

            if img is None:
                time.sleep(INTERVAL)
                frame += 1
                continue

            # OCR
            text = ocr_image(img)

            # Only log changes
            if text and text != last_text:
                entry = f"[{ts}] {text}"
                with open(LOG_FILE, "a", encoding="utf-8") as log:
                    log.write(entry + "\n---\n")

                # Console preview
                preview = text[:150].replace('\n', ' | ')
                print(f"[{ts}] CHANGE: {preview}")
                last_text = text
            else:
                sys.stdout.write(".")
                sys.stdout.flush()

            frame += 1
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print(f"\nStopped. {frame} frames captured. Log: {LOG_FILE}")

if __name__ == "__main__":
    main()
