"""Targeted scan: find active game state, card encodings, player data"""
import ctypes
import ctypes.wintypes as wt
import re
import json
import struct

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
            return int(line.strip('"').split('","')[1])
    return None

# Card decoding: Suprema likely uses suit*13+rank or rank*4+suit
# Common encodings:
# Method A: card = rank*4 + suit (0=clubs,1=diamonds,2=hearts,3=spades)
# Method B: card = suit*13 + rank
# 36 could be: 36/4=9(rank9), 36%4=0 -> 9c  OR  36/13=2(hearts), 36%13=10 -> Jh
# 38 could be: 38/4=9(rank9), 38%4=2 -> 9h  OR  38/13=2(hearts), 38%13=12 -> Kh

RANKS_A = ['2','3','4','5','6','7','8','9','T','J','Q','K','A']
SUITS_A = ['c','d','h','s']

def decode_card_methodA(n):
    """rank*4+suit"""
    if n < 0 or n > 51: return f"?{n}"
    return RANKS_A[n // 4] + SUITS_A[n % 4]

def decode_card_methodB(n):
    """suit*13+rank"""
    if n < 0 or n > 51: return f"?{n}"
    return RANKS_A[n % 13] + SUITS_A[n // 13]

def scan_memory(pid):
    handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        print("Cannot open process"); return

    mbi = MEMORY_BASIC_INFORMATION()
    address = 0

    # Search for:
    # 1. roomID / tableID strings with numbers
    # 2. Card number sequences
    # 3. Player data with chips/stack
    # 4. Serialized game state (MessagePack or JSON)

    room_pat = re.compile(rb'"(?:roomID|tableID|matchID|gameID|roundID)":\s*\d+')
    player_pat = re.compile(rb'"(?:playerID|userID|userName|nickName|stack|chip|coin|balance)":\s*["\d]')
    card_json_pat = re.compile(rb'"(?:cards?|hand|holeCards?|boardCards?|communityCards?|myCards?)"\s*:\s*\[[\d,\s]+\]')
    action_pat = re.compile(rb'"(?:action|act|type|phase|state|stage|round|street)":\s*["\d]')

    # Look for MessagePack encoded data near card-like bytes
    # In Pomelo+notepack, data is msgpack encoded

    # Also look for any number arrays that could be cards
    num_array_pat = re.compile(rb'\[(\d{1,2}(?:,\d{1,2}){1,8})\]')

    all_rooms = set()
    all_players = set()
    all_card_json = set()
    all_actions = set()
    all_num_arrays = set()

    # Big JSON objects (game state)
    big_json = set()
    big_json_pat = re.compile(rb'\{[^{}]{50,5000}(?:card|hand|board|seat|blind|dealer|stack|chip|pot|bet|round)[^{}]{10,5000}\}', re.IGNORECASE)

    while address < 0x7FFFFFFF:
        result = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address),
                                          ctypes.byref(mbi), ctypes.sizeof(mbi))
        if result == 0: break

        if mbi.State == 0x1000 and mbi.Protect in (0x02, 0x04, 0x20, 0x40):
            size = min(mbi.RegionSize, 10 * 1024 * 1024)
            buf = ctypes.create_string_buffer(size)
            bytesRead = ctypes.c_size_t()
            if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(address),
                                           buf, size, ctypes.byref(bytesRead)):
                content = buf.raw[:bytesRead.value]

                for m in room_pat.finditer(content):
                    ctx = content[max(0,m.start()-100):m.end()+300]
                    all_rooms.add(ctx)

                for m in player_pat.finditer(content):
                    ctx = content[max(0,m.start()-50):m.end()+400]
                    all_players.add(ctx)

                for m in card_json_pat.finditer(content):
                    all_card_json.add(m.group())

                for m in action_pat.finditer(content):
                    ctx = content[max(0,m.start()-100):m.end()+200]
                    lower = ctx.lower()
                    if any(k in lower for k in [b'card', b'seat', b'bet', b'pot', b'fold', b'call', b'raise', b'blind', b'hand']):
                        all_actions.add(ctx)

                for m in num_array_pat.finditer(content):
                    try:
                        nums = [int(x) for x in m.group(1).split(b',')]
                        if all(0 <= n <= 51 for n in nums) and len(nums) >= 2:
                            all_num_arrays.add(m.group())
                    except:
                        pass

                for m in big_json_pat.finditer(content):
                    big_json.add(m.group()[:2000])

        address += mbi.RegionSize
        if address <= 0: break

    kernel32.CloseHandle(handle)

    print("=" * 60)
    print("CARD JSON FIELDS")
    print("=" * 60)
    for s in sorted(all_card_json):
        text = s.decode('utf-8', errors='replace')
        print(f"  {text}")
        # Try to extract and decode the numbers
        nums_match = re.search(r'\[([\d,\s]+)\]', text)
        if nums_match:
            nums = [int(x.strip()) for x in nums_match.group(1).split(',')]
            print(f"    Method A (rank*4+suit): {[decode_card_methodA(n) for n in nums]}")
            print(f"    Method B (suit*13+rank): {[decode_card_methodB(n) for n in nums]}")

    print(f"\n{'=' * 60}")
    print(f"NUMBER ARRAYS (0-51 range, possible cards) - {len(all_num_arrays)} found")
    print("=" * 60)
    for s in sorted(all_num_arrays):
        text = s.decode()
        nums = [int(x) for x in re.findall(r'\d+', text)]
        print(f"  {text}")
        print(f"    A: {[decode_card_methodA(n) for n in nums]}")
        print(f"    B: {[decode_card_methodB(n) for n in nums]}")

    print(f"\n{'=' * 60}")
    print(f"ROOM/TABLE DATA - {len(all_rooms)} found")
    print("=" * 60)
    for s in sorted(all_rooms)[:10]:
        try:
            clean = re.sub(rb'[^\x20-\x7e]', b'.', s)
            print(f"  {clean.decode('ascii', errors='replace')[:300]}")
        except: pass

    print(f"\n{'=' * 60}")
    print(f"PLAYER DATA - {len(all_players)} found")
    print("=" * 60)
    for s in sorted(all_players)[:15]:
        try:
            clean = re.sub(rb'[^\x20-\x7e]', b'.', s)
            print(f"  {clean.decode('ascii', errors='replace')[:300]}")
        except: pass

    print(f"\n{'=' * 60}")
    print(f"BIG GAME STATE OBJECTS - {len(big_json)} found")
    print("=" * 60)
    for s in sorted(big_json)[:10]:
        try:
            text = s.decode('utf-8', errors='replace')
            print(f"  {text[:500]}")
            print()
        except: pass

if __name__ == '__main__':
    pid = find_suprema_pid()
    if pid:
        print(f"SupremaPoker PID: {pid}")
        scan_memory(pid)
    else:
        print("SupremaPoker not running")
