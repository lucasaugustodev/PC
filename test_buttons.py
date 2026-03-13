"""Test button clicking on SupremaPoker window."""
import ctypes, time, sys

try:
    import pygetwindow as gw
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pygetwindow'])
    import pygetwindow as gw

def click(rel_x, rel_y, label=''):
    wins = gw.getWindowsWithTitle('SupremaPoker')
    if not wins:
        print("SupremaPoker window not found!")
        return
    w = wins[0]
    abs_x = w.left + rel_x
    abs_y = w.top + rel_y
    print("Clicking %s at window(%d,%d) -> screen(%d,%d)" % (label, rel_x, rel_y, abs_x, abs_y))
    ctypes.windll.user32.SetCursorPos(abs_x, abs_y)
    time.sleep(0.05)
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.02)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)

# Main action buttons
BTN_FOLD = (77, 812)
BTN_CHECK = (232, 812)
BTN_BET = (388, 812)

# Raise panel buttons (calibrated from raise2.png 449x829 + chrome 8/9)
BTN_PRESET1 = (53, 802)    # 1/3 POT or 2.5X
BTN_PRESET2 = (141, 802)   # 2/3 POT or 3X
BTN_PRESET3 = (221, 802)   # 1 POT or 4X
BTN_ALLIN = (308, 802)     # All In
BTN_CONFIRM = (408, 802)   # Confirmar
BTN_PLUS = (324, 545)
BTN_MINUS = (324, 615)

print("=== SupremaPoker Button Tester ===")
print()
wins = gw.getWindowsWithTitle('SupremaPoker')
if wins:
    w = wins[0]
    print("Window: left=%d top=%d w=%d h=%d" % (w.left, w.top, w.width, w.height))
else:
    print("SupremaPoker not found!")
    sys.exit(1)

print()
print("Commands:")
print("  1 = FOLD (Desistir)")
print("  2 = CHECK/CALL (Passar)")
print("  3 = BET/RAISE (Apostar) - opens raise panel")
print("  4 = Preset 1 (1/3 POT or 2.5X)")
print("  5 = Preset 2 (2/3 POT or 3X)")
print("  6 = Preset 3 (1 POT or 4X)")
print("  7 = All In")
print("  8 = Confirmar")
print("  9 = + (plus)")
print("  0 = - (minus)")
print("  r = Full raise: Apostar -> Preset2 -> Confirmar")
print("  a = Full all-in: Apostar -> All In -> Confirmar")
print("  q = Quit")
print()

while True:
    cmd = input("> ").strip().lower()
    if cmd == 'q':
        break
    elif cmd == '1':
        click(*BTN_FOLD, 'FOLD')
    elif cmd == '2':
        click(*BTN_CHECK, 'CHECK/CALL')
    elif cmd == '3':
        click(*BTN_BET, 'APOSTAR')
    elif cmd == '4':
        click(*BTN_PRESET1, 'PRESET1')
    elif cmd == '5':
        click(*BTN_PRESET2, 'PRESET2')
    elif cmd == '6':
        click(*BTN_PRESET3, 'PRESET3')
    elif cmd == '7':
        click(*BTN_ALLIN, 'ALL-IN')
    elif cmd == '8':
        click(*BTN_CONFIRM, 'CONFIRMAR')
    elif cmd == '9':
        click(*BTN_PLUS, 'PLUS')
    elif cmd == '0':
        click(*BTN_MINUS, 'MINUS')
    elif cmd == 'r':
        print("--- Full raise: Apostar -> Preset2 -> Confirmar ---")
        click(*BTN_BET, 'APOSTAR')
        time.sleep(0.8)
        click(*BTN_PRESET2, 'PRESET2')
        time.sleep(0.3)
        click(*BTN_CONFIRM, 'CONFIRMAR')
    elif cmd == 'a':
        print("--- Full all-in: Apostar -> All In -> Confirmar ---")
        click(*BTN_BET, 'APOSTAR')
        time.sleep(0.8)
        click(*BTN_ALLIN, 'ALL-IN')
        time.sleep(0.3)
        click(*BTN_CONFIRM, 'CONFIRMAR')
    else:
        print("Unknown command")
