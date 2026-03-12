"""
Suprema Poker Real-Time Traffic Monitor
Hooks OpenSSL SSL_read/SSL_write via Frida to capture decrypted WebSocket traffic.
Decodes Pomelo/MessagePack messages in real-time.
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
    if 0 <= n <= 51:
        return RANKS[n % 13] + SUITS[n // 13]
    return f'?{n}'

def format_cards(cards):
    if not cards or not isinstance(cards, list): return '---'
    return ' '.join(dc(c) for c in cards if isinstance(c, (int, float)))

# ── Msgpack decoder (Python side) ──
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
    if b == 0xcb and pos+8 < len(data):
        return struct.unpack('>d', data[pos+1:pos+9])[0], pos+9
    if b == 0xca and pos+4 < len(data):
        return struct.unpack('>f', data[pos+1:pos+5])[0], pos+5
    return None, pos+1

# ── Pomelo protocol decoder ──
# Pomelo frame: type(1) + id(3 bytes if needed) + route + body(msgpack)
# Types: 0=handshake, 1=handshakeAck, 2=heartbeat, 3=data, 4=kick
# For type 3 (data): compressRoute(1 bit) + msgId(variable) + route + body

def decode_pomelo_frame(data):
    """Decode a Pomelo protocol frame"""
    if len(data) < 4:
        return None

    # Pomelo package header: type(1 byte) + length(3 bytes big-endian)
    pkg_type = data[0]
    pkg_len = (data[1] << 16) | (data[2] << 8) | data[3]

    type_names = {0: 'handshake', 1: 'handshakeAck', 2: 'heartbeat', 3: 'data', 4: 'kick'}
    result = {'type': type_names.get(pkg_type, f'unknown({pkg_type})'), 'length': pkg_len}

    body = data[4:4+pkg_len] if pkg_len > 0 else b''

    if pkg_type == 2:  # heartbeat
        return result

    if pkg_type == 0:  # handshake - JSON
        try:
            import json
            result['data'] = json.loads(body.decode('utf-8'))
        except:
            pass
        return result

    if pkg_type == 3 and len(body) > 0:  # data message
        # Message header: flag(1) + msgId(variable) + route(variable)
        flag = body[0]
        msg_type = (flag >> 1) & 0x07  # 0=request, 1=notify, 2=response, 3=push
        compress_route = flag & 0x01

        type_strs = {0: 'request', 1: 'notify', 2: 'response', 3: 'push'}
        result['msg_type'] = type_strs.get(msg_type, f'msg({msg_type})')

        pos = 1

        # Read message ID (variable length encoding for request/response)
        msg_id = 0
        if msg_type == 0 or msg_type == 2:  # request or response
            while pos < len(body):
                b = body[pos]
                msg_id = (msg_id << 7) | (b & 0x7f)
                pos += 1
                if b < 128:
                    break
            result['msg_id'] = msg_id

        # Read route
        if msg_type == 0 or msg_type == 1 or msg_type == 3:  # has route
            if compress_route:
                if pos + 1 < len(body):
                    route_code = (body[pos] << 8) | body[pos+1]
                    result['route'] = f'compressed({route_code})'
                    pos += 2
            else:
                if pos < len(body):
                    route_len = body[pos]
                    pos += 1
                    if pos + route_len <= len(body):
                        try:
                            result['route'] = body[pos:pos+route_len].decode('utf-8')
                        except:
                            result['route'] = f'bytes({route_len})'
                        pos += route_len

        # Rest is msgpack body
        if pos < len(body):
            try:
                msg_body, _ = read_msgpack(body, pos)
                result['data'] = msg_body
            except:
                result['raw_body_len'] = len(body) - pos

        return result

    return result

def extract_game_info(decoded):
    """Extract interesting game info from decoded message"""
    if not decoded or not isinstance(decoded.get('data'), dict):
        return None

    data = decoded['data']
    route = decoded.get('route', '')
    info = []

    # Check for event-based messages (Pomelo push)
    event = data.get('event') or data.get('0') or ''

    # Cards in any field
    for key in ['cards', 'shared_cards', 'holeCards', 'boardCards', 'myCards']:
        if key in data and isinstance(data[key], list):
            cards = data[key]
            if any(isinstance(c, int) and 0 <= c <= 77 for c in cards):
                info.append(f'{key}: {format_cards(cards)} (raw: {cards})')

    # Nested game_result
    if 'game_result' in data:
        gr = data['game_result']
        if isinstance(gr, dict):
            if 'cards' in gr:
                info.append(f'board: {format_cards(gr["cards"])} (raw: {gr["cards"]})')
            if 'allpots' in gr:
                info.append(f'pot: {gr["allpots"]}')
            seats = gr.get('seats', [])
            if isinstance(seats, (list, dict)):
                items = seats.items() if isinstance(seats, dict) else enumerate(seats)
                for k, s in items:
                    if isinstance(s, dict) and 'cards' in s:
                        uid = s.get('uid', '?')
                        cards = format_cards(s.get('cards', []))
                        me = ' <<ME' if uid == 588900 else ''
                        info.append(f'  seat {s.get("seat","?")}: uid={uid} {cards}{me}')

    # game_info
    if 'game_info' in data:
        gi = data['game_info']
        if isinstance(gi, dict):
            sc = gi.get('shared_cards')
            if isinstance(sc, list):
                info.append(f'board: {format_cards(sc)} (raw: {sc})')

    # opencard
    if 'seat' in data and 'cards' in data:
        seat = data.get('seat')
        cards = data.get('cards')
        if isinstance(cards, list):
            info.append(f'seat {seat} cards: {format_cards(cards)} (raw: {cards})')

    # pot/bet
    if 'pot' in data:
        info.append(f'pot: {data["pot"]}')
    if 'bet' in data:
        info.append(f'bet: {data["bet"]}')
    if 'chips' in data:
        info.append(f'chips: {data["chips"]}')

    return info if info else None

# ── Frida JS script ──
FRIDA_SCRIPT = r"""
'use strict';

// Buffer to accumulate partial reads/writes
var readBuffers = {};
var writeBuffers = {};

// Hook SSL_read in libssl-1_1.dll
var ssl_read = Module.findExportByName('libssl-1_1.dll', 'SSL_read');
var ssl_write = Module.findExportByName('libssl-1_1.dll', 'SSL_write');

if (ssl_read) {
    Interceptor.attach(ssl_read, {
        onEnter: function(args) {
            this.ssl = args[0];
            this.buf = args[1];
            this.num = args[2].toInt32();
        },
        onLeave: function(retval) {
            var nread = retval.toInt32();
            if (nread > 0) {
                var data = this.buf.readByteArray(nread);
                send({type: 'ssl_read', size: nread}, data);
            }
        }
    });
    send({type: 'info', msg: 'Hooked SSL_read @ ' + ssl_read});
} else {
    send({type: 'error', msg: 'SSL_read not found!'});
}

if (ssl_write) {
    Interceptor.attach(ssl_write, {
        onEnter: function(args) {
            this.ssl = args[0];
            this.buf = args[1];
            this.num = args[2].toInt32();
            if (this.num > 0) {
                var data = this.buf.readByteArray(this.num);
                send({type: 'ssl_write', size: this.num}, data);
            }
        }
    });
    send({type: 'info', msg: 'Hooked SSL_write @ ' + ssl_write});
}

send({type: 'info', msg: 'Hooks installed. Monitoring traffic...'});
"""

# ── Main ──
def find_pid():
    out = subprocess.check_output(
        ['tasklist', '/FI', 'IMAGENAME eq SupremaPoker.exe', '/FO', 'CSV', '/NH'], text=True)
    for line in out.strip().split('\n'):
        if 'SupremaPoker' in line:
            return int(line.strip('"').split('","')[1])
    return None

class TrafficMonitor:
    def __init__(self):
        self.recv_buffer = bytearray()
        self.send_buffer = bytearray()
        self.msg_count = 0
        self.log_file = open('suprema_traffic.log', 'a', encoding='utf-8')
        self.interesting_events = []

    def process_pomelo_stream(self, buf, direction):
        """Process accumulated buffer as Pomelo frames"""
        results = []
        while len(buf) >= 4:
            pkg_type = buf[0]
            pkg_len = (buf[1] << 16) | (buf[2] << 8) | buf[3]
            total = 4 + pkg_len

            if pkg_type > 4:  # Invalid type, likely mid-stream
                # Try to find next valid frame header
                found = False
                for i in range(1, min(len(buf), 100)):
                    if buf[i] <= 4:
                        candidate_len = (buf[i+1] << 16 | buf[i+2] << 8 | buf[i+3]) if i+3 < len(buf) else 999999
                        if candidate_len < 65536:  # reasonable
                            del buf[:i]
                            found = True
                            break
                if not found:
                    buf.clear()
                break

            if total > len(buf):
                break  # Wait for more data

            frame = bytes(buf[:total])
            del buf[:total]

            decoded = decode_pomelo_frame(frame)
            if decoded:
                results.append((direction, decoded))

        return results

    def on_message(self, message, data):
        if message['type'] == 'send':
            payload = message['payload']

            if payload['type'] == 'info':
                print(f"[FRIDA] {payload['msg']}")
                return

            if payload['type'] == 'error':
                print(f"[FRIDA ERROR] {payload['msg']}")
                return

            if data is None:
                return

            ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            raw = bytes(data)

            if payload['type'] == 'ssl_read':
                self.recv_buffer.extend(raw)
                frames = self.process_pomelo_stream(self.recv_buffer, 'RECV')
            elif payload['type'] == 'ssl_write':
                self.send_buffer.extend(raw)
                frames = self.process_pomelo_stream(self.send_buffer, 'SEND')
            else:
                return

            for direction, decoded in frames:
                self.msg_count += 1
                msg_type = decoded.get('type', '?')

                # Skip heartbeats for clean output
                if msg_type == 'heartbeat':
                    continue

                route = decoded.get('route', '')
                msg_kind = decoded.get('msg_type', '')

                # Format output
                header = f"[{ts}] {direction} #{self.msg_count} {msg_type}"
                if msg_kind:
                    header += f"/{msg_kind}"
                if route:
                    header += f" route={route}"

                print(f"\n{header}")
                self.log_file.write(f"\n{header}\n")

                # Show data summary
                d = decoded.get('data')
                if isinstance(d, dict):
                    # Show keys
                    keys = list(d.keys())
                    if len(keys) <= 15:
                        print(f"  keys: {keys}")
                    else:
                        print(f"  keys({len(keys)}): {keys[:10]}...")

                    # Extract game-relevant info
                    game_info = extract_game_info(decoded)
                    if game_info:
                        print(f"  --- GAME DATA ---")
                        for line in game_info:
                            print(f"  {line}")
                            self.log_file.write(f"  {line}\n")
                        self.interesting_events.append({
                            'time': ts,
                            'route': route,
                            'info': game_info
                        })

                    # Show full data for small messages or game events
                    game_events = ['gameover', 'opencard', 'gamestart', 'countdown',
                                   'updateseat', 'prompt', 'updateboard', 'deal',
                                   'flop', 'turn', 'river', 'showdown', 'action',
                                   'bet', 'fold', 'call', 'raise', 'check', 'allin']

                    event_name = d.get('event', d.get('0', route))
                    if isinstance(event_name, str) and any(e in event_name.lower() for e in game_events):
                        self._print_data(d, indent=2)
                    elif len(str(d)) < 500:
                        self._print_data(d, indent=2)

                self.log_file.flush()

        elif message['type'] == 'error':
            print(f"[FRIDA ERROR] {message.get('stack', message)}")

    def _print_data(self, data, indent=0):
        prefix = ' ' * indent
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (dict, list)) and len(str(v)) > 100:
                    print(f"{prefix}{k}:")
                    self._print_data(v, indent + 2)
                else:
                    print(f"{prefix}{k}: {v}")
        elif isinstance(data, list):
            if len(data) <= 10:
                print(f"{prefix}{data}")
            else:
                for i, item in enumerate(data[:10]):
                    print(f"{prefix}[{i}] {item}")
                if len(data) > 10:
                    print(f"{prefix}... ({len(data)} total)")
        else:
            print(f"{prefix}{data}")

def main():
    pid = find_pid()
    if not pid:
        print("SupremaPoker not running!")
        return

    print(f"Attaching to SupremaPoker PID {pid}...")

    monitor = TrafficMonitor()

    session = frida.attach(pid)
    script = session.create_script(FRIDA_SCRIPT)
    script.on('message', monitor.on_message)
    script.load()

    print(f"\n{'='*60}")
    print(f"  SUPREMA POKER TRAFFIC MONITOR")
    print(f"  Intercepting decrypted WebSocket traffic in real-time")
    print(f"  Log: suprema_traffic.log")
    print(f"{'='*60}")
    print(f"\nWaiting for traffic... (play a hand!)\n")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"\n\nStopping... {monitor.msg_count} messages captured.")
        print(f"Interesting events: {len(monitor.interesting_events)}")
        for ev in monitor.interesting_events[-10:]:
            print(f"  [{ev['time']}] {ev['route']}: {ev['info']}")
    finally:
        script.unload()
        session.detach()
        monitor.log_file.close()

if __name__ == '__main__':
    main()
