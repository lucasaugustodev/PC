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
    # bin8
    if b == 0xc4 and pos+1 < len(data):
        slen = data[pos+1]
        return data[pos+2:pos+2+slen], pos+2+slen
    # bin16
    if b == 0xc5 and pos+2 < len(data):
        slen = (data[pos+1]<<8)|data[pos+2]
        return data[pos+3:pos+3+slen], pos+3+slen
    return None, pos+1

# ── WebSocket frame parser ──
def parse_ws_frames(buf):
    """Parse WebSocket frames from buffer. Returns list of (payload, consumed_bytes)"""
    frames = []
    pos = 0
    while pos + 2 <= len(buf):
        b0 = buf[pos]
        b1 = buf[pos+1]
        # fin = (b0 >> 7) & 1
        opcode = b0 & 0x0f
        masked = (b1 >> 7) & 1
        payload_len = b1 & 0x7f

        hdr_size = 2
        if payload_len == 126:
            if pos + 4 > len(buf): break
            payload_len = (buf[pos+2] << 8) | buf[pos+3]
            hdr_size = 4
        elif payload_len == 127:
            if pos + 10 > len(buf): break
            payload_len = int.from_bytes(buf[pos+2:pos+10], 'big')
            hdr_size = 10

        mask_key = None
        if masked:
            if pos + hdr_size + 4 > len(buf): break
            mask_key = buf[pos+hdr_size:pos+hdr_size+4]
            hdr_size += 4

        total = hdr_size + payload_len
        if pos + total > len(buf):
            break

        payload = bytearray(buf[pos+hdr_size:pos+total])
        if mask_key:
            for i in range(len(payload)):
                payload[i] ^= mask_key[i % 4]

        frames.append((opcode, bytes(payload)))
        pos += total

    return frames, pos

# ── Pomelo protocol ──
def decode_pomelo(payload):
    """Decode Pomelo package(s) from WebSocket payload"""
    results = []
    pos = 0
    while pos + 4 <= len(payload):
        pkg_type = payload[pos]
        pkg_len = (payload[pos+1] << 16) | (payload[pos+2] << 8) | payload[pos+3]
        pos += 4

        if pkg_type > 4 or pkg_len > len(payload) - pos + 4:
            break

        body = payload[pos:pos+pkg_len]
        pos += pkg_len

        type_names = {0: 'handshake', 1: 'ack', 2: 'heartbeat', 3: 'data', 4: 'kick'}
        result = {'pkg_type': type_names.get(pkg_type, f'?{pkg_type}')}

        if pkg_type == 2:  # heartbeat
            results.append(result)
            continue

        if pkg_type == 0:  # handshake = JSON
            try:
                import json
                result['data'] = json.loads(body.decode('utf-8'))
            except:
                pass
            results.append(result)
            continue

        if pkg_type == 3 and len(body) > 0:  # data
            flag = body[0]
            msg_type = (flag >> 1) & 0x07
            compress_route = flag & 0x01
            type_strs = {0: 'req', 1: 'notify', 2: 'resp', 3: 'push'}
            result['msg_type'] = type_strs.get(msg_type, f'm{msg_type}')

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

# ── Display helpers ──
MY_UID = 588900

GAME_EVENTS = {
    'gamestart', 'gameover', 'opencard', 'countdown', 'moveturn',
    'updateseat', 'updategamer', 'prompt', 'updateboard', 'deal',
    'flop', 'turn', 'river', 'showdown', 'action', 'allin',
    'sitdown', 'standup', 'ready', 'leave', 'buyin', 'insurance',
}

def show_game_data(data, route='', event=''):
    """Extract and display interesting game data"""
    if not isinstance(data, dict):
        return

    lines = []
    name = event or route

    # opencard: seat cards
    if 'seat' in data and 'cards' in data and isinstance(data['cards'], list):
        seat = data.get('seat', '?')
        cards = data['cards']
        raw = cards[:]
        decoded = format_cards(cards)
        uid = data.get('uid', '')
        me = ' <<ME' if uid == MY_UID else ''
        lines.append(f"  CARDS seat {seat}: {decoded} (raw {raw}){me}")

    # game_info: board, pot, dealer
    gi = data.get('game_info')
    if isinstance(gi, dict):
        sc = gi.get('shared_cards')
        if isinstance(sc, list) and any(isinstance(c, int) and c > 0 for c in sc):
            lines.append(f"  BOARD: {format_cards(sc)} (raw {sc})")
        pot = gi.get('pot')
        if pot: lines.append(f"  POT: {pot}")
        gc = gi.get('game_counter')
        if gc: lines.append(f"  HAND #{gc}")
        dealer = gi.get('dealer_seat')
        if dealer is not None: lines.append(f"  DEALER: seat {dealer}")

    # game_result
    gr = data.get('game_result')
    if isinstance(gr, dict):
        board = gr.get('cards', [])
        if isinstance(board, list) and board:
            lines.append(f"  BOARD: {format_cards(board)} (raw {board})")
        pots = gr.get('allpots')
        if pots: lines.append(f"  TOTAL POT: {pots}")
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
                    if isinstance(cards, list) and any(isinstance(c, int) and c > 0 for c in cards):
                        lines.append(f"    seat {s.get('seat','?')}: uid={uid} {format_cards(cards)} (raw {cards}) coins={coins} prize={prize}{me}")

    # game_seat: player positions & cards
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
                if isinstance(cards, list) and any(isinstance(c, int) and c > 0 for c in cards):
                    lines.append(f"    seat {seat}: uid={uid} {format_cards(cards)} (raw {cards}){me}")
                elif uid == MY_UID:
                    lines.append(f"    seat {seat}: uid={uid} cards={cards} coins={coins} <<ME")

    # prompt: action options
    gp = data.get('gamer_prompt')
    if isinstance(gp, dict):
        opts = []
        for k in ['fold', 'check', 'call', 'raise', 'allin']:
            v = gp.get(k)
            if v is not None and v is not False:
                if isinstance(v, (int, float)) and v > 0:
                    opts.append(f"{k}={v}")
                elif v is True or v == 0 or v is None:
                    opts.append(k)
        if opts:
            lines.append(f"  OPTIONS: {' | '.join(opts)}")

    # countdown
    cd = data.get('countdown')
    if isinstance(cd, dict):
        seat = cd.get('seat', '?')
        timeout = cd.get('timeout', '?')
        lines.append(f"  COUNTDOWN: seat {seat}, {timeout}s")

    # room_status
    rs = data.get('room_status')
    if isinstance(rs, dict):
        phase = rs.get('phase', '?')
        lines.append(f"  PHASE: {phase}")

    # direct cards field
    if 'cards' in data and isinstance(data['cards'], list) and 'seat' not in data and 'game_result' not in data:
        cards = data['cards']
        if any(isinstance(c, int) and c > 0 for c in cards):
            lines.append(f"  CARDS: {format_cards(cards)} (raw {cards})")

    # pot/bet at top level
    if 'pot' in data and not gi:
        lines.append(f"  POT: {data['pot']}")
    if 'bet' in data:
        lines.append(f"  BET: {data['bet']}")

    for line in lines:
        print(line)

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
            send({d: 'R', s: n}, this.buf.readByteArray(n));
        }
    }
});

Interceptor.attach(ssl_write_addr, {
    onEnter: function(args) {
        var n = args[2].toInt32();
        if (n > 0) {
            send({d: 'W', s: n}, args[1].readByteArray(n));
        }
    }
});

send({d: 'I', m: 'SSL hooks active'});
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
        if 'I' == p.get('d'):
            print(f"[*] {p['m']}")
            return
        if data is None:
            return

        raw = bytes(data)
        direction = p['d']
        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]

        if direction == 'R':
            recv_buf.extend(raw)
            buf = recv_buf
        else:
            send_buf.extend(raw)
            buf = send_buf

        # Parse WebSocket frames
        frames, consumed = parse_ws_frames(buf)
        if consumed > 0:
            del buf[:consumed]

        for opcode, payload in frames:
            if opcode == 0x08:  # close
                continue
            if opcode == 0x09 or opcode == 0x0a:  # ping/pong
                continue

            # Decode Pomelo packages
            pkgs = decode_pomelo(payload)
            for pkg in pkgs:
                pkg_type = pkg.get('pkg_type', '?')

                if pkg_type == 'heartbeat':
                    continue

                msg_count[0] += 1
                arrow = '<--' if direction == 'R' else '-->'
                route = pkg.get('route', '')
                msg_type = pkg.get('msg_type', '')
                msg_id = pkg.get('msg_id', '')

                # Get event name from data
                d = pkg.get('data')
                event = ''
                if isinstance(d, dict):
                    event = d.get('event', d.get('0', ''))
                    if isinstance(event, str):
                        event = event
                    else:
                        event = ''

                # Header
                label = event or route or pkg_type
                is_game = any(g in label.lower() for g in GAME_EVENTS) if label else False

                # Color coding via simple markers
                if is_game:
                    marker = '***'
                else:
                    marker = '   '

                header = f"[{ts}] {arrow} {marker} {label}"
                if msg_type: header += f" ({msg_type})"
                if msg_id: header += f" id={msg_id}"

                print(header)
                log.write(f"{header}\n")

                # Show data
                if isinstance(d, dict):
                    # Always show game-relevant data
                    if is_game:
                        show_game_data(d, route, event)

                    # For non-game events, show compact summary
                    elif len(str(d)) < 300:
                        keys = list(d.keys())
                        print(f"  {d}")
                    else:
                        keys = list(d.keys())
                        print(f"  keys: {keys}")

                    # Log full data
                    log.write(f"  {d}\n")
                elif d is not None:
                    print(f"  {d}")
                    log.write(f"  {d}\n")

                log.flush()

    script.on('message', on_message)
    script.load()

    print(f"\n{'='*60}")
    print(f"  SUPREMA TRAFFIC MONITOR - REAL-TIME")
    print(f"  Log: suprema_traffic.log")
    print(f"  *** = game events")
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
