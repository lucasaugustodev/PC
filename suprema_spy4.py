"""Suprema Protocol Spy v4 - Hooks ALL SupremaPoker PIDs simultaneously."""
import frida, json, time, sys, os, subprocess, threading
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import msgpack
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'msgpack'])
    import msgpack

LOG_FILE = os.path.expanduser('~/suprema_spy4.log')
lock = threading.Lock()
send_buf = b''
recv_buf = b''

def parse_ws_frames(buf):
    frames = []
    pos = 0
    while pos < len(buf):
        if pos + 1 >= len(buf): break
        b0 = buf[pos]; b1 = buf[pos + 1]
        opcode = b0 & 0x0F
        if opcode not in (0x01, 0x02, 0x08, 0x09, 0x0A) and (b0 & 0x80) == 0:
            pos += 1; continue
        masked = (b1 & 0x80) != 0
        payload_len = b1 & 0x7F
        header_len = 2
        if payload_len == 126:
            if pos + 3 >= len(buf): break
            payload_len = (buf[pos + 2] << 8) | buf[pos + 3]; header_len = 4
        elif payload_len == 127:
            if pos + 9 >= len(buf): break
            payload_len = int.from_bytes(buf[pos + 2:pos + 10], 'big'); header_len = 10
        if masked: header_len += 4
        total = pos + header_len + payload_len
        if total > len(buf): break
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
    if len(payload) < 2: return None
    ptype = payload[0]
    if ptype == 4 and len(payload) >= 4:
        plen = (payload[1] << 16) | (payload[2] << 8) | payload[3]
        pbody = payload[4:4 + plen]
        if direction == 'SEND':
            # CLIENT: [reqId 2B] [routeLen 1B] [route] [JSON body]
            if len(pbody) < 3:
                return {'type': 'REQUEST', 'raw': payload[:50].hex()}
            reqId = (pbody[0] << 8) | pbody[1]
            rlen = pbody[2]
            if 3 + rlen > len(pbody):
                return {'type': 'REQUEST', 'reqId': reqId, 'raw': pbody[:50].hex()}
            route = bytes(pbody[3:3+rlen]).decode('utf-8', errors='replace')
            body = None
            body_raw = pbody[3+rlen:]
            if body_raw:
                try: body = json.loads(body_raw.decode('utf-8', errors='replace'))
                except:
                    try: body = msgpack.unpackb(body_raw, raw=False)
                    except: body = {'_hex': body_raw[:200].hex()}
            return {'type': 'REQUEST', 'reqId': reqId, 'route': route, 'body': body}
        else:
            # SERVER: [flags 1B] [routeLen 1B] [route] [msgpack body]
            if len(pbody) < 2:
                return {'type': 'PUSH', 'raw': payload[:50].hex()}
            rlen = pbody[1]
            off = 2 + rlen
            route = bytes(pbody[2:2 + rlen]).decode('utf-8', errors='replace')
            body = None
            if off < len(pbody):
                try: body = msgpack.unpackb(pbody[off:], raw=False)
                except: pass
            return {'type': 'PUSH', 'route': route, 'body': body}
    if ptype == 2 and len(payload) >= 4:
        req_id = (payload[1] << 16) | (payload[2] << 8) | payload[3]
        body = None
        if len(payload) > 4:
            try: body = msgpack.unpackb(payload[4:], raw=False)
            except: pass
        return {'type': 'RESPONSE', 'reqId': req_id, 'body': body}
    if ptype == 3 and len(payload) <= 4:
        return {'type': 'HEARTBEAT'}
    return {'type': f'UNK({ptype})', 'hex': payload[:80].hex()}

def log_frame(direction, decoded, raw_len):
    if not decoded: return
    if decoded.get('type') == 'HEARTBEAT': return
    ts = time.strftime('%H:%M:%S')
    dtype = decoded['type']
    arrow = '>>>' if direction == 'SEND' else '<<<'
    route = decoded.get('route', '')
    req_id = decoded.get('reqId', '')
    id_str = f' [#{req_id}]' if req_id else ''
    header = f'[{ts}] {arrow} {dtype}{id_str} {route} ({raw_len}b)'
    body = decoded.get('body')
    body_str = ''
    if body:
        try:
            body_str = json.dumps(body, ensure_ascii=False, default=str)
            if len(body_str) > 1500: body_str = body_str[:1500] + '...'
        except: pass
    raw_hex = decoded.get('raw', decoded.get('hex', ''))
    print(header)
    if body_str: print(f'  {body_str}')
    if raw_hex: print(f'  hex: {raw_hex}')
    sys.stdout.flush()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f'{header}\n')
        if body_str: f.write(f'  {body_str}\n')
        if raw_hex: f.write(f'  hex: {raw_hex}\n')
        f.write('\n')

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

# Find all PIDs
r = subprocess.check_output(
    'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
    shell=True, text=True
).strip()
pids = []
for line in r.splitlines():
    if 'SupremaPoker' in line:
        pids.append(int(line.split(',')[1].strip('"')))

if not pids:
    print("SupremaPoker not running!")
    sys.exit(1)

print(f"Found {len(pids)} processes: {pids}")

# Clear log
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write(f'=== Suprema Spy v4 - {time.strftime("%Y-%m-%d %H:%M:%S")} ===\n\n')

JS = r'''
try {
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    Interceptor.attach(sslmod.findExportByName("SSL_read"), {
        onEnter: function(args) { this.buf = args[1]; },
        onLeave: function(retval) {
            var n = retval.toInt32();
            if (n > 0) send({t:"data", d:"RECV"}, this.buf.readByteArray(n));
        }
    });
    Interceptor.attach(sslmod.findExportByName("SSL_write"), {
        onEnter: function(args) {
            var n = args[2].toInt32();
            if (n > 0) send({t:"data", d:"SEND"}, args[1].readByteArray(n));
        }
    });
    send({t:"ready"});
} catch(e) { send({t:"fatal", e:e.toString()}); }
'''

# Hook ALL PIDs
sessions = []
scripts = []

def make_handler(pid):
    def on_msg(msg, data):
        if msg['type'] != 'send': return
        p = msg['payload']
        if p.get('t') == 'ready':
            print(f"  PID {pid}: HOOK OK!")
            sys.stdout.flush()
            return
        if p.get('t') == 'fatal':
            print(f"  PID {pid}: FATAL: {p['e']}")
            return
        if not data: return
        process_data(bytes(data), p.get('d', 'RECV'))
    return on_msg

for pid in pids:
    try:
        sess = frida.attach(pid)
        sc = sess.create_script(JS)
        sc.on('message', make_handler(pid))
        sc.load()
        sessions.append(sess)
        scripts.append(sc)
        print(f"  Hooked PID {pid}")
    except Exception as e:
        print(f"  PID {pid} failed: {e}")

print(f"\nMonitoring {len(scripts)} processes. Navigate in the app!")
print("=" * 50)
sys.stdout.flush()

try:
    while True: time.sleep(0.5)
except KeyboardInterrupt:
    pass

print("\nStopping...")
for sc in scripts:
    try: sc.unload()
    except: pass
for sess in sessions:
    try: sess.detach()
    except: pass
