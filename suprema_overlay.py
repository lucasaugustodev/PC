import tkinter as tk
from tkinter import scrolledtext
import ctypes
from PIL import ImageGrab, Image, ImageEnhance
import pytesseract
import numpy as np
import threading
import time
import re
import os
from datetime import datetime
from collections import deque

pytesseract.pytesseract.tesseract_cmd = os.path.expanduser(r"~\scoop\shims\tesseract.exe")
user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                 ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
LOG_FILE = r"C:\Users\PC\suprema_hands.log"

# Suprema suit colors:
# Blue = Diamonds (ouros), Green = Clubs (paus), Black = Spades (espadas), Red = Hearts (copas)

# 9-max seat positions (center point of each seat as % of window)
# Used to map detected bet text to the nearest seat
SEAT_CENTERS_9 = {
    'S1': (0.30, 0.10),   # top-center-left
    'S2': (0.65, 0.10),   # top-center-right
    'S3': (0.82, 0.22),   # right-high
    'S4': (0.82, 0.40),   # right-low
    'S5': (0.70, 0.55),   # bottom-right
    'S6': (0.40, 0.62),   # bottom-center
    'S7': (0.15, 0.55),   # bottom-left
    'S8': (0.10, 0.40),   # left-low
    'S9': (0.10, 0.22),   # left-high
}

# Bet text positions: pills with "X BB" between player and center
# Calibrated precisely: bets are BELOW stacks, BETWEEN player and table center
# Player names ~y=13%, stacks ~y=15% (yellow), bets ~y=17% (white in gray pill)
SEAT_BET_POS_9 = {
    'S1': (0.35, 0.172),   # top-left bet (below EdnaA stack, toward center)
    'S2': (0.58, 0.172),   # top-right bet (below BlackL018 stack, toward center)
    'S3': (0.73, 0.26),    # right-high bet
    'S4': (0.73, 0.40),    # right-low bet
    'S5': (0.58, 0.52),    # bottom-right bet
    'S6': (0.40, 0.58),    # bottom-center bet
    'S7': (0.22, 0.52),    # bottom-left bet
    'S8': (0.15, 0.40),    # left-low bet
    'S9': (0.15, 0.26),    # left-high bet
}


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


def get_window_rect(hwnd):
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def find_card_columns(arr):
    """Find white card rectangles by scanning columns for high brightness"""
    gray = np.mean(arr, axis=2)
    h, w = gray.shape

    # White card pixels (brightness > 190)
    white = gray > 190
    col_ratio = np.mean(white, axis=0)

    # Find contiguous columns with significant white
    in_card = False
    cards = []
    start = 0
    for x in range(w):
        if col_ratio[x] > 0.15 and not in_card:
            start = x; in_card = True
        elif col_ratio[x] < 0.08 and in_card:
            width = x - start
            if width > 15:  # minimum card width in pixels
                cards.append((start, x))
            in_card = False
    if in_card and w - start > 15:
        cards.append((start, w))

    return cards


def detect_suit(card_arr):
    """Detect suit by color. Returns suit symbol."""
    r, g, b = card_arr[:,:,0].astype(int), card_arr[:,:,1].astype(int), card_arr[:,:,2].astype(int)
    gray = np.mean(card_arr, axis=2)

    # Only analyze non-white, non-gray-background pixels
    on_card = gray < 180  # colored/dark pixels on the card

    if np.sum(on_card) < 5:
        return '?'

    r_m, g_m, b_m = r[on_card], g[on_card], b[on_card]

    # Blue (diamonds/ouros): b dominant
    blue_n = int(np.sum((b_m > r_m + 25) & (b_m > g_m + 10) & (b_m > 100)))
    # Red (hearts/copas): r dominant
    red_n = int(np.sum((r_m > g_m + 40) & (r_m > b_m + 40) & (r_m > 140)))
    # Green (clubs/paus): g dominant
    green_n = int(np.sum((g_m > r_m + 25) & (g_m > b_m + 25) & (g_m > 80)))
    # Black (spades/espadas): very dark
    black_n = int(np.sum((r_m < 80) & (g_m < 80) & (b_m < 80)))

    counts = {'♦': blue_n, '♥': red_n, '♣': green_n, '♠': black_n}
    best = max(counts, key=counts.get)

    if counts[best] < 3:
        return '?'
    return best


def ocr_card_value(card_arr):
    """Read the card value using OCR"""
    h, w = card_arr.shape[:2]

    # Use top-left portion for the value number/letter
    val_region = card_arr[:int(h*0.55), :int(w*0.60)]

    # Scale up 6x for better OCR
    val_img = Image.fromarray(val_region)
    val_img = val_img.resize((val_img.width*6, val_img.height*6), Image.LANCZOS)

    arr = np.array(val_img)
    gray = np.mean(arr, axis=2)

    # Try two binarization thresholds
    for threshold in [185, 170, 200]:
        bw = np.where(gray > threshold, 255, 0).astype(np.uint8)
        bw_img = Image.fromarray(bw)

        for psm in [10, 7, 8, 13]:
            text = pytesseract.image_to_string(bw_img,
                config=f'--psm {psm} -c tessedit_char_whitelist=0123456789AKQJ').strip().upper()
            if text:
                break
        if text:
            break

    # Also try inverted (dark on light -> light on dark)
    if not text:
        inv = np.where(gray > 185, 0, 255).astype(np.uint8)
        inv_img = Image.fromarray(inv)
        text = pytesseract.image_to_string(inv_img,
            config='--psm 10 -c tessedit_char_whitelist=0123456789AKQJ').strip().upper()

    # Clean common OCR errors
    text = text.replace('1O', '10').replace('IO', '10').replace('1Q', '10')
    text = text.replace('O', '0').replace('I', '1').replace('L', '1') if len(text) <= 2 else text
    text = text.replace('\n', '').replace(' ', '')

    valid = {'A','2','3','4','5','6','7','8','9','10','J','Q','K'}
    if text in valid:
        return text
    for c in text:
        if c in 'AKQJ':
            return c
    if '10' in text:
        return '10'
    if text and text[0].isdigit():
        return text[0]
    return '?'


def read_board_cards(full_img):
    """Read community cards from the board.
    Returns list of strings like '8h', 'Ks', etc."""
    w, h = full_img.size

    # Card row region - calibrated for 580x1043 window
    y_top = int(h * 0.345)
    y_bot = int(h * 0.405)
    x_left = int(w * 0.06)
    x_right = int(w * 0.82)

    board_arr = np.array(full_img.crop((x_left, y_top, x_right, y_bot)))
    bh, bw = board_arr.shape[:2]

    # Find card columns
    card_cols = find_card_columns(board_arr)

    if not card_cols:
        return []

    # For each card column, find vertical extent and read
    cards = []
    gray = np.mean(board_arr, axis=2)
    white = gray > 190

    for x1, x2 in card_cols:
        # Find vertical card extent in this column
        col_slice = white[:, x1:x2]
        row_ratio = np.mean(col_slice, axis=1)

        y1 = next((y for y in range(bh) if row_ratio[y] > 0.2), 0)
        y2 = next((y for y in range(bh-1, 0, -1) if row_ratio[y] > 0.2), bh)

        if y2 - y1 < 10:
            continue

        card_arr = board_arr[y1:y2+1, x1:x2]

        # Get suit
        suit = detect_suit(card_arr)

        # Get value
        value = ocr_card_value(card_arr)

        cards.append(f"{value}{suit}")

    return cards


def read_all_bets(full_img):
    """Read bet amounts by scanning for white-text-in-gray-pill patterns.
    Bets are small pills with white text 'X BB' + colored chips nearby.
    Stacks are yellow text below player names at the edges."""
    w, h = full_img.size
    arr = np.array(full_img)
    bets = {}

    for seat, (cx, cy) in SEAT_BET_POS_9.items():
        # Box wide enough to capture full pill (~80px wide, ~18px tall)
        x1 = max(0, int(w * (cx - 0.09)))
        y1 = max(0, int(h * (cy - 0.013)))
        x2 = min(w, int(w * (cx + 0.09)))
        y2 = min(h, int(h * (cy + 0.016)))

        crop = full_img.crop((x1, y1, x2, y2))
        crop_arr = np.array(crop)

        # Check if there's any white text in this region (bright pixels)
        gray = np.mean(crop_arr, axis=2)
        bright_ratio = np.mean(gray > 190)
        if bright_ratio < 0.02:
            continue  # no bright text, skip OCR

        # Check it's not yellow text (stack) - sample color of bright pixels
        bright_mask = gray > 190
        if np.sum(bright_mask) > 5:
            bright_r = np.mean(crop_arr[:,:,0][bright_mask])
            bright_g = np.mean(crop_arr[:,:,1][bright_mask])
            bright_b = np.mean(crop_arr[:,:,2][bright_mask])
            # Yellow: R>200, G>180, B<150
            if bright_r > 200 and bright_g > 180 and bright_b < 150:
                continue  # yellow text = stack, skip

        # Scale 6x with sharpening for decimal point detection
        big = crop.resize((crop.width * 6, crop.height * 6), Image.LANCZOS)
        big = ImageEnhance.Sharpness(big).enhance(2.5)
        big_arr = np.array(big)
        big_gray = np.mean(big_arr, axis=2)
        bw = np.where(big_gray > 150, 0, 255).astype(np.uint8)
        bw_img = Image.fromarray(bw)

        text = ""
        try:
            text = pytesseract.image_to_string(bw_img,
                config='--psm 7 -c tessedit_char_whitelist=0123456789.BB').strip()
        except:
            continue

        # Try to match "X.X BB" or "X BB" or just "X.X" (pill partially cropped)
        m = re.search(r'([\d.]+)\s*B', text)
        if not m:
            m = re.match(r'^([\d.]+)$', text.replace(' ', ''))
        if m:
            try:
                val = float(m.group(1))
                # Sanity: if val >= 10 and could be a decimal misread (e.g. 50 = 5.0, 15 = 1.5)
                # check if the raw text had no decimal but the value is suspiciously round
                raw_num = m.group(1)
                if '.' not in raw_num and val >= 10:
                    # OCR likely missed decimal - try inserting before last digit
                    # e.g. "50" -> "5.0", "15" -> "1.5", "25" -> "2.5"
                    fixed = raw_num[:-1] + '.' + raw_num[-1]
                    val = float(fixed)
                if 0.1 <= val <= 200:
                    bets[seat] = str(val)
            except ValueError:
                pass

    return bets


def read_pot(full_img):
    """Read pot value from the pill below POT label"""
    w, h = full_img.size
    # Tight crop: just the pill with the number, below "POT" text
    # y=31.5-34.5%, x=32-68% - avoids "POT" text and chips above
    pot_pill = full_img.crop((int(w*0.32), int(h*0.315), int(w*0.68), int(h*0.345)))

    # Scale up 5x and sharpen for decimal point detection
    pr = pot_pill.resize((pot_pill.width*5, pot_pill.height*5), Image.LANCZOS)
    pr = ImageEnhance.Sharpness(pr).enhance(2.5)
    arr = np.array(pr)
    gray = np.mean(arr, axis=2)

    # White text on dark gray pill
    bw = np.where(gray > 150, 0, 255).astype(np.uint8)
    bw_img = Image.fromarray(bw)

    text = pytesseract.image_to_string(bw_img,
        config='--psm 7 -c tessedit_char_whitelist=0123456789.BB').strip()

    match = re.search(r'([\d.]+)\s*B', text)
    if match:
        return f"{match.group(1)} BB"

    return ""


class HandTracker:
    def __init__(self):
        self.history = deque(maxlen=300)
        self.current_board = []
        self.current_pot = ""
        self.current_bets = {}
        self.hand_number = 0
        self.had_cards = False

    def update(self, board_cards, pot, bets=None):
        ts = datetime.now().strftime("%H:%M:%S")
        events = []
        has_cards = len(board_cards) > 0

        # New hand detection: cards disappear
        if self.had_cards and not has_cards:
            self.hand_number += 1
            events.append(("newhand", f"[{ts}] ========== MAO #{self.hand_number} =========="))
            self.current_board = []
            self.current_pot = ""
            self.current_bets = {}

        self.had_cards = has_cards

        # Board changed
        board_str = ' '.join(board_cards)
        old_str = ' '.join(self.current_board)

        if board_cards and board_str != old_str:
            n = len(board_cards)
            n_old = len(self.current_board)

            if n == 3 and n_old < 3:
                events.append(("flop", f"[{ts}] FLOP:  {board_str}"))
            elif n == 4 and n_old < 4:
                events.append(("turn", f"[{ts}] TURN:  {board_str}"))
            elif n == 5 and n_old < 5:
                events.append(("river", f"[{ts}] RIVER: {board_str}"))
            elif n != n_old:
                events.append(("board", f"[{ts}] BOARD: {board_str}"))
            elif n == n_old and board_str != old_str:
                events.append(("board", f"[{ts}] BOARD: {board_str}"))

            self.current_board = board_cards[:]

        # Pot changed
        if pot and pot != self.current_pot:
            events.append(("pot", f"[{ts}] POT: {pot}"))
            self.current_pot = pot

        # Bets changed
        if bets and bets != self.current_bets:
            new_bets = {s: v for s, v in bets.items() if self.current_bets.get(s) != v}
            if new_bets:
                bet_parts = [f"{s}={v}BB" for s, v in sorted(new_bets.items())]
                events.append(("bet", f"[{ts}] BETS: {' | '.join(bet_parts)}"))
            self.current_bets = bets.copy()

        for e in events:
            self.history.append(e)
        return events


class SupremaOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Suprema Monitor")
        self.root.geometry("500x550+600+30")
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#0d1117')
        self.root.resizable(True, True)

        # Header
        header = tk.Frame(self.root, bg='#161b22')
        header.pack(fill='x', padx=2, pady=2)
        self.status_label = tk.Label(header, text="SUPREMA MONITOR",
            font=('Consolas', 12, 'bold'), fg='#00ff88', bg='#161b22')
        self.status_label.pack(side='left', padx=10, pady=5)
        self.fps_label = tk.Label(header, text="...",
            font=('Consolas', 9), fg='#555', bg='#161b22')
        self.fps_label.pack(side='right', padx=10, pady=5)

        # Current state
        state = tk.Frame(self.root, bg='#161b22', relief='flat', borderwidth=0)
        state.pack(fill='x', padx=4, pady=(0,2))

        self.board_label = tk.Label(state, text="BOARD: aguardando...",
            font=('Consolas', 18, 'bold'), fg='#ffa657', bg='#161b22', anchor='w')
        self.board_label.pack(fill='x', padx=10, pady=(6,0))

        self.pot_label = tk.Label(state, text="POT: --",
            font=('Consolas', 13, 'bold'), fg='#7ee787', bg='#161b22', anchor='w')
        self.pot_label.pack(fill='x', padx=10, pady=(0,2))

        self.hand_label = tk.Label(state, text="Mao #0 | Preflop",
            font=('Consolas', 10), fg='#8b949e', bg='#161b22', anchor='w')
        self.hand_label.pack(fill='x', padx=10, pady=(0,2))

        self.bets_label = tk.Label(state, text="BETS: --",
            font=('Consolas', 11, 'bold'), fg='#79c0ff', bg='#161b22', anchor='w')
        self.bets_label.pack(fill='x', padx=10, pady=(0,4))

        # Separator
        sep = tk.Frame(self.root, bg='#30363d', height=1)
        sep.pack(fill='x', padx=4)

        # History
        self.history_text = scrolledtext.ScrolledText(self.root,
            font=('Consolas', 10), bg='#0d1117', fg='#c9d1d9',
            insertbackground='white', wrap='word', borderwidth=0, padx=10, pady=8)
        self.history_text.pack(fill='both', expand=True, padx=4, pady=4)

        self.history_text.tag_config('newhand', foreground='#ff7b72', font=('Consolas', 11, 'bold'))
        self.history_text.tag_config('flop', foreground='#ffa657', font=('Consolas', 11, 'bold'))
        self.history_text.tag_config('turn', foreground='#d2a8ff', font=('Consolas', 11, 'bold'))
        self.history_text.tag_config('river', foreground='#ff7b72', font=('Consolas', 11, 'bold'))
        self.history_text.tag_config('board', foreground='#ffa657')
        self.history_text.tag_config('pot', foreground='#7ee787')
        self.history_text.tag_config('bet', foreground='#79c0ff')

        self.running = True
        self.frame_count = 0
        self.hwnd = None
        self.tracker = HandTracker()
        self.last_img_hash = None

        self.thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.thread.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.running = False
        self.root.destroy()

    def add_history(self, tag, text):
        self.history_text.config(state='normal')
        self.history_text.insert('end', text + '\n', tag)
        self.history_text.config(state='disabled')
        self.history_text.see('end')

    def flash(self):
        self.status_label.config(fg='#ff7b72', text="CHANGE!")
        self.root.after(600, lambda: self.status_label.config(fg='#00ff88', text="SUPREMA MONITOR"))

    def capture_loop(self):
        while self.running:
            t0 = time.time()

            # Find window
            if self.frame_count % 10 == 0:
                self.hwnd = find_suprema()

            if not self.hwnd:
                self.root.after(0, lambda: self.fps_label.config(text="Janela nao encontrada"))
                time.sleep(2)
                self.frame_count += 1
                continue

            bbox = get_window_rect(self.hwnd)
            if bbox[0] < -50:
                user32.SetWindowPos(self.hwnd, None, 50, 50,
                    bbox[2]-bbox[0], bbox[3]-bbox[1], 0x0040)
                time.sleep(0.5)
                bbox = get_window_rect(self.hwnd)

            try:
                img = ImageGrab.grab(bbox)
            except:
                time.sleep(1); continue

            w, h = img.size

            # Quick change detection: hash the board region
            board_check = img.crop((int(w*0.06), int(h*0.34), int(w*0.82), int(h*0.41)))
            small = board_check.resize((40, 20))
            img_hash = hash(small.tobytes())

            if img_hash == self.last_img_hash:
                elapsed = time.time() - t0
                self.root.after(0, lambda t=f"{elapsed:.2f}s | #{self.frame_count}":
                    self.fps_label.config(text=t))
                self.frame_count += 1
                time.sleep(max(0.1, 0.7 - elapsed))
                continue

            self.last_img_hash = img_hash

            # Read board cards
            board_cards = read_board_cards(img)

            # Read pot
            pot = read_pot(img)

            # Read bets (every other frame to save CPU)
            bets = {}
            if self.frame_count % 2 == 0:
                try:
                    bets = read_all_bets(img)
                except:
                    pass

            # Track changes
            events = self.tracker.update(board_cards, pot, bets if bets else None)

            elapsed = time.time() - t0

            # Update UI
            if events:
                for tag, text in events:
                    self.root.after(0, lambda t=tag, tx=text: self.add_history(t, tx))
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(text + "\n")
                self.root.after(0, self.flash)

            # Update current state display
            if board_cards:
                n = len(board_cards)
                street = {3: "Flop", 4: "Turn", 5: "River"}.get(n, f"{n} cards")
                board_display = ' '.join(board_cards)
            else:
                street = "Preflop"
                board_display = "---"

            pot_display = pot if pot else "--"

            # Format bets display
            cur_bets = self.tracker.current_bets
            if cur_bets:
                bets_display = ' | '.join(f"{s}={v}BB" for s, v in sorted(cur_bets.items()))
            else:
                bets_display = "--"

            self.root.after(0, lambda b=board_display:
                self.board_label.config(text=f"BOARD: {b}"))
            self.root.after(0, lambda p=pot_display:
                self.pot_label.config(text=f"POT: {p}"))
            self.root.after(0, lambda s=street:
                self.hand_label.config(text=f"Mao #{self.tracker.hand_number} | {s}"))
            self.root.after(0, lambda bd=bets_display:
                self.bets_label.config(text=f"BETS: {bd}"))
            self.root.after(0, lambda t=f"{elapsed:.2f}s | #{self.frame_count}":
                self.fps_label.config(text=t))

            self.frame_count += 1
            time.sleep(max(0.1, 1.0 - elapsed))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = SupremaOverlay()
    app.run()
