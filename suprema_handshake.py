"""Capture Pomelo handshake to determine server version.
Pomelo handshake types: 1=handshake, 2=handshake_ack, 3=heartbeat
The server sends handshake (type 1) with sys info including version, heartbeat, dict, protos.
"""
import frida, json, time, sys, subprocess, threading
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LOG = []
lock = threading.Lock()

JS = r'''
try {
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    var ssl_read = sslmod.findExportByName("SSL_read");
    var ssl_write = sslmod.findExportByName("SSL_write");

    Interceptor.attach(ssl_read, {
        onEnter: function(a) { this.buf = a[1]; },
        onLeave: function(r) {
            var n = r.toInt32();
            if (n > 0) send({d:"RECV"}, this.buf.readByteArray(n));
        }
    });
    Interceptor.attach(ssl_write, {
        onEnter: function(a) {
            var n = a[2].toInt32();
            if (n > 0) send({d:"SEND"}, a[1].readByteArray(n));
        }
    });
    send({t:"ready"});
} catch(e) { send({t:"fatal",e:e.toString()}); }
'''

def on_msg(msg, data):
    if msg['type'] != 'send': return
    p = msg['payload']
    if p.get('t') == 'ready':
        print("HOOK OK"); return
    if not data: return
    raw = bytes(data)
    d = p.get('d', 'RECV')
    with lock:
        analyze(raw, d)

def analyze(raw, direction):
    """Look for Pomelo handshake messages in raw SSL data."""
    # Pomelo message types (before WebSocket framing):
    # 1 = handshake (server -> client, JSON with sys info)
    # 2 = handshake_ack (client -> server)
    # 3 = heartbeat
    # 4 = data (normal messages)
    # 5 = kick

    ts = time.strftime('%H:%M:%S')

    # Try direct Pomelo (no WS framing)
    if len(raw) >= 4:
        ptype = raw[0]
        if ptype in (1, 2, 3, 5):
            plen = (raw[1]<<16)|(raw[2]<<8)|raw[3]
            print(f"\n[{ts}] {direction} POMELO type={ptype} len={plen}")
            if ptype == 1 and plen > 0 and 4+plen <= len(raw):
                body = raw[4:4+plen]
                try:
                    obj = json.loads(body.decode('utf-8'))
                    print(f"  HANDSHAKE: {json.dumps(obj, indent=2)}")
                    LOG.append(('HANDSHAKE', obj))
                except:
                    print(f"  raw: {body[:200]}")
            elif ptype == 2:
                print(f"  HANDSHAKE ACK")
            elif ptype == 3:
                pass  # heartbeat, skip
            elif ptype == 5:
                body = raw[4:4+plen] if plen > 0 else b''
                print(f"  KICK: {body[:200]}")

    # Try inside WebSocket frames
    pos = 0
    while pos < len(raw):
        if pos + 1 >= len(raw): break
        b0 = raw[pos]; b1 = raw[pos+1]
        op = b0 & 0xF
        if op not in (1,2,8,9,10) and (b0&0x80)==0:
            pos += 1; continue
        masked = (b1&0x80) != 0
        pl = b1 & 0x7F; hl = 2
        if pl == 126:
            if pos+3 >= len(raw): break
            pl = (raw[pos+2]<<8)|raw[pos+3]; hl = 4
        elif pl == 127:
            if pos+9 >= len(raw): break
            pl = int.from_bytes(raw[pos+2:pos+10],'big'); hl = 10
        if masked: hl += 4
        t = pos + hl + pl
        if t > len(raw): break

        if masked:
            mk = raw[pos+hl-4:pos+hl]
            payload = bytearray(raw[pos+hl:t])
            for i in range(len(payload)): payload[i] ^= mk[i%4]
            payload = bytes(payload)
        else:
            payload = raw[pos+hl:t]

        # Check Pomelo type inside WS payload
        if len(payload) >= 4:
            ptype = payload[0]
            plen = (payload[1]<<16)|(payload[2]<<8)|payload[3]

            if ptype == 1:  # Handshake from server
                body = payload[4:4+plen] if plen > 0 else b''
                try:
                    obj = json.loads(body.decode('utf-8'))
                    print(f"\n\033[92m[{ts}] {direction} === POMELO HANDSHAKE (inside WS) ===")
                    print(json.dumps(obj, indent=2))
                    print(f"\033[0m")
                    LOG.append(('HANDSHAKE_WS', obj))
                except:
                    print(f"\n[{ts}] {direction} HANDSHAKE raw: {body[:300]}")

            elif ptype == 2:
                print(f"[{ts}] {direction} HANDSHAKE_ACK (inside WS)")

            elif ptype == 5:
                body = payload[4:4+plen] if plen > 0 else b''
                try:
                    obj = json.loads(body.decode('utf-8'))
                    print(f"\n\033[91m[{ts}] {direction} KICK: {json.dumps(obj)}\033[0m")
                except:
                    print(f"\n[{ts}] {direction} KICK raw: {body[:200]}")

            elif ptype == 4:
                # Normal data - check for interesting routes
                pb = payload[4:4+plen]
                if len(pb) >= 2:
                    if direction == 'SEND':
                        if len(pb) >= 3:
                            rid = (pb[0]<<8)|pb[1]; rl = pb[2]
                            if 3+rl <= len(pb):
                                route = bytes(pb[3:3+rl]).decode('utf-8', errors='replace')
                                if route not in ('room.roomHandler.clientMessage',):
                                    print(f"  [{ts}] >>> [{rid}] {route}")

        pos = t

    # Also dump first bytes for debugging
    if len(raw) > 0 and raw[0] not in (0x82, 0x81, 4):
        hex_preview = raw[:40].hex()
        ascii_preview = raw[:60].decode('ascii', errors='replace')
        if any(x in ascii_preview for x in ['sys', 'version', 'heartbeat', 'protos', 'pomelo']):
            print(f"\n\033[93m[{ts}] {direction} INTERESTING RAW:")
            print(f"  hex: {hex_preview}")
            print(f"  ascii: {ascii_preview}\033[0m")

# Find PIDs
def get_pids():
    r = subprocess.check_output(
        'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
        shell=True, text=True
    ).strip()
    return [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]

pids = get_pids()
if not pids:
    print("SupremaPoker not running. Waiting for it to start...")
    print("Open SupremaPoker now!")
    for i in range(120):
        time.sleep(2)
        pids = get_pids()
        if pids:
            print(f"\nDetected! PIDs: {pids}")
            # Wait a bit more for all processes to spawn
            time.sleep(3)
            pids = get_pids()
            print(f"Final PIDs: {pids}")
            break
        if i % 5 == 0:
            sys.stdout.write(f"\r  Waiting... {i*2}s ")
            sys.stdout.flush()
    if not pids:
        print("\nTimeout waiting for SupremaPoker."); sys.exit(1)
else:
    print(f"PIDs: {pids}")

sessions = []
for pid in pids:
    try:
        sess = frida.attach(pid)
        sc = sess.create_script(JS)
        sc.on('message', on_msg)
        sc.load()
        sessions.append((sess, sc))
        print(f"  Hooked PID {pid}")
    except Exception as e:
        print(f"  PID {pid}: {e}")

print("\n" + "="*60)
print("  POMELO HANDSHAKE CAPTURE")
print("  Restart SupremaPoker or reconnect to trigger handshake")
print("  The handshake only happens at connection init!")
print("  Press Ctrl+C when done")
print("="*60 + "\n")

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    pass

print(f"\nCaptured {len(LOG)} handshake messages")
for typ, obj in LOG:
    print(f"\n{typ}:")
    print(json.dumps(obj, indent=2))

for sess, sc in sessions:
    try: sc.unload()
    except: pass
    try: sess.detach()
    except: pass
