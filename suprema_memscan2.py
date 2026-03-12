"""Deep scan Suprema Poker memory for card data structures and game state"""
import ctypes
import ctypes.wintypes as wt
import re
import json

kernel32 = ctypes.windll.kernel32
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', wt.DWORD),
        ('RegionSize', ctypes.c_size_t),
        ('State', wt.DWORD),
        ('Protect', wt.DWORD),
        ('Type', wt.DWORD),
    ]

def find_suprema_pid():
    import subprocess
    out = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq SupremaPoker.exe', '/FO', 'CSV', '/NH'], text=True)
    for line in out.strip().split('\n'):
        if 'SupremaPoker' in line:
            parts = line.strip('"').split('","')
            return int(parts[1])
    return None

def scan_memory(pid):
    handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        print("Cannot open process")
        return

    mbi = MEMORY_BASIC_INFORMATION()
    address = 0

    # Patterns to find game state JSON/data
    # Look for card arrays, hand data, board data
    card_pattern = re.compile(rb'"cards?"?\s*[:\[]\s*\[?\s*\d+')
    json_pattern = re.compile(rb'\{[^{}]{10,2000}\}')
    hand_pattern = re.compile(rb'(?:handCard|slHandCard|boardcard|gameCard|CardData|customHandCard)[^"]*?"?\s*[:\[]\s*[\[\{]?[^}]{5,500}', re.IGNORECASE)
    game_state_pattern = re.compile(rb'(?:gameState|GameState|EGameState|gameStatus|onGameCards)[^"]*?"?\s*[:=]\s*[\[\{"]?[^}]{5,300}', re.IGNORECASE)
    seat_pattern = re.compile(rb'"seat(?:s|Info|ID|Num)?"?\s*[:\[]\s*[\[\{]?[^}]{5,500}', re.IGNORECASE)
    pot_pattern = re.compile(rb'"pot"?\s*[:=]\s*\d+')
    bet_pattern = re.compile(rb'"bet"?\s*[:=]\s*\d+')

    # Also look for arrays of small numbers (card encoding: typically 0-51 or suit*13+rank)
    card_array = re.compile(rb'\[(?:\d{1,2},\s*){1,6}\d{1,2}\]')

    results = {
        'cards': set(),
        'json_game': set(),
        'hand_data': set(),
        'game_state': set(),
        'seats': set(),
        'pots': set(),
        'bets': set(),
        'card_arrays': set(),
    }

    regions = 0
    while address < 0x7FFFFFFF:
        result = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address),
                                          ctypes.byref(mbi), ctypes.sizeof(mbi))
        if result == 0:
            break

        if mbi.State == 0x1000 and mbi.Protect in (0x02, 0x04, 0x20, 0x40):
            size = min(mbi.RegionSize, 10 * 1024 * 1024)
            buf = ctypes.create_string_buffer(size)
            bytesRead = ctypes.c_size_t()
            if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(address),
                                           buf, size, ctypes.byref(bytesRead)):
                content = buf.raw[:bytesRead.value]

                for m in card_pattern.finditer(content):
                    ctx = content[max(0,m.start()-50):m.end()+200]
                    results['cards'].add(ctx)

                for m in hand_pattern.finditer(content):
                    results['hand_data'].add(m.group()[:500])

                for m in game_state_pattern.finditer(content):
                    results['game_state'].add(m.group()[:300])

                for m in pot_pattern.finditer(content):
                    ctx = content[max(0,m.start()-100):m.end()+100]
                    results['pots'].add(ctx)

                for m in card_array.finditer(content):
                    arr = m.group()
                    try:
                        nums = json.loads(arr)
                        if all(0 <= n <= 52 for n in nums):
                            results['card_arrays'].add(arr)
                    except:
                        pass

                # Find JSON objects with game-related keys
                for m in json_pattern.finditer(content):
                    try:
                        chunk = m.group()
                        lower = chunk.lower()
                        if any(k in lower for k in [b'card', b'hand', b'board', b'seat', b'pot', b'bet', b'blind', b'dealer', b'stack', b'round', b'phase']):
                            # Try to decode
                            text = chunk.decode('utf-8', errors='replace')
                            if text.count('"') > 4:  # Looks like JSON
                                results['json_game'].add(chunk[:1000])
                    except:
                        pass

                regions += 1

        address += mbi.RegionSize
        if address <= 0:
            break

    kernel32.CloseHandle(handle)

    print(f"Scanned {regions} memory regions\n")

    print("=" * 60)
    print("CARD ARRAYS (potential card encodings)")
    print("=" * 60)
    for s in sorted(results['card_arrays']):
        print(f"  {s.decode()}")

    print(f"\n{'=' * 60}")
    print(f"HAND DATA ({len(results['hand_data'])} matches)")
    print("=" * 60)
    for s in sorted(results['hand_data'])[:30]:
        try:
            print(f"  {s.decode('utf-8', errors='replace')[:200]}")
        except:
            pass

    print(f"\n{'=' * 60}")
    print(f"GAME STATE ({len(results['game_state'])} matches)")
    print("=" * 60)
    for s in sorted(results['game_state'])[:20]:
        try:
            print(f"  {s.decode('utf-8', errors='replace')[:200]}")
        except:
            pass

    print(f"\n{'=' * 60}")
    print(f"POT/BET DATA ({len(results['pots'])} matches)")
    print("=" * 60)
    for s in sorted(results['pots'])[:20]:
        try:
            text = s.decode('utf-8', errors='replace')
            # Filter printable
            clean = re.sub(r'[^\x20-\x7e]', '.', text)
            print(f"  {clean[:200]}")
        except:
            pass

    print(f"\n{'=' * 60}")
    print(f"JSON GAME OBJECTS ({len(results['json_game'])} matches)")
    print("=" * 60)
    for s in sorted(results['json_game'])[:30]:
        try:
            text = s.decode('utf-8', errors='replace')
            print(f"  {text[:300]}")
            print()
        except:
            pass

if __name__ == '__main__':
    pid = find_suprema_pid()
    if pid:
        print(f"Found SupremaPoker PID: {pid}")
        scan_memory(pid)
    else:
        print("SupremaPoker not found")
