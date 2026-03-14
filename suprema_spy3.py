"""Suprema Protocol Spy v3 - Properly unmasks client WebSocket frames."""
import frida, json, time, sys, os, subprocess, threading
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import msgpack
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'msgpack'])
    import msgpack

def find_pid():
    r = subprocess.check_output(
        'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
        shell=True, text=True
    ).strip()
    for line in r.splitlines():
        if 'SupremaPoker' in line:
            return int(line.split(',')[1].strip('"'))
    return None

pid = find_pid()
if not pid:
    print("SupremaPoker not running!")
    sys.exit(1)

LOG_FILE = os.path.expanduser('~/suprema_spy3.log')
lock = threading.Lock()

# Buffers per direction
send_buf = b''
recv_buf = b''

def parse_ws_frames(buf):
    """Parse WebSocket frames, unmask if needed. Returns (frames, remaining_buf)."""
    frames = []
    pos = 0
    while pos < len(buf):
        if pos + 1 >= len(buf):
            break

        b0 = buf[pos]
        b1 = buf[pos + 1]

        # Check if this looks like a WebSocket frame
        opcode = b0 & 0x0F
        if opcode not in (0x01, 0x02, 0x08, 0x09, 0x0A) and (b0 & 0x80) == 0:
            # Not a valid frame start, skip
            pos += 1
            continue

        masked = (b1 & 0x80) != 0
        payload_len = b1 & 0x7F
        header_len = 2

        if payload_len == 126:
            if pos + 3 >= len(buf):
                break
            payload_len = (buf[pos + 2] << 8) | buf[pos + 3]
            header_len = 4
        elif payload_len == 127:
            if pos + 9 >= len(buf):
                break
            payload_len = int.from_bytes(buf[pos + 2:pos + 10], 'big')
            header_len = 10

        if masked:
            header_len += 4

        total = pos + header_len + payload_len
        if total > len(buf):
            break  # Incomplete frame

        if masked:
            mask_off = header_len - 4
            mask_key = buf[pos + mask_off:pos + mask_off + 4]
            raw_payload = bytearray(buf[pos + header_len:total])
            for i in range(len(raw_payload)):
                raw_payload[i] ^= mask_key[i % 4]
            payload = bytes(raw_payload)
        else:
            payload = buf[pos + header_len:total]

        frames.append(payload)
        pos = total

    return frames, buf[pos:]

def decode_pomelo(payload, direction):
    """Decode Pomelo protocol from unmasked WebSocket payload."""
    if len(payload) < 2:
        return None

    ptype = payload[0]

    # Server push (type 4) - same as suprema_realtime.py
    if ptype == 4 and len(payload) >= 4:
        plen = (payload[1] << 16) | (payload[2] << 8) | payload[3]
        pbody = payload[4:4 + plen]
        if len(pbody) < 2:
            return {'type': 'PUSH', 'raw': payload[:50].hex()}
        rlen = pbody[1]
        off = 2 + rlen
        route = ''
        try:
            route = bytes(pbody[2:2 + rlen]).decode('utf-8', errors='replace')
        except:
            pass
        body = None
        if off < len(pbody):
            try:
                body = msgpack.unpackb(pbody[off:], raw=False)
            except:
                pass
        return {'type': 'PUSH', 'route': route, 'body': body}

    # Client request (type 0) - has reqId
    if ptype == 0 and len(payload) >= 5:
        req_id = (payload[1] << 16) | (payload[2] << 8) | payload[3]
        # After reqId, there might be route info
        # Format varies - try route_len + route + msgpack
        rlen = payload[4]
        if rlen < 100 and 5 + rlen <= len(payload):
            try:
                route = bytes(payload[5:5 + rlen]).decode('utf-8', errors='replace')
            except:
                route = ''
            body = None
            if 5 + rlen < len(payload):
                try:
                    body = msgpack.unpackb(payload[5 + rlen:], raw=False)
                except:
                    pass
            return {'type': 'REQUEST', 'reqId': req_id, 'route': route, 'body': body}
        return {'type': 'REQUEST', 'reqId': req_id, 'raw': payload[4:50].hex()}

    # Client notify (type 1)
    if ptype == 1 and len(payload) >= 3:
        rlen = payload[1]
        if rlen < 100 and 2 + rlen <= len(payload):
            try:
                route = bytes(payload[2:2 + rlen]).decode('utf-8', errors='replace')
            except:
                route = ''
            body = None
            if 2 + rlen < len(payload):
                try:
                    body = msgpack.unpackb(payload[2 + rlen:], raw=False)
                except:
                    pass
            return {'type': 'NOTIFY', 'route': route, 'body': body}

    # Response (type 2)
    if ptype == 2 and len(payload) >= 4:
        req_id = (payload[1] << 16) | (payload[2] << 8) | payload[3]
        body = None
        if len(payload) > 4:
            try:
                body = msgpack.unpackb(payload[4:], raw=False)
            except:
                pass
        return {'type': 'RESPONSE', 'reqId': req_id, 'body': body}

    # Heartbeat / handshake
    if ptype == 3 and len(payload) <= 4:
        return {'type': 'HEARTBEAT'}

    # Unknown - show hex
    return {'type': f'UNK({ptype})', 'hex': payload[:80].hex()}

def log_frame(direction, decoded, raw_len):
    if not decoded:
        return
    if decoded.get('type') == 'HEARTBEAT':
        return

    # Skip noisy server events
    if decoded.get('type') == 'PUSH':
        body = decoded.get('body', {})
        if isinstance(body, dict):
            event = body.get('event', '')
            if event in ('gameinfo', 'countdown', 'matchesStatusPushNotify',
                         'apiClub.clubHandler.jackpot', 'clientPing'):
                return

    ts = time.strftime('%H:%M:%S')
    dtype = decoded['type']

    if direction == 'SEND':
        arrow = '>>>'
        color = '\033[93m'
    else:
        arrow = '<<<'
        color = '\033[96m'

    route = decoded.get('route', '')
    req_id = decoded.get('reqId', '')
    id_str = f" [#{req_id}]" if req_id else ''

    # Header line
    header = f"[{ts}] {arrow} {dtype}{id_str} {route} ({raw_len}b)"
    print(f"{color}{header}\033[0m")

    # Body
    body = decoded.get('body')
    if body:
        try:
            js = json.dumps(body, ensure_ascii=False, default=str)
            if len(js) > 500:
                js = js[:500] + '...'
            print(f"  {js}")
        except:
            pass

    # Raw hex for unknown
    raw_hex = decoded.get('raw', decoded.get('hex', ''))
    if raw_hex:
        print(f"  hex: {raw_hex}")

    print()

    # Log to file
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{header}\n")
        if body:
            try:
                js = json.dumps(body, ensure_ascii=False, default=str)
                f.write(f"  {js}\n")
            except:
                pass
        if raw_hex:
            f.write(f"  hex: {raw_hex}\n")
        f.write("\n")

def process_data(raw, direction):
    global send_buf, recv_buf

    with lock:
        if direction == 'SEND':
            send_buf += raw
            frames, send_buf = parse_ws_frames(send_buf)
        else:
            recv_buf += raw
            frames, recv_buf = parse_ws_frames(recv_buf)

        for frame in frames:
            decoded = decode_pomelo(frame, direction)
            log_frame(direction, decoded, len(frame))

def on_msg(msg, data):
    if msg['type'] != 'send':
        return
    p = msg['payload']
    if p.get('t') == 'ready':
        print("\033[92mHOOK OK!\033[0m")
        return
    if p.get('t') == 'fatal':
        print(f"\033[91mFATAL: {p['e']}\033[0m")
        return
    if not data:
        return
    process_data(bytes(data), p.get('d', 'RECV'))

# Clear log
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write(f"=== Suprema Spy v3 - {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")

print(f"Connecting to SupremaPoker (PID {pid})...")
sess = frida.attach(pid)

js = r'''
try {
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    var ssl_read = sslmod.findExportByName("SSL_read");
    Interceptor.attach(ssl_read, {
        onEnter: function(args) { this.buf = args[1]; },
        onLeave: function(retval) {
            var n = retval.toInt32();
            if (n > 0) send({t:"data", d:"RECV"}, this.buf.readByteArray(n));
        }
    });
    var ssl_write = sslmod.findExportByName("SSL_write");
    Interceptor.attach(ssl_write, {
        onEnter: function(args) {
            var n = args[2].toInt32();
            if (n > 0) send({t:"data", d:"SEND"}, args[1].readByteArray(n));
        }
    });
    send({t:"ready"});
} catch(e) { send({t:"fatal", e:e.toString()}); }
'''

sc = sess.create_script(js)
sc.on('message', on_msg)
sc.load()

print("\033[92m")
print("=" * 60)
print("  SUPREMA SPY v3 - UNMASKED")
print(f"  Log: {LOG_FILE}")
print("  >>> AMARELO = Client requests (UNMASKED)")
print("  <<< AZUL    = Server responses")
print("  SAI e ENTRA numa mesa!")
print("=" * 60)
print("\033[0m")

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    pass

print("\nStopping...")
sc.unload()
sess.detach()
