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

# Raise panel buttons
BTN_25X = (44, 817)
BTN_3X = (119, 817)
BTN_4X = (191, 817)
BTN_ALLIN = (272, 817)
BTN_CONFIRM = (388, 817)
BTN_PLUS = (316, 536)
BTN_MINUS = (316, 606)

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
print("  3 = BET/RAISE (Apostar)")
print("  4 = 2.5X preset")
print("  5 = 3X preset")
print("  6 = 4X preset")
print("  7 = All In")
print("  8 = Confirmar")
print("  9 = + (plus)")
print("  0 = - (minus)")
print("  r = Full raise test: Apostar -> 3X -> Confirmar")
print("  a = Full all-in test: Apostar -> All In -> Confirmar")
print("  q = Quit")
print()
print("NOTE: Make sure it's your turn before testing!")
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
        click(*BTN_25X, '2.5X')
    elif cmd == '5':
        click(*BTN_3X, '3X')
    elif cmd == '6':
        click(*BTN_4X, '4X')
    elif cmd == '7':
        click(*BTN_ALLIN, 'ALL-IN')
    elif cmd == '8':
        click(*BTN_CONFIRM, 'CONFIRMAR')
    elif cmd == '9':
        click(*BTN_PLUS, 'PLUS')
    elif cmd == '0':
        click(*BTN_MINUS, 'MINUS')
    elif cmd == 'r':
        print("--- Full raise sequence ---")
        click(*BTN_BET, 'APOSTAR')
        time.sleep(0.7)
        click(*BTN_3X, '3X')
        time.sleep(0.3)
        click(*BTN_CONFIRM, 'CONFIRMAR')
    elif cmd == 'a':
        print("--- Full all-in sequence ---")
        click(*BTN_BET, 'APOSTAR')
        time.sleep(0.7)
        click(*BTN_ALLIN, 'ALL-IN')
        time.sleep(0.3)
        click(*BTN_CONFIRM, 'CONFIRMAR')
    else:
        print("Unknown command")
