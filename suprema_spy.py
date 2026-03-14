"""Suprema Protocol Spy - Captures SEND + RECV to map join/room requests."""
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

print(f"Found SupremaPoker PID: {pid}")

LOG_FILE = os.path.expanduser('~/suprema_spy.log')
lock = threading.Lock()
recv_buf = b''
send_buf = b''

# Pomelo message types
POMELO_TYPES = {0: 'REQUEST', 1: 'NOTIFY', 2: 'RESPONSE', 3: 'PUSH', 4: 'PUSH2'}

# Known route mappings (built as we discover them)
request_routes = {}  # reqId -> route

def parse_pomelo_frames(raw, direction):
    """Parse WebSocket + Pomelo frames from raw SSL data."""
    results = []
    pos = 0
    while pos < len(raw):
        if pos >= len(raw):
            break

        opcode = raw[pos]
        # WebSocket binary frame (0x82) or text frame (0x81) or masked (client->server)
        is_ws = opcode in (0x81, 0x82)
        is_masked_ws = opcode in (0x01, 0x02)  # without FIN sometimes

        if not is_ws and not is_masked_ws:
            pos += 1
            continue

        if pos + 1 >= len(raw):
            break

        b1 = raw[pos + 1]
        masked = (b1 & 0x80) != 0
        payload_len = b1 & 0x7F
        offset = 2

        if payload_len == 126:
            if pos + 3 >= len(raw):
                break
            payload_len = (raw[pos + 2] << 8) | raw[pos + 3]
            offset = 4
        elif payload_len == 127:
            if pos + 9 >= len(raw):
                break
            payload_len = int.from_bytes(raw[pos + 2:pos + 10], 'big')
            offset = 10

        mask_key = None
        if masked:
            if pos + offset + 3 >= len(raw):
                break
            mask_key = raw[pos + offset:pos + offset + 4]
            offset += 4

        total = offset + payload_len
        if pos + total > len(raw):
            break

        payload = bytearray(raw[pos + offset:pos + total])

        # Unmask if needed
        if mask_key:
            for i in range(len(payload)):
                payload[i] ^= mask_key[i % 4]

        pos += total

        # Parse Pomelo protocol
        if len(payload) < 1:
            continue

        ptype = payload[0]

        if ptype in (0, 1) and len(payload) >= 5:
            # REQUEST (0) or NOTIFY (1) - client -> server
            # Format: type(1) | reqId(3 for request) | route_len(1) | route | msgpack_body
            if ptype == 0:
                # Request: type(1) + reqId(3) + ...
                req_id = (payload[1] << 16) | (payload[2] << 8) | payload[3]
                if len(payload) < 5:
                    continue
                route_len = payload[4]
                if len(payload) < 5 + route_len:
                    continue
                route = bytes(payload[5:5 + route_len]).decode('utf-8', errors='replace')
                body_start = 5 + route_len
                request_routes[req_id] = route
            else:
                # Notify: type(1) + route_len(1) + route + body
                if len(payload) < 2:
                    continue
                route_len = payload[1]
                if len(payload) < 2 + route_len:
                    continue
                route = bytes(payload[2:2 + route_len]).decode('utf-8', errors='replace')
                body_start = 2 + route_len
                req_id = None

            body = None
            if body_start < len(payload):
                try:
                    body = msgpack.unpackb(bytes(payload[body_start:]), raw=False)
                except:
                    body = bytes(payload[body_start:]).hex()

            results.append({
                'dir': direction,
                'type': POMELO_TYPES.get(ptype, f'UNK({ptype})'),
                'reqId': req_id,
                'route': route,
                'body': body
            })

        elif ptype == 2 and len(payload) >= 4:
            # RESPONSE - server -> client
            req_id = (payload[1] << 16) | (payload[2] << 8) | payload[3]
            body = None
            if len(payload) > 4:
                try:
                    body = msgpack.unpackb(bytes(payload[4:]), raw=False)
                except:
                    body = bytes(payload[4:]).hex()

            route = request_routes.get(req_id, '???')
            results.append({
                'dir': direction,
                'type': 'RESPONSE',
                'reqId': req_id,
                'route': route,
                'body': body
            })

        elif ptype in (3, 4) and len(payload) >= 4:
            # PUSH - server -> client
            plen = (payload[1] << 16) | (payload[2] << 8) | payload[3]
            pbody = payload[4:4 + plen]
            if len(pbody) < 2:
                continue
            rlen = pbody[1]
            off = 2 + rlen
            body = None
            if off < len(pbody):
                try:
                    body = msgpack.unpackb(bytes(pbody[off:]), raw=False)
                except:
                    pass

            # Extract event from body
            event = ''
            if isinstance(body, dict):
                event = body.get('event', body.get('route', ''))

            # Skip noisy events
            if event in ('gameinfo', 'countdown', 'matchesStatusPushNotify', 'apiClub.clubHandler.jackpot', 'clientPing'):
                continue

            results.append({
                'dir': direction,
                'type': 'PUSH',
                'event': event,
                'body': body
            })

    return results

def log_msg(msg_data):
    """Log a parsed message to file and console."""
    direction = msg_data['dir']
    mtype = msg_data['type']

    arrow = '>>>' if direction == 'SEND' else '<<<'

    # Colorize
    if direction == 'SEND':
        prefix = f"\033[93m{arrow} {mtype}\033[0m"  # Yellow for send
    else:
        prefix = f"\033[96m{arrow} {mtype}\033[0m"  # Cyan for recv

    route = msg_data.get('route', msg_data.get('event', ''))
    req_id = msg_data.get('reqId', '')
    body = msg_data.get('body', '')

    id_str = f" [#{req_id}]" if req_id else ''

    line = f"[{time.strftime('%H:%M:%S')}] {arrow} {mtype}{id_str} {route}"

    # Pretty print body
    body_str = ''
    if body:
        try:
            body_str = json.dumps(body, ensure_ascii=False, default=str)
            if len(body_str) > 500:
                body_str = body_str[:500] + '...'
        except:
            body_str = str(body)[:500]

    print(f"{prefix}{id_str} \033[97m{route}\033[0m")
    if body_str:
        print(f"  {body_str[:200]}")

    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{line}\n")
        if body_str:
            f.write(f"  {body_str}\n")
        f.write("\n")

def on_msg(msg, data):
    if msg['type'] != 'send':
        return
    p = msg['payload']

    if p.get('t') == 'ready':
        print("\033[92mHOOK OK! Monitoring SEND + RECV...\033[0m")
        return
    if p.get('t') == 'fatal':
        print(f"\033[91mFATAL: {p['e']}\033[0m")
        return

    if not data:
        return

    raw = bytes(data)
    direction = p.get('d', 'RECV')

    with lock:
        try:
            frames = parse_pomelo_frames(raw, direction)
            for frame in frames:
                log_msg(frame)
        except Exception as e:
            pass

# Clear log
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write(f"=== Suprema Protocol Spy - {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")

print(f"Connecting to SupremaPoker (PID {pid})...")
sess = frida.attach(pid)

# Hook BOTH SSL_read AND SSL_write
js = r'''
try {
    var sslmod = Process.findModuleByName("libssl-1_1.dll");

    // Hook SSL_read (server -> client)
    var ssl_read = sslmod.findExportByName("SSL_read");
    Interceptor.attach(ssl_read, {
        onEnter: function(args) { this.buf = args[1]; },
        onLeave: function(retval) {
            var n = retval.toInt32();
            if (n > 0) send({t:"data", d:"RECV"}, this.buf.readByteArray(n));
        }
    });

    // Hook SSL_write (client -> server)
    var ssl_write = sslmod.findExportByName("SSL_write");
    Interceptor.attach(ssl_write, {
        onEnter: function(args) {
            var n = args[2].toInt32();
            if (n > 0) send({t:"data", d:"SEND"}, args[1].readByteArray(n));
        }
    });

    send({t:"ready"});
} catch(e) {
    send({t:"fatal", e:e.toString()});
}
'''

sc = sess.create_script(js)
sc.on('message', on_msg)
sc.load()

print("\033[92m")
print("=" * 60)
print("  SUPREMA PROTOCOL SPY ACTIVE")
print("  Logging to: ~/suprema_spy.log")
print("  ")
print("  Agora entra numa mesa no Suprema!")
print("  Vou capturar todos os requests de JOIN")
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
