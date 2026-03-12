"""
Card Template Collector for Suprema Poker.
Continuously captures board cards and saves unique ones.
User manually labels them after collection.
"""
from PIL import ImageGrab, Image
import numpy as np
import ctypes
import time
import os
import hashlib
from datetime import datetime

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                 ("r", ctypes.c_long), ("b", ctypes.c_long)]

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))

OUT_DIR = r"C:\Users\PC\suprema_templates\collected"
os.makedirs(OUT_DIR, exist_ok=True)

def find_suprema():
    found = [None]
    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            if 'supremapoker' in buf.value.lower():
                found[0] = hwnd; return False
        return True
    user32.EnumWindows(EnumWindowsProc(cb), None)
    return found[0]

def extract_cards(img):
    """Extract individual card images from the board area"""
    w, h = img.size

    # Board card row region - precise crop below POT
    y1, y2 = int(h * 0.335), int(h * 0.40)
    x1, x2 = int(w * 0.06), int(w * 0.74)
    board = np.array(img.crop((x1, y1, x2, y2)))
    bh, bw = board.shape[:2]

    # Find white card rectangles
    gray = np.mean(board, axis=2)
    white = gray > 185
    col_ratio = np.mean(white, axis=0)

    in_card = False
    card_cols = []
    start = 0
    for x in range(bw):
        if col_ratio[x] > 0.12 and not in_card:
            start = x; in_card = True
        elif col_ratio[x] < 0.06 and in_card:
            if x - start > 12:
                card_cols.append((start, x))
            in_card = False
    if in_card and bw - start > 12:
        card_cols.append((start, bw))

    cards = []
    for cx1, cx2 in card_cols:
        col_slice = white[:, cx1:cx2]
        row_r = np.mean(col_slice, axis=1)
        cy1 = next((y for y in range(bh) if row_r[y] > 0.15), 0)
        cy2 = next((y for y in range(bh-1, 0, -1) if row_r[y] > 0.15), bh)

        if cy2 - cy1 < 8:
            continue

        card = board[cy1:cy2+1, cx1:cx2]
        cards.append(Image.fromarray(card))

    return cards

def img_hash(img):
    """Perceptual hash of card image"""
    small = img.resize((16, 24)).convert('L')
    arr = np.array(small)
    avg = np.mean(arr)
    bits = (arr > avg).flatten()
    return hashlib.md5(bits.tobytes()).hexdigest()[:12]

def main():
    print("=== SUPREMA CARD COLLECTOR ===")
    print(f"Output: {OUT_DIR}")
    print("Collecting unique card images from the board...")
    print("Press Ctrl+C to stop\n")

    seen_hashes = set()
    # Load existing hashes
    for f in os.listdir(OUT_DIR):
        if f.endswith('.png'):
            try:
                existing = Image.open(os.path.join(OUT_DIR, f))
                seen_hashes.add(img_hash(existing))
            except:
                pass

    print(f"Already collected: {len(seen_hashes)} unique cards\n")

    hwnd = find_suprema()
    total_frames = 0

    try:
        while True:
            if total_frames % 10 == 0:
                hwnd = find_suprema()

            if not hwnd:
                time.sleep(2)
                total_frames += 1
                continue

            r = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))

            if r.l < -50:
                user32.SetWindowPos(hwnd, None, 50, 50, r.r-r.l, r.b-r.t, 0x0040)
                time.sleep(0.5)
                user32.GetWindowRect(hwnd, ctypes.byref(r))

            try:
                img = ImageGrab.grab((r.l, r.t, r.r, r.b))
            except:
                time.sleep(1)
                continue

            cards = extract_cards(img)

            for card in cards:
                h = img_hash(card)
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    ts = datetime.now().strftime("%H%M%S")
                    filename = f"card_{ts}_{h}.png"
                    card.save(os.path.join(OUT_DIR, filename))

                    # Also save zoomed
                    zoomed = card.resize((card.width*4, card.height*4), Image.LANCZOS)
                    zoomed.save(os.path.join(OUT_DIR, f"card_{ts}_{h}_zoom.png"))

                    print(f"[{ts}] NEW CARD #{len(seen_hashes)}: {filename} ({card.size})")

            total_frames += 1
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\nDone! Collected {len(seen_hashes)} unique cards in {OUT_DIR}")
        print("Next step: rename files to their card value (e.g., Ah.png, Ks.png, 10d.png)")

if __name__ == "__main__":
    main()
