"""
Suprema Poker Real-Time Traffic Monitor
Hooks OpenSSL via Frida to capture decrypted WebSocket/Pomelo/MessagePack traffic.
"""
import frida
import struct
import sys
import os
import subprocess
import time
import json
from datetime import datetime

# ── Card decoding (Method B: suit*13+rank) ──
RANKS = '23456789TJQKA'
SUITS = 'cdhs'

def dc(n):
    if isinstance(n, float): n = int(n)
    if not isinstance(n, int): return '??'
    if 0 <= n <= 51: return RANKS[n % 13] + SUITS[n // 13]
    return f'?{n}'

def format_cards(cards):
    if not cards or not isinstance(cards, list): return '---'
    out = []
    for c in cards:
        if isinstance(c, (int, float)):
            out.append(dc(int(c)))
    return ' '.join(out) if out else '---'

# ── Msgpack decoder ──
def read_msgpack(data, pos):
    if pos >= len(data): return None, pos
    b = data[pos]
    if b <= 0x7f: return b, pos+1
    if b >= 0xe0: return b-256, pos+1
    if 0xa0 <= b <= 0xbf:
        slen = b - 0xa0
        try: return data[pos+1:pos+1+slen].decode('utf-8','replace'), pos+1+slen
        except: return None, pos+1+slen
    if 0x90 <= b <= 0x9f:
        count = b - 0x90; arr = []; p = pos+1
        for _ in range(count):
            v, p = read_msgpack(data, p); arr.append(v)
        return arr, p
    if 0x80 <= b <= 0x8f:
        count = b - 0x80; d = {}; p = pos+1
        for _ in range(count):
            k, p = read_msgpack(data, p); v, p = read_msgpack(data, p)
            if k is not None: d[str(k)] = v
        return d, p
    if b == 0xc0: return None, pos+1
    if b == 0xc2: return False, pos+1
    if b == 0xc3: return True, pos+1
    if b == 0xcc and pos+1 < len(data): return data[pos+1], pos+2
    if b == 0xcd and pos+2 < len(data): return (data[pos+1]<<8)|data[pos+2], pos+3
    if b == 0xce and pos+4 < len(data):
        return (data[pos+1]<<24)|(data[pos+2]<<16)|(data[pos+3]<<8)|data[pos+4], pos+5
    if b == 0xcf and pos+8 < len(data):
        return int.from_bytes(data[pos+1:pos+9], 'big'), pos+9
    if b == 0xd0 and pos+1 < len(data):
        v = data[pos+1]; return (v-256 if v>=128 else v), pos+2
    if b == 0xd1 and pos+2 < len(data):
        v = (data[pos+1]<<8)|data[pos+2]; return (v-65536 if v>=32768 else v), pos+3
    if b == 0xd2 and pos+4 < len(data):
        v = (data[pos+1]<<24)|(data[pos+2]<<16)|(data[pos+3]<<8)|data[pos+4]
        return (v - 0x100000000 if v >= 0x80000000 else v), pos+5
    if b == 0xd9 and pos+1 < len(data):
        slen = data[pos+1]
        try: return data[pos+2:pos+2+slen].decode('utf-8','replace'), pos+2+slen
        except: return None, pos+2+slen
    if b == 0xda and pos+2 < len(data):
        slen = (data[pos+1]<<8)|data[pos+2]
        try: return data[pos+3:pos+3+slen].decode('utf-8','replace'), pos+3+slen
        except: return None, pos+3+slen
    if b == 0xdb and pos+4 < len(data):
        slen = (data[pos+1]<<24)|(data[pos+2]<<16)|(data[pos+3]<<8)|data[pos+4]
        try: return data[pos+5:pos+5+slen].decode('utf-8','replace'), pos+5+slen
        except: return None, pos+5+slen
    if b == 0xdc and pos+2 < len(data):
        count = (data[pos+1]<<8)|data[pos+2]; arr = []; p = pos+3
        for _ in range(min(count,500)):
            v, p = read_msgpack(data, p); arr.append(v)
        return arr, p
    if b == 0xdd and pos+4 < len(data):
        count = (data[pos+1]<<24)|(data[pos+2]<<16)|(data[pos+3]<<8)|data[pos+4]
        arr = []; p = pos+5
        for _ in range(min(count,500)):
            v, p = read_msgpack(data, p); arr.append(v)
        return arr, p
    if b == 0xde and pos+2 < len(data):
        count = (data[pos+1]<<8)|data[pos+2]; d = {}; p = pos+3
        for _ in range(min(count,500)):
            k, p = read_msgpack(data, p); v, p = read_msgpack(data, p)
            if k is not None: d[str(k)] = v
        return d, p
    if b == 0xdf and pos+4 < len(data):
        count = (data[pos+1]<<24)|(data[pos+2]<<16)|(data[pos+3]<<8)|data[pos+4]
        d = {}; p = pos+5
        for _ in range(min(count,500)):
            k, p = read_msgpack(data, p); v, p = read_msgpack(data, p)
            if k is not None: d[str(k)] = v
        return d, p
    if b == 0xcb and pos+8 < len(data):
        return struct.unpack('>d', data[pos+1:pos+9])[0], pos+9
    if b == 0xca and pos+4 < len(data):
        return struct.unpack('>f', data[pos+1:pos+5])[0], pos+5
    if b == 0xc4 and pos+1 < len(data):
        slen = data[pos+1]; return data[pos+2:pos+2+slen], pos+2+slen
    if b == 0xc5 and pos+2 < len(data):
        slen = (data[pos+1]<<8)|data[pos+2]; return data[pos+3:pos+3+slen], pos+3+slen
    return None, pos+1

# ── Pomelo protocol ──
# Pomelo package types: 1=handshake, 2=handshakeAck, 3=heartbeat, 4=data, 5=kick
# Message types: 0=request, 1=notify, 2=response, 3=push

def decode_pomelo(payload):
    """Decode Pomelo packages from a WebSocket payload"""
    results = []
    pos = 0
    while pos + 4 <= len(payload):
        pkg_type = payload[pos]
        pkg_len = (payload[pos+1] << 16) | (payload[pos+2] << 8) | payload[pos+3]
        pos += 4

        if pkg_type < 1 or pkg_type > 5:
            break
        if pkg_len > len(payload) - pos + 4:
            break

        body = payload[pos:pos+pkg_len]
        pos += pkg_len

        if pkg_type == 3:  # heartbeat
            continue

        result = {}

        if pkg_type == 1:  # handshake (JSON)
            try:
                result['type'] = 'handshake'
                result['data'] = json.loads(body.decode('utf-8'))
            except:
                pass
            results.append(result)
            continue

        if pkg_type == 4 and len(body) > 0:  # data
            flag = body[0]
            msg_type = (flag >> 1) & 0x07
            compress_route = flag & 0x01
            msg_type_str = {0: 'req', 1: 'notify', 2: 'resp', 3: 'push'}.get(msg_type, f'm{msg_type}')
            result['msg_type'] = msg_type_str

            bp = 1

            # msg_id for request/response
            if msg_type in (0, 2):
                msg_id = 0
                while bp < len(body):
                    b = body[bp]
                    msg_id = (msg_id << 7) | (b & 0x7f)
                    bp += 1
                    if b < 128: break
                result['msg_id'] = msg_id

            # route for request/notify/push
            if msg_type in (0, 1, 3):
                if compress_route and bp + 1 < len(body):
                    result['route'] = f'c:{(body[bp]<<8)|body[bp+1]}'
                    bp += 2
                elif bp < len(body):
                    route_len = body[bp]; bp += 1
                    if bp + route_len <= len(body):
                        try: result['route'] = body[bp:bp+route_len].decode('utf-8')
                        except: result['route'] = f'r:{route_len}b'
                        bp += route_len

            # msgpack body
            if bp < len(body):
                try:
                    result['data'], _ = read_msgpack(body, bp)
                except:
                    result['raw_len'] = len(body) - bp

            results.append(result)

    return results

# ── Display ──
MY_UID = 588900

HIGHLIGHT_EVENTS = {
    'gamestart', 'gameover', 'opencard', 'moveturn', 'prompt',
    'updateboard', 'deal', 'showdown', 'insurance',
    'countdown',
}
SKIP_EVENTS = {
    'matchesStatusPushNotify',
}

def print_game_data(data, indent=2):
    """Recursively find and display card/game data"""
    if not isinstance(data, dict):
        return

    prefix = ' ' * indent

    # Cards
    for key in ['cards', 'shared_cards', 'holeCards', 'boardCards']:
        if key in data and isinstance(data[key], list):
            cards = data[key]
            has_cards = any(isinstance(c, int) and c > 0 for c in cards)
            if has_cards:
                print(f"{prefix}{key}: {format_cards(cards)} (raw {cards})")

    # Seat info
    if 'seat' in data and 'uid' in data:
        uid = data.get('uid', '?')
        seat = data.get('seat', '?')
        coins = data.get('coins', '')
        chips = data.get('chips', '')
        me = ' <<ME' if uid == MY_UID else ''
        cards = data.get('cards', [])
        if isinstance(cards, list) and any(isinstance(c, int) and c > 0 for c in cards):
            print(f"{prefix}seat {seat}: uid={uid} {format_cards(cards)} (raw {cards}) coins={coins}{me}")
        elif uid == MY_UID:
            print(f"{prefix}seat {seat}: uid={uid} cards={cards} coins={coins} chips={chips} <<ME")

    # Prompt options
    gp = data.get('gamer_prompt')
    if isinstance(gp, dict):
        opts = []
        for k in ['fold', 'check', 'call', 'raise', 'allin']:
            v = gp.get(k)
            if v is not None:
                if isinstance(v, (int, float)) and v > 0:
                    opts.append(f"{k}={v}")
                elif v is not False:
                    opts.append(k)
        if opts:
            print(f"{prefix}OPTIONS: {' | '.join(opts)}")

    # game_info
    gi = data.get('game_info')
    if isinstance(gi, dict):
        sc = gi.get('shared_cards')
        if isinstance(sc, list) and any(isinstance(c, int) and c > 0 for c in sc):
            print(f"{prefix}BOARD: {format_cards(sc)} (raw {sc})")
        pot = gi.get('pot')
        if pot: print(f"{prefix}POT: {pot}")
        gc = gi.get('game_counter')
        dealer = gi.get('dealer_seat')
        gtype = gi.get('type')
        if gc or dealer is not None or gtype:
            print(f"{prefix}hand #{gc} type={gtype} dealer=seat {dealer}")

    # game_result
    gr = data.get('game_result')
    if isinstance(gr, dict):
        board = gr.get('cards', [])
        if isinstance(board, list) and board:
            print(f"{prefix}BOARD: {format_cards(board)} (raw {board})")
        pots = gr.get('allpots')
        if pots: print(f"{prefix}TOTAL POT: {pots}")
        seats = gr.get('seats')
        if isinstance(seats, (list, dict)):
            items = seats.items() if isinstance(seats, dict) else enumerate(seats)
            for k, s in items:
                if isinstance(s, dict):
                    uid = s.get('uid', '?')
                    cards = s.get('cards', [])
                    coins = s.get('coins', '?')
                    prize = s.get('prize', [])
                    me = ' <<ME' if uid == MY_UID else ''
                    has_cards = isinstance(cards, list) and any(isinstance(c, int) and c > 0 for c in cards)
                    if has_cards or uid == MY_UID:
                        print(f"{prefix}  seat {s.get('seat','?')}: uid={uid} {format_cards(cards)} coins={coins} prize={prize}{me}")

    # game_seat
    gs = data.get('game_seat')
    if isinstance(gs, (list, dict)):
        items = gs.items() if isinstance(gs, dict) else enumerate(gs)
        for k, s in items:
            if isinstance(s, dict):
                uid = s.get('uid', 0)
                cards = s.get('cards', [])
                seat = s.get('seat', '?')
                coins = s.get('coins', '?')
                me = ' <<ME' if uid == MY_UID else ''
                has_cards = isinstance(cards, list) and any(isinstance(c, int) and c > 0 for c in cards)
                if has_cards or uid == MY_UID:
                    print(f"{prefix}  seat {seat}: uid={uid} {format_cards(cards)} coins={coins}{me}")

    # room_status
    rs = data.get('room_status')
    if isinstance(rs, dict):
        phase = rs.get('phase')
        if phase: print(f"{prefix}PHASE: {phase}")

    # countdown
    cd = data.get('countdown')
    if isinstance(cd, dict):
        print(f"{prefix}countdown: seat {cd.get('seat','?')} {cd.get('timeout','?')}s")

    # pot/bet at top level
    if 'pot' in data and not gi:
        print(f"{prefix}POT: {data['pot']}")
    if 'bet' in data:
        print(f"{prefix}BET: {data['bet']}")

# ── Frida JS ──
FRIDA_SCRIPT = """
var mod = Process.findModuleByName('libssl-1_1.dll');
var ssl_read_addr = mod.findExportByName('SSL_read');
var ssl_write_addr = mod.findExportByName('SSL_write');

Interceptor.attach(ssl_read_addr, {
    onEnter: function(args) {
        this.buf = args[1];
    },
    onLeave: function(retval) {
        var n = retval.toInt32();
        if (n > 0) {
            send({d: 0, s: n}, this.buf.readByteArray(n));
        }
    }
});

Interceptor.attach(ssl_write_addr, {
    onEnter: function(args) {
        var n = args[2].toInt32();
        if (n > 0) {
            send({d: 1, s: n}, args[1].readByteArray(n));
        }
    }
});

send({d: 9, m: 'Hooks active'});
"""

def find_pid():
    out = subprocess.check_output(
        ['tasklist', '/FI', 'IMAGENAME eq SupremaPoker.exe', '/FO', 'CSV', '/NH'], text=True)
    for line in out.strip().split('\n'):
        if 'SupremaPoker' in line:
            return int(line.strip('"').split('","')[1])
    return None

def main():
    pid = find_pid()
    if not pid:
        print("SupremaPoker not running!")
        return

    print(f"Attaching to PID {pid}...")

    recv_buf = bytearray()
    send_buf = bytearray()
    msg_count = [0]
    log = open('suprema_traffic.log', 'w', encoding='utf-8')

    session = frida.attach(pid)
    script = session.create_script(FRIDA_SCRIPT)

    def on_message(message, data):
        if message['type'] != 'send':
            if message['type'] == 'error':
                print(f"[ERR] {message.get('description','?')}")
            return

        p = message['payload']
        if p.get('d') == 9:
            print(f"[*] {p['m']}")
            return
        if data is None:
            return

        raw = bytes(data)
        direction = p['d']  # 0=recv, 1=send
        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]

        # Parse WebSocket frame(s) directly from this SSL read/write
        # Server->client: no mask. Client->server: masked.
        if len(raw) < 2:
            return

        b0, b1 = raw[0], raw[1]
        opcode = b0 & 0x0f
        mask = (b1 >> 7) & 1
        plen = b1 & 0x7f
        hdr = 2

        if plen == 126 and len(raw) >= 4:
            plen = (raw[2] << 8) | raw[3]
            hdr = 4
        elif plen == 127 and len(raw) >= 10:
            plen = int.from_bytes(raw[2:10], 'big')
            hdr = 10

        if mask:
            if len(raw) < hdr + 4:
                return
            mask_key = raw[hdr:hdr+4]
            hdr += 4
            payload = bytearray(raw[hdr:])
            for i in range(len(payload)):
                payload[i] ^= mask_key[i % 4]
            payload = bytes(payload)
        else:
            payload = raw[hdr:]

        if opcode not in (1, 2):  # text or binary only
            return

        # Decode Pomelo packages
        pkgs = decode_pomelo(payload)

        for pkg in pkgs:
            d = pkg.get('data')
            route = pkg.get('route', '')
            msg_type = pkg.get('msg_type', '')
            msg_id = pkg.get('msg_id', '')

            # Get event name
            event = ''
            if isinstance(d, dict):
                event = str(d.get('event', d.get('0', '')))

            label = event or route or pkg.get('type', '?')

            # Skip noisy events
            if label in SKIP_EVENTS:
                continue

            msg_count[0] += 1
            arrow = '<--' if direction == 0 else '-->'
            is_highlight = any(e in label.lower() for e in HIGHLIGHT_EVENTS)

            # Format header
            header = f"[{ts}] {arrow}"
            if is_highlight:
                header += f" *** {label.upper()} ***"
            else:
                header += f" {label}"
            if msg_type:
                header += f" ({msg_type})"

            print(header)
            log.write(f"{header}\n")

            if isinstance(d, dict):
                # Always extract game data for highlighted events
                if is_highlight:
                    print_game_data(d)

                # Show compact data for everything
                data_field = d.get('data')
                if isinstance(data_field, dict):
                    print_game_data(data_field)

                    # For small payloads show full data
                    s = str(data_field)
                    if len(s) < 400 and is_highlight:
                        for k, v in data_field.items():
                            if k not in ('game_info', 'game_result', 'game_seat', 'room_status',
                                        'gamer_prompt', 'countdown', 'cards', 'shared_cards'):
                                print(f"  {k}: {v}")

                # For non-game events, just show keys
                elif not is_highlight:
                    keys = list(d.keys())
                    if len(keys) <= 8:
                        compact = {k: v for k, v in d.items() if not isinstance(v, (dict, list)) or len(str(v)) < 100}
                        if len(str(compact)) < 200:
                            print(f"  {compact}")
                        else:
                            print(f"  keys: {keys}")

                log.write(f"  {d}\n")
            elif d is not None:
                print(f"  {d}")
                log.write(f"  {d}\n")

            log.flush()
            sys.stdout.flush()

    script.on('message', on_message)
    script.load()

    print(f"\n{'='*60}")
    print(f"  SUPREMA TRAFFIC MONITOR - REAL-TIME")
    print(f"  Intercepting decrypted WebSocket traffic")
    print(f"  Log: suprema_traffic.log | UID: {MY_UID}")
    print(f"{'='*60}\n")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"\n{msg_count[0]} messages captured.")
    finally:
        try:
            script.unload()
            session.detach()
        except: pass
        log.close()

if __name__ == '__main__':
    main()
