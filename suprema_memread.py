"""
Suprema Poker Memory Reader - Real-time game state from RAM
Reads hand cards, board cards, pot, and player data directly from process memory.
"""
import ctypes
import ctypes.wintypes as wt
import re
import time
import json
import subprocess
import os
from datetime import datetime

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

# Card decoding
RANKS = ['2','3','4','5','6','7','8','9','T','J','Q','K','A']
SUITS = ['c','d','h','s']
SUIT_SYMBOLS = {'c': '\u2663', 'd': '\u2666', 'h': '\u2665', 's': '\u2660'}

def decode_card(n):
    """Decode card number to human readable. Testing both methods."""
    if n < 0 or n > 51:
        return f"?{n}"
    # Method B seems correct based on [36,38] -> Qh, Ah
    rank = RANKS[n % 13]
    suit = SUITS[n // 13]
    return rank + suit

def card_pretty(card_str):
    """Make card string pretty with suit symbols"""
    if len(card_str) < 2:
        return card_str
    rank = card_str[:-1]
    suit = card_str[-1]
    symbol = SUIT_SYMBOLS.get(suit, suit)
    return f"{rank}{symbol}"

def find_pid():
    out = subprocess.check_output(
        ['tasklist', '/FI', 'IMAGENAME eq SupremaPoker.exe', '/FO', 'CSV', '/NH'],
        text=True
    )
    for line in out.strip().split('\n'):
        if 'SupremaPoker' in line:
            return int(line.strip('"').split('","')[1])
    return None

def read_process_memory(handle):
    """Read all readable memory regions and return combined data with addresses"""
    mbi = MEMORY_BASIC_INFORMATION()
    address = 0
    regions = []

    while address < 0x7FFFFFFF:
        result = kernel32.VirtualQueryEx(
            handle, ctypes.c_void_p(address),
            ctypes.byref(mbi), ctypes.sizeof(mbi)
        )
        if result == 0:
            break

        if mbi.State == 0x1000 and mbi.Protect in (0x02, 0x04, 0x20, 0x40):
            size = min(mbi.RegionSize, 10 * 1024 * 1024)
            buf = ctypes.create_string_buffer(size)
            bytesRead = ctypes.c_size_t()
            if kernel32.ReadProcessMemory(
                handle, ctypes.c_void_p(address),
                buf, size, ctypes.byref(bytesRead)
            ):
                regions.append((address, buf.raw[:bytesRead.value]))

        address += mbi.RegionSize
        if address <= 0:
            break

    return regions

def extract_game_state(regions):
    """Extract all game-relevant data from memory regions"""
    state = {
        'hand_cards': [],
        'board_cards': [],
        'card_arrays': [],
        'players': [],
        'room_info': {},
        'game_data': [],
        'pot': None,
        'raw_matches': [],
    }

    # Patterns
    num_array_pat = re.compile(rb'\[(\d{1,2}(?:,\d{1,2}){1,8})\]')
    room_pat = re.compile(rb'"roomID"\s*:\s*"([^"]+)"')
    player_id_pat = re.compile(rb'"playerID"\s*:\s*(\d+)')
    match_id_pat = re.compile(rb'"matchID"\s*:\s*(\d+)')

    # Look for Pomelo response data - MessagePack encoded
    # After decoding, card data appears as small integer arrays
    # Focus on finding [N,N] patterns (2 cards = hole cards) and [N,N,N,N?,N?] (board)

    all_card_arrays = {}  # dedup

    for base_addr, content in regions:
        # Find number arrays in the 0-51 card range
        for m in num_array_pat.finditer(content):
            try:
                nums = [int(x) for x in m.group(1).split(b',')]
                if all(0 <= n <= 51 for n in nums) and any(n > 0 for n in nums):
                    key = tuple(nums)
                    if key not in all_card_arrays:
                        all_card_arrays[key] = base_addr + m.start()
            except:
                pass

        # Extract room/player info
        for m in room_pat.finditer(content):
            room_id = m.group(1).decode('utf-8', errors='replace')
            if '_' in room_id:  # Active game room
                state['room_info']['roomID'] = room_id

        # Find JSON-like game data
        # Look for structures with game state
        for m in re.finditer(rb'"(?:cards|hand|holeCards|boardCards)":\[[\d,]+\]', content):
            state['raw_matches'].append(m.group().decode('utf-8', errors='replace'))

        # Look for the actual Pomelo protocol messages
        # These are typically msgpack-encoded, but might also be in JS object form
        for m in re.finditer(rb'(?:cards|myCards|holeCards)\x00{0,4}[\x92-\x95]([\x00-\x33]{2,5})', content):
            # msgpack fixarray(2-5) followed by card bytes
            arr_data = m.group(1)
            cards = list(arr_data)
            if all(0 <= c <= 51 for c in cards):
                state['hand_cards'].append(cards)

        # Look for board cards pattern in msgpack
        for m in re.finditer(rb'(?:board|community)\x00{0,4}[\x93-\x95]([\x00-\x33]{3,5})', content):
            arr_data = m.group(1)
            cards = list(arr_data)
            if all(0 <= c <= 51 for c in cards):
                state['board_cards'].append(cards)

    # Classify card arrays
    for nums, addr in sorted(all_card_arrays.items(), key=lambda x: x[1]):
        decoded_b = [decode_card(n) for n in nums]
        entry = {
            'raw': list(nums),
            'decoded': decoded_b,
            'addr': hex(addr),
            'count': len(nums),
        }
        state['card_arrays'].append(entry)

    return state

def display_state(state, prev_state=None):
    """Display current game state"""
    ts = datetime.now().strftime('%H:%M:%S')
    os.system('cls' if os.name == 'nt' else 'clear')

    print(f"{'=' * 50}")
    print(f"  SUPREMA POKER MEMORY READER  [{ts}]")
    print(f"{'=' * 50}")

    if state['room_info']:
        print(f"\n  Room: {state['room_info'].get('roomID', '?')}")

    print(f"\n  Card Arrays Found ({len(state['card_arrays'])} total):")
    print(f"  {'─' * 45}")

    # Show 2-card arrays (likely hole cards)
    hole_cards = [a for a in state['card_arrays'] if a['count'] == 2]
    board_cards_3 = [a for a in state['card_arrays'] if a['count'] == 3]
    board_cards_4 = [a for a in state['card_arrays'] if a['count'] == 4]
    board_cards_5 = [a for a in state['card_arrays'] if a['count'] == 5]
    other = [a for a in state['card_arrays'] if a['count'] not in (2,3,4,5)]

    if hole_cards:
        print(f"\n  HOLE CARDS (2-card arrays):")
        for a in hole_cards:
            pretty = ' '.join(card_pretty(c) for c in a['decoded'])
            print(f"    {pretty:20s}  raw={a['raw']}  @{a['addr']}")

    if board_cards_3:
        print(f"\n  FLOP candidates (3-card arrays):")
        for a in board_cards_3:
            pretty = ' '.join(card_pretty(c) for c in a['decoded'])
            print(f"    {pretty:30s}  raw={a['raw']}  @{a['addr']}")

    if board_cards_4:
        print(f"\n  TURN candidates (4-card arrays):")
        for a in board_cards_4:
            pretty = ' '.join(card_pretty(c) for c in a['decoded'])
            print(f"    {pretty:30s}  raw={a['raw']}  @{a['addr']}")

    if board_cards_5:
        print(f"\n  RIVER candidates (5-card arrays):")
        for a in board_cards_5:
            pretty = ' '.join(card_pretty(c) for c in a['decoded'])
            print(f"    {pretty:30s}  raw={a['raw']}  @{a['addr']}")

    if other:
        print(f"\n  OTHER arrays:")
        for a in other[:10]:
            pretty = ' '.join(card_pretty(c) for c in a['decoded'])
            print(f"    [{a['count']}] {pretty:30s}  raw={a['raw']}")

    if state['raw_matches']:
        print(f"\n  RAW CARD JSON:")
        for m in state['raw_matches']:
            print(f"    {m}")

    if state['hand_cards']:
        print(f"\n  MSGPACK HAND CARDS:")
        for cards in state['hand_cards']:
            decoded = [card_pretty(decode_card(c)) for c in cards]
            print(f"    {' '.join(decoded)}  raw={cards}")

    if state['board_cards']:
        print(f"\n  MSGPACK BOARD CARDS:")
        for cards in state['board_cards']:
            decoded = [card_pretty(decode_card(c)) for c in cards]
            print(f"    {' '.join(decoded)}  raw={cards}")

    print(f"\n  Press Ctrl+C to stop")
    return state

def main():
    pid = find_pid()
    if not pid:
        print("SupremaPoker not running!")
        return

    print(f"SupremaPoker PID: {pid}")
    print("Starting memory reader... (scanning every 2 seconds)")

    handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        print("Cannot open process!")
        return

    prev_state = None
    try:
        while True:
            regions = read_process_memory(handle)
            state = extract_game_state(regions)
            prev_state = display_state(state, prev_state)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        kernel32.CloseHandle(handle)

if __name__ == '__main__':
    main()
