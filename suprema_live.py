"""
Suprema Poker Live Monitor v1
Reads game state from process memory via Pomelo/MessagePack decoding.
Outputs to suprema_state.txt every scan cycle.
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

class MBI(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', wt.DWORD), ('RegionSize', ctypes.c_size_t),
        ('State', wt.DWORD), ('Protect', wt.DWORD), ('Type', wt.DWORD),
    ]

# Card decoding - need to figure out correct method
# From gameover data: shared_cards [44, 53, 24] in a NLH game
# From opencard: seat cards [36,38] confirmed as Qh,Ah visually
#
# Testing: card = value where rank = card // 4, suit = card % 4
# suit: 0=c, 1=d, 2=h, 3=s  |  rank: 0=2, 1=3, ..., 11=K, 12=A
# 36: rank=9(J), suit=0(c) -> Jc  -- but we saw Qh!
#
# Method B: suit*13+rank
# 36: suit=2(h), rank=10(Q) -> Qh -- MATCHES!
# 38: suit=2(h), rank=12(A) -> Ah -- MATCHES!
# 44: suit=3(s), rank=5(7) -> 7s
# 53: suit=4(?), rank=1(3) -> ??
# 24: suit=1(d), rank=11(K) -> Kd
#
# So for 53: maybe the encoding wraps or has special values
# 52 = 4*13+0 = "2" of suit 4 (joker/extra?)
# OR 52+ means the card is face-down/unknown
# OR the game uses a short deck where some cards are removed
# and the encoding accounts for that
#
# For now: use method B for 0-51, mark 52+ as unknown

RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['c', 'd', 'h', 's']

def decode_card(n):
    if isinstance(n, float):
        n = int(n)
    if not isinstance(n, int):
        return '??'
    if 0 <= n <= 51:
        return RANKS[n % 13] + SUITS[n // 13]
    # Extended range: try wrapping
    if 52 <= n <= 103:
        # Maybe second deck or different encoding
        # Try: treat as same encoding but with extended suits
        return RANKS[n % 13] + f'x{n // 13}'
    return f'?{n}'

def format_cards(cards):
    if not cards or not isinstance(cards, list):
        return '---'
    decoded = []
    for c in cards:
        if isinstance(c, (int, float)) and c != 0:
            decoded.append(decode_card(c))
        elif isinstance(c, (int, float)) and c == 0:
            decoded.append('__')
    return ' '.join(decoded) if decoded else '---'

def read_msgpack_value(data, pos):
    if pos >= len(data):
        return None, pos
    b = data[pos]
    if b <= 0x7f: return b, pos+1
    if 0xa0 <= b <= 0xbf:
        slen = b - 0xa0
        try: return data[pos+1:pos+1+slen].decode('utf-8','replace'), pos+1+slen
        except: return None, pos+1+slen
    if 0x90 <= b <= 0x9f:
        count = b - 0x90; arr = []; p = pos+1
        for _ in range(count):
            v, p = read_msgpack_value(data, p); arr.append(v)
        return arr, p
    if 0x80 <= b <= 0x8f:
        count = b - 0x80; d = {}; p = pos+1
        for _ in range(count):
            k, p = read_msgpack_value(data, p)
            v, p = read_msgpack_value(data, p)
            if k is not None: d[str(k)] = v
        return d, p
    if b == 0xc0: return None, pos+1
    if b == 0xc2: return False, pos+1
    if b == 0xc3: return True, pos+1
    if b == 0xcc and pos+1 < len(data): return data[pos+1], pos+2
    if b == 0xcd and pos+2 < len(data): return (data[pos+1]<<8)|data[pos+2], pos+3
    if b == 0xce and pos+4 < len(data):
        return (data[pos+1]<<24)|(data[pos+2]<<16)|(data[pos+3]<<8)|data[pos+4], pos+5
    if b == 0xd0 and pos+1 < len(data):
        v = data[pos+1]; return (v-256 if v>=128 else v), pos+2
    if b >= 0xe0: return b-256, pos+1
    if b == 0xd9 and pos+1 < len(data):
        slen = data[pos+1]
        try: return data[pos+2:pos+2+slen].decode('utf-8','replace'), pos+2+slen
        except: return None, pos+2+slen
    if b == 0xda and pos+2 < len(data):
        slen = (data[pos+1]<<8)|data[pos+2]
        try: return data[pos+3:pos+3+slen].decode('utf-8','replace'), pos+3+slen
        except: return None, pos+3+slen
    if b == 0xdc and pos+2 < len(data):
        count = (data[pos+1]<<8)|data[pos+2]; arr = []; p = pos+3
        for _ in range(min(count,200)):
            v, p = read_msgpack_value(data, p); arr.append(v)
        return arr, p
    if b == 0xde and pos+2 < len(data):
        count = (data[pos+1]<<8)|data[pos+2]; d = {}; p = pos+3
        for _ in range(min(count,200)):
            k, p = read_msgpack_value(data, p)
            v, p = read_msgpack_value(data, p)
            if k is not None: d[str(k)] = v
        return d, p
    if b == 0xcb and pos+8 < len(data):
        import struct
        return struct.unpack('>d', data[pos+1:pos+9])[0], pos+9
    if b == 0xca and pos+4 < len(data):
        import struct
        return struct.unpack('>f', data[pos+1:pos+5])[0], pos+5
    return None, pos+1

def find_pid():
    out = subprocess.check_output(
        ['tasklist', '/FI', 'IMAGENAME eq SupremaPoker.exe', '/FO', 'CSV', '/NH'], text=True)
    for line in out.strip().split('\n'):
        if 'SupremaPoker' in line:
            return int(line.strip('"').split('","')[1])
    return None

def scan(handle):
    mbi = MBI(); addr = 0
    state = {
        'room': None,
        'shared_cards': None,
        'my_cards': None,
        'my_uid': 588900,
        'seats': {},
        'pot': None,
        'game_counter': None,
        'dealer': None,
        'game_type': None,
        'events': [],
        'gameover': None,
        'opencard_history': [],
    }

    while addr < 0x7FFFFFFF:
        r = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi))
        if r == 0: break
        if mbi.State == 0x1000 and mbi.Protect in (0x02, 0x04, 0x20, 0x40):
            sz = min(mbi.RegionSize, 10*1024*1024)
            buf = ctypes.create_string_buffer(sz)
            br = ctypes.c_size_t()
            if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, sz, ctypes.byref(br)):
                data = buf.raw[:br.value]

                # Find gameover events (most complete data)
                for m in re.finditer(rb'\xa8gameover\xa4data', data):
                    try:
                        pos = m.end()
                        val, _ = read_msgpack_value(data, pos)
                        if isinstance(val, dict) and 'game_info' in val:
                            gi = val['game_info']
                            if isinstance(gi, dict):
                                sc = gi.get('shared_cards')
                                if isinstance(sc, list) and len(sc) >= 3:
                                    state['shared_cards'] = sc
                                    state['pot'] = gi.get('pot')
                                    state['game_counter'] = gi.get('game_counter')
                                    state['dealer'] = gi.get('dealer_seat')
                                    state['game_type'] = gi.get('type')
                            gr = val.get('game_result', {})
                            if isinstance(gr, dict):
                                seats = gr.get('seats', {})
                                if isinstance(seats, dict):
                                    for uid_str, sdata in seats.items():
                                        if isinstance(sdata, dict):
                                            state['seats'][uid_str] = sdata
                                state['gameover'] = gr
                            state['room'] = val.get('roomID')
                    except:
                        pass

                # Find opencard (hole cards dealt to players)
                for m in re.finditer(rb'\xa8opencard', data):
                    try:
                        pos = m.end()
                        val, _ = read_msgpack_value(data, pos)
                        if isinstance(val, dict):
                            seat = val.get('seat')
                            cards = val.get('cards', [])
                            if isinstance(cards, list) and any(c and c != 0 for c in cards if isinstance(c, (int, float))):
                                state['opencard_history'].append({
                                    'seat': seat, 'cards': cards
                                })
                    except:
                        pass

                # Find game_seat data with our UID
                for m in re.finditer(rb'\xa9game_seat\xce\x00\x08\xfc\x64', data):
                    # 588900 = 0x0008FC64
                    try:
                        # Read the seat map after game_seat key
                        pos = m.start() + 10  # after game_seat
                        val, _ = read_msgpack_value(data, pos)
                        if isinstance(val, int):  # seat number
                            # Read the map
                            pass
                    except:
                        pass

                # Find direct seat.uid.588900 patterns with cards
                for m in re.finditer(rb'\xa4seat(.)\xa3uid\xce\x00\x08\xfc\x64', data):
                    try:
                        seat_num = m.group(1)[0]
                        pos = m.end()
                        # Read remaining fields
                        fields = {}
                        for _ in range(20):
                            if pos >= len(data): break
                            key, pos = read_msgpack_value(data, pos)
                            if not isinstance(key, str): break
                            val, pos = read_msgpack_value(data, pos)
                            fields[key] = val
                            if key == 'stepaway': break
                        if 'cards' in fields:
                            state['my_cards'] = fields['cards']
                    except:
                        pass

        addr += mbi.RegionSize
        if addr <= 0: break

    return state

def display(state):
    ts = datetime.now().strftime('%H:%M:%S')
    lines = []
    lines.append(f"{'='*55}")
    lines.append(f"  SUPREMA LIVE MONITOR  [{ts}]")
    lines.append(f"{'='*55}")
    lines.append(f"  Room: {state['room'] or '?'}")
    lines.append(f"  Game #{state['game_counter'] or '?'}  Type: {state['game_type'] or '?'}  Dealer: seat {state['dealer'] or '?'}")
    lines.append("")

    if state['my_cards']:
        lines.append(f"  >> MY HAND:  {format_cards(state['my_cards'])}")

    if state['shared_cards']:
        lines.append(f"  >> BOARD:    {format_cards(state['shared_cards'])}")

    if state['pot']:
        lines.append(f"  >> POT:      {state['pot']}")

    lines.append("")

    # Show seats from gameover
    if state['seats']:
        lines.append("  SEATS:")
        for uid_str, sdata in state['seats'].items():
            if isinstance(sdata, dict):
                seat = sdata.get('seat', '?')
                cards = format_cards(sdata.get('cards', []))
                chips = sdata.get('chips', '?')
                prize = sdata.get('prize', [])
                me = " <<< ME" if str(uid_str) == str(state['my_uid']) else ""
                lines.append(f"    Seat {seat}: uid={uid_str} cards={cards} chips={chips} prize={prize}{me}")

    # Show opencard history
    if state['opencard_history']:
        lines.append(f"\n  OPENCARD HISTORY ({len(state['opencard_history'])}):")
        for oc in state['opencard_history'][-10:]:
            lines.append(f"    seat={oc['seat']} cards={format_cards(oc['cards'])}")

    lines.append(f"\n  [Ctrl+C to stop | Scan every 3s]")

    output = '\n'.join(lines)
    with open('suprema_state.txt', 'w', encoding='utf-8') as f:
        f.write(output)

    # Print to console
    try:
        sys.stdout.write('\033[2J\033[H')  # clear screen
        sys.stdout.flush()
    except:
        pass
    print(output)

def main():
    pid = find_pid()
    if not pid:
        print("SupremaPoker not running!")
        return

    handle = kernel32.OpenProcess(0x0410, False, pid)
    if not handle:
        print("Cannot open process!")
        return

    print(f"Monitoring PID {pid}...")
    try:
        while True:
            state = scan(handle)
            display(state)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        kernel32.CloseHandle(handle)

if __name__ == '__main__':
    main()
