"""
Suprema Poker Memory Monitor - Real-time game state from process RAM
Decodes Pomelo/MessagePack game messages directly from memory.
"""
import ctypes
import ctypes.wintypes as wt
import re
import time
import subprocess
import sys
import os
from datetime import datetime

kernel32 = ctypes.windll.kernel32
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

class MBI(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', wt.DWORD),
        ('RegionSize', ctypes.c_size_t),
        ('State', wt.DWORD),
        ('Protect', wt.DWORD),
        ('Type', wt.DWORD),
    ]

# Card decoding (Method B: suit*13+rank)
RANKS = '23456789TJQKA'
SUITS = 'cdhs'

def dc(n):
    """Decode card number to string"""
    if 0 <= n <= 51:
        return RANKS[n % 13] + SUITS[n // 13]
    return f'?{n}'

def dc_pretty(n):
    """Decode card with suit symbol"""
    syms = {'c': 'C', 'd': 'D', 'h': 'H', 's': 'S'}
    if 0 <= n <= 51:
        rank = RANKS[n % 13]
        suit = SUITS[n // 13]
        return f'{rank}{syms[suit]}'
    return f'?{n}'

def find_pid():
    out = subprocess.check_output(
        ['tasklist', '/FI', 'IMAGENAME eq SupremaPoker.exe', '/FO', 'CSV', '/NH'],
        text=True
    )
    for line in out.strip().split('\n'):
        if 'SupremaPoker' in line:
            return int(line.strip('"').split('","')[1])
    return None

def read_msgpack_value(data, pos):
    """Read a single msgpack value at position. Returns (value, next_pos)"""
    if pos >= len(data):
        return None, pos
    b = data[pos]

    # positive fixint
    if b <= 0x7f:
        return b, pos + 1
    # fixstr
    if 0xa0 <= b <= 0xbf:
        slen = b - 0xa0
        s = data[pos+1:pos+1+slen]
        try:
            return s.decode('utf-8', errors='replace'), pos + 1 + slen
        except:
            return s, pos + 1 + slen
    # fixarray
    if 0x90 <= b <= 0x9f:
        count = b - 0x90
        arr = []
        p = pos + 1
        for _ in range(count):
            val, p = read_msgpack_value(data, p)
            arr.append(val)
        return arr, p
    # fixmap
    if 0x80 <= b <= 0x8f:
        count = b - 0x80
        d = {}
        p = pos + 1
        for _ in range(count):
            key, p = read_msgpack_value(data, p)
            val, p = read_msgpack_value(data, p)
            if key is not None:
                d[str(key)] = val
        return d, p
    # nil
    if b == 0xc0:
        return None, pos + 1
    # false/true
    if b == 0xc2:
        return False, pos + 1
    if b == 0xc3:
        return True, pos + 1
    # uint8
    if b == 0xcc and pos + 1 < len(data):
        return data[pos+1], pos + 2
    # uint16
    if b == 0xcd and pos + 2 < len(data):
        return (data[pos+1] << 8) | data[pos+2], pos + 3
    # uint32
    if b == 0xce and pos + 4 < len(data):
        val = (data[pos+1]<<24)|(data[pos+2]<<16)|(data[pos+3]<<8)|data[pos+4]
        return val, pos + 5
    # int8
    if b == 0xd0 and pos + 1 < len(data):
        v = data[pos+1]
        if v >= 128: v -= 256
        return v, pos + 2
    # negative fixint
    if b >= 0xe0:
        return b - 256, pos + 1
    # str8
    if b == 0xd9 and pos + 1 < len(data):
        slen = data[pos+1]
        s = data[pos+2:pos+2+slen]
        try:
            return s.decode('utf-8', errors='replace'), pos + 2 + slen
        except:
            return str(s), pos + 2 + slen
    # str16
    if b == 0xda and pos + 2 < len(data):
        slen = (data[pos+1] << 8) | data[pos+2]
        s = data[pos+3:pos+3+slen]
        try:
            return s.decode('utf-8', errors='replace'), pos + 3 + slen
        except:
            return str(s), pos + 3 + slen
    # array16
    if b == 0xdc and pos + 2 < len(data):
        count = (data[pos+1] << 8) | data[pos+2]
        arr = []
        p = pos + 3
        for _ in range(min(count, 100)):
            val, p = read_msgpack_value(data, p)
            arr.append(val)
        return arr, p
    # map16
    if b == 0xde and pos + 2 < len(data):
        count = (data[pos+1] << 8) | data[pos+2]
        d = {}
        p = pos + 3
        for _ in range(min(count, 100)):
            key, p = read_msgpack_value(data, p)
            val, p = read_msgpack_value(data, p)
            if key is not None:
                d[str(key)] = val
        return d, p
    # float64
    if b == 0xcb and pos + 8 < len(data):
        import struct
        val = struct.unpack('>d', data[pos+1:pos+9])[0]
        return val, pos + 9
    # float32
    if b == 0xca and pos + 4 < len(data):
        import struct
        val = struct.unpack('>f', data[pos+1:pos+5])[0]
        return val, pos + 5

    return None, pos + 1

def scan_game_state(handle):
    """Scan process memory for current game state"""
    mbi = MBI()
    addr = 0

    state = {
        'my_cards': None,
        'board': None,
        'seats': [],
        'pot': None,
        'room': None,
        'events': [],
        'gameover': [],
        'opencard': [],
        'all_seat_data': [],
    }

    MY_UID = 588900  # Your player ID

    while addr < 0x7FFFFFFF:
        r = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(addr),
                                     ctypes.byref(mbi), ctypes.sizeof(mbi))
        if r == 0:
            break

        if mbi.State == 0x1000 and mbi.Protect in (0x02, 0x04, 0x20, 0x40):
            sz = min(mbi.RegionSize, 10 * 1024 * 1024)
            buf = ctypes.create_string_buffer(sz)
            br = ctypes.c_size_t()
            if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr),
                                           buf, sz, ctypes.byref(br)):
                data = buf.raw[:br.value]

                # Find Pomelo onMsg events
                # Pattern: route.onMsg.event.{eventName}.data.{msgpack data}
                for m in re.finditer(rb'\xa5route\xa5onMsg\xa5event', data):
                    pos = m.end()
                    try:
                        event_name, pos = read_msgpack_value(data, pos)
                        # Read 'data' key
                        data_key, pos = read_msgpack_value(data, pos)
                        if data_key == 'data':
                            msg_data, _ = read_msgpack_value(data, pos)
                            if isinstance(msg_data, dict):
                                state['events'].append({
                                    'event': event_name,
                                    'data': msg_data,
                                    'addr': hex(addr + m.start())
                                })

                                if event_name == 'gameover' and 'game_result' in msg_data:
                                    state['gameover'].append(msg_data)
                    except:
                        pass

                # Find opencard messages (hole cards dealt)
                for m in re.finditer(rb'\xa4data.{0,4}\xa8opencard', data):
                    try:
                        pos = m.end()
                        val, _ = read_msgpack_value(data, pos)
                        if isinstance(val, dict):
                            state['opencard'].append(val)
                    except:
                        pass

                # Find seat data with cards (game state snapshots)
                # Pattern: seat.uid.{N}.coins.{N}.cards.[array]
                for m in re.finditer(rb'\xa4seat', data):
                    try:
                        pos = m.end()
                        # Try to read the surrounding map
                        # Back up to find a map header
                        start = max(0, m.start() - 100)
                        # Try reading from seat key onward
                        seat_val, p1 = read_msgpack_value(data, pos)
                        if isinstance(seat_val, int):
                            # Read next key-value pairs
                            seat_info = {'seat': seat_val}
                            for _ in range(15):
                                if p1 >= len(data):
                                    break
                                key, p1 = read_msgpack_value(data, p1)
                                if key is None or not isinstance(key, str):
                                    break
                                val, p1 = read_msgpack_value(data, p1)
                                seat_info[key] = val
                                if key == 'stepaway':
                                    break

                            if 'cards' in seat_info and isinstance(seat_info['cards'], list):
                                cards = seat_info['cards']
                                if any(isinstance(c, int) and 1 <= c <= 51 for c in cards):
                                    state['all_seat_data'].append(seat_info)
                                    uid = seat_info.get('uid', 0)
                                    if uid == MY_UID:
                                        state['my_cards'] = cards
                    except:
                        pass

                # Find roomID
                for m in re.finditer(rb'\xa6roomID\xa0{0,2}([\xa0-\xbf])', data):
                    try:
                        pos = m.start() + 6  # after 'roomID' key
                        val, _ = read_msgpack_value(data, pos)
                        if isinstance(val, str) and '_' in val:
                            state['room'] = val
                    except:
                        pass

        addr += mbi.RegionSize
        if addr <= 0:
            break

    return state

def format_cards(cards):
    """Format card list to readable string"""
    if not cards:
        return "---"
    result = []
    for c in cards:
        if isinstance(c, int) and 0 <= c <= 51:
            result.append(dc_pretty(c))
        elif isinstance(c, int):
            result.append(f'?{c}')
    return ' '.join(result) if result else "---"

def display(state):
    """Display current state"""
    ts = datetime.now().strftime('%H:%M:%S')

    lines = []
    lines.append(f"===== SUPREMA MEMORY MONITOR [{ts}] =====")
    lines.append(f"Room: {state['room'] or '?'}")
    lines.append("")

    if state['my_cards']:
        lines.append(f">> MY HAND: {format_cards(state['my_cards'])}")

    if state['board']:
        lines.append(f">> BOARD:   {format_cards(state['board'])}")

    lines.append("")

    # Show all seat data with cards
    if state['all_seat_data']:
        lines.append(f"SEATS ({len(state['all_seat_data'])} with cards):")
        seen_uids = set()
        for s in state['all_seat_data']:
            uid = s.get('uid', '?')
            if uid in seen_uids:
                continue
            seen_uids.add(uid)
            cards = format_cards(s.get('cards', []))
            seat = s.get('seat', '?')
            chips = s.get('chips', '?')
            coins = s.get('coins', '?')
            me = " <-- ME" if uid == 588900 else ""
            lines.append(f"  Seat {seat}: uid={uid} cards={cards} chips={chips}{me}")

    # Show game events
    if state['events']:
        lines.append(f"\nEVENTS ({len(state['events'])}):")
        # Show only last 5 unique events
        seen = set()
        for ev in reversed(state['events'][-20:]):
            event = ev['event']
            if event not in seen:
                seen.add(event)
                data_keys = list(ev['data'].keys()) if isinstance(ev['data'], dict) else []
                lines.append(f"  {event}: keys={data_keys}")

    # Show gameover results
    if state['gameover']:
        lines.append(f"\nGAME RESULTS ({len(state['gameover'])}):")
        for go in state['gameover'][-3:]:
            gr = go.get('game_result', {})
            if isinstance(gr, dict):
                allpots = gr.get('allpots', '?')
                board = gr.get('cards', [])
                lines.append(f"  Board: {format_cards(board) if isinstance(board, list) else board}  Pot: {allpots}")
                seats = gr.get('seats', [])
                if isinstance(seats, list):
                    for seat in seats[:9]:
                        if isinstance(seat, dict):
                            uid = seat.get('uid', '?')
                            cards = format_cards(seat.get('cards', []))
                            coins = seat.get('coins', '?')
                            lines.append(f"    uid={uid} cards={cards} coins={coins}")

    # Show opencard
    if state['opencard']:
        lines.append(f"\nOPENCARD ({len(state['opencard'])}):")
        for oc in state['opencard'][-5:]:
            if isinstance(oc, dict):
                seat = oc.get('seat', '?')
                cards = format_cards(oc.get('cards', []))
                lines.append(f"  seat={seat} cards={cards}")

    lines.append(f"\n[Scanning... Ctrl+C to stop]")

    output = '\n'.join(lines)

    # Write to file for safe display (avoid encoding issues)
    with open('suprema_state.txt', 'w', encoding='utf-8') as f:
        f.write(output)

    # Also print (ascii safe)
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except:
        pass
    print(output)

    return output

def main():
    pid = find_pid()
    if not pid:
        print("SupremaPoker not running!")
        return

    print(f"SupremaPoker PID: {pid}")
    print("Opening process...")

    handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        print("Cannot open process!")
        return

    print("Starting monitor (scan every 3s)...\n")

    try:
        while True:
            state = scan_game_state(handle)
            display(state)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        kernel32.CloseHandle(handle)

if __name__ == '__main__':
    main()
