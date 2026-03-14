"""Debug injection - test JSON vs msgpack body, different reqIds, capture ALL responses."""
import frida, json, time, sys, os, msgpack, subprocess, threading, random
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

lock = threading.Lock()
all_recv = []  # (timestamp, raw_bytes)
all_send = []

# Find PIDs
r = subprocess.check_output(
    'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
    shell=True, text=True
).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
print(f"PIDs: {pids}")

JS = r'''
try {
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    var ssl_read = sslmod.findExportByName("SSL_read");
    var ssl_write = sslmod.findExportByName("SSL_write");
    var ssl_write_fn = new NativeFunction(ssl_write, 'int', ['pointer', 'pointer', 'int']);
    var gameSSL = null;
    var sslConns = {};

    Interceptor.attach(ssl_read, {
        onEnter: function(a) { this.ssl = a[0]; this.buf = a[1]; },
        onLeave: function(r) {
            var n = r.toInt32();
            if (n > 0) {
                var ptr = this.ssl.toString();
                var b0 = this.buf.readU8();
                if (b0 === 0x82 || b0 === 4 || b0 === 3) {
                    gameSSL = this.ssl;
                    sslConns[ptr] = true;
                }
                if (sslConns[ptr]) {
                    send({t:"d", d:"R"}, this.buf.readByteArray(n));
                }
            }
        }
    });

    Interceptor.attach(ssl_write, {
        onEnter: function(a) {
            this.ssl = a[0];
            var n = a[2].toInt32();
            if (n > 0) {
                var ptr = this.ssl.toString();
                var b0 = a[1].readU8();
                if (b0 === 0x82 || b0 === 4 || b0 === 3) {
                    gameSSL = this.ssl;
                    sslConns[ptr] = true;
                }
                if (sslConns[ptr]) {
                    send({t:"d", d:"S"}, a[1].readByteArray(n));
                }
            }
        }
    });

    rpc.exports = {
        inject: function(hex) {
            if (!gameSSL) return "NO_SSL";
            var d = [];
            for (var i = 0; i < hex.length; i += 2)
                d.push(parseInt(hex.substr(i, 2), 16));
            var b = Memory.alloc(d.length);
            b.writeByteArray(d);
            return "OK:" + ssl_write_fn(gameSSL, b, d.length);
        },
        hasssl: function() { return gameSSL ? "YES" : "NO"; }
    };
    send({t:"ready"});
} catch(e) { send({t:"fatal", e:e.toString()}); }
'''

sessions = []
active_sc = None

def on_msg_factory(pid):
    def on_msg(msg, data):
        if msg['type'] != 'send': return
        p = msg['payload']
        if p.get('t') == 'ready':
            print(f"  PID {pid}: HOOK OK")
            return
        if p.get('t') == 'd' and data:
            raw = bytes(data)
            d = p.get('d', '?')
            with lock:
                if d == 'R': all_recv.append((time.time(), raw))
                else: all_send.append((time.time(), raw))
    return on_msg

for pid in pids:
    try:
        sess = frida.attach(pid)
        sc = sess.create_script(JS)
        sc.on('message', on_msg_factory(pid))
        sc.load()
        sessions.append((sess, sc, pid))
        print(f"  Hooked PID {pid}")
    except Exception as e:
        print(f"  PID {pid}: {e}")

print("\nEsperando SSL (3s)...")
time.sleep(3)

# Find active SC
for sess, sc, pid in sessions:
    try:
        if sc.exports_sync.hasssl() == "YES":
            active_sc = sc
            print(f"  Active: PID {pid}")
            break
    except: pass

if not active_sc:
    print("No gameSSL found!")
    sys.exit(1)

def build_ws(payload):
    f = bytearray([0x82])
    pl = len(payload)
    if pl < 126: f.append(0x80 | pl)
    elif pl < 65536: f.append(0x80 | 126); f.extend(pl.to_bytes(2, 'big'))
    m = bytes([random.randint(0, 255) for _ in range(4)])
    f.extend(m)
    mp = bytearray(payload)
    for i in range(len(mp)): mp[i] ^= m[i % 4]
    f.extend(mp)
    return bytes(f)

def decode_all_recv(since_ts):
    """Decode ALL received data since timestamp."""
    results = []
    with lock:
        recent = [(t, r) for t, r in all_recv if t > since_ts]

    for ts, raw in recent:
        # Try to parse as WS frame
        if len(raw) < 2: continue

        if raw[0] == 0x82:
            # WS binary frame
            pl = raw[1] & 0x7F; off = 2
            if pl == 126 and len(raw) >= 4:
                pl = (raw[2]<<8)|raw[3]; off = 4
            elif pl == 127 and len(raw) >= 10:
                pl = int.from_bytes(raw[2:10], 'big'); off = 10
            payload = raw[off:off+pl]
            if len(payload) < 1: continue

            ptype = payload[0]
            if ptype == 3:
                results.append("HEARTBEAT")
            elif ptype == 2:
                # Response
                if len(payload) >= 4:
                    rid = (payload[1]<<16)|(payload[2]<<8)|payload[3]
                    body = None
                    if len(payload) > 4:
                        try: body = msgpack.unpackb(payload[4:], raw=False)
                        except: body = payload[4:40].hex()
                    results.append(f"RESP[{rid}]={body}")
            elif ptype == 4:
                # Push
                if len(payload) >= 4:
                    pplen = (payload[1]<<16)|(payload[2]<<8)|payload[3]
                    pb = payload[4:4+pplen]
                    if len(pb) >= 1:
                        flags = pb[0]
                        if (flags & 1) == 0 and len(pb) >= 3:
                            rc = (pb[1]<<8)|pb[2]
                            body = None
                            if len(pb) > 3:
                                try: body = msgpack.unpackb(pb[3:], raw=False)
                                except: body = pb[3:20].hex()
                            if isinstance(body, dict):
                                ev = body.get('event', '')
                                if ev in ('matchesStatusPushNotify', 'apiClub.clubHandler.jackpot', 'countdown', 'clientPing', 'gameinfo'):
                                    continue  # skip noise
                                results.append(f"PUSH(c) rc={rc} ev={ev} keys={list(body.keys())[:5]}")
                            else:
                                results.append(f"PUSH(c) rc={rc} body={str(body)[:100]}")
                        elif (flags & 1) == 1 and len(pb) >= 2:
                            rl = pb[1]
                            route = bytes(pb[2:2+rl]).decode('utf-8', errors='replace')
                            body = None
                            off2 = 2+rl
                            if off2 < len(pb):
                                try: body = msgpack.unpackb(pb[off2:], raw=False)
                                except: body = pb[off2:off2+20].hex()
                            if isinstance(body, dict):
                                ev = body.get('event', '')
                                if ev in ('matchesStatusPushNotify', 'apiClub.clubHandler.jackpot', 'countdown', 'clientPing', 'gameinfo'):
                                    continue
                                results.append(f"PUSH(s) route={route} ev={ev}")
                            else:
                                results.append(f"PUSH(s) route={route} body={str(body)[:100]}")
            else:
                results.append(f"TYPE_{ptype}: {payload[:20].hex()}")
        elif raw[0] in (2, 3, 4):
            # Raw Pomelo (not WS-wrapped)
            ptype = raw[0]
            if ptype == 2 and len(raw) >= 4:
                rid = (raw[1]<<16)|(raw[2]<<8)|raw[3]
                body = None
                if len(raw) > 4:
                    try: body = msgpack.unpackb(raw[4:], raw=False)
                    except: body = raw[4:30].hex()
                results.append(f"RAW_RESP[{rid}]={body}")
            elif ptype == 3:
                results.append("RAW_HEARTBEAT")
            elif ptype == 4 and len(raw) >= 4:
                pplen = (raw[1]<<16)|(raw[2]<<8)|raw[3]
                pb = raw[4:4+pplen]
                results.append(f"RAW_PUSH: {pb[:30].hex()}")
        else:
            results.append(f"UNK: {raw[:20].hex()}")

    return results

def inject_test(label, reqid, route, body_dict, use_msgpack=False):
    print(f"\n{'='*50}")
    print(f"TEST: {label}")
    route_bytes = route.encode('utf-8')
    if use_msgpack:
        body_bytes = msgpack.packb(body_dict)
        print(f"  Body format: MSGPACK ({len(body_bytes)}b)")
    else:
        body_bytes = json.dumps(body_dict).encode('utf-8')
        print(f"  Body format: JSON ({len(body_bytes)}b)")

    print(f"  reqId={reqid} route={route}")

    inner = bytes([(reqid >> 8) & 0xFF, reqid & 0xFF, len(route_bytes)]) + route_bytes + body_bytes
    plen = len(inner)
    pomelo = bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner
    ws = build_ws(pomelo)

    print(f"  Pomelo frame: {pomelo[:40].hex()}")

    ts = time.time()
    result = active_sc.exports_sync.inject(ws.hex())
    print(f"  SSL_write: {result}")
    sys.stdout.flush()

    time.sleep(5)

    recv = decode_all_recv(ts)
    non_hb = [r for r in recv if 'HEARTBEAT' not in r]
    print(f"  Received: {len(recv)} total, {len(non_hb)} non-heartbeat")
    for r in non_hb[:10]:
        print(f"    {r[:300]}")
    sys.stdout.flush()

# Load target data
scanner_file = os.path.expanduser('~/suprema_scanner.json')
target = None
if os.path.exists(scanner_file):
    with open(scanner_file, 'r', encoding='utf-8') as f:
        sdata = json.load(f)
    for k, m in sdata.get('matches', {}).items():
        if m.get('!!', 0) > 0 and not m.get('prizePool'):
            target = m
            break

if not target:
    print("No active cash table found!")
    sys.exit(1)

mid = target['matchID']
cid = target['clubID']
uid = target['unionID']
room_id = f"{cid}_{mid}#{uid}@41157%128"
print(f"\nTarget: match={mid} club={cid} room={room_id}")

body = {
    "clubID": str(cid), "unionID": uid,
    "myClubID": 41157, "myUnionID": 128,
    "roomID": room_id,
    "privatecode": None, "ver": 7288, "lan": "pt", "verPackage": "5"
}

# TEST 1: JSON body, high reqId
inject_test("joinGameRoom JSON reqId=500", 500,
            "apiPlayer.playerHandler.joinGameRoom", body, use_msgpack=False)

# TEST 2: msgpack body, different reqId
inject_test("joinGameRoom MSGPACK reqId=501", 501,
            "apiPlayer.playerHandler.joinGameRoom", body, use_msgpack=True)

# TEST 3: Simple heartbeat (type 3) - should get pong
print(f"\n{'='*50}")
print("TEST: Send heartbeat")
heartbeat = bytes([3])
ws_hb = build_ws(heartbeat)
ts = time.time()
r = active_sc.exports_sync.inject(ws_hb.hex())
print(f"  SSL_write: {r}")
time.sleep(3)
recv = decode_all_recv(ts)
non_hb = [r for r in recv if 'HEARTBEAT' not in r]
print(f"  Received: {len(recv)} total, {len(non_hb)} non-heartbeat")
for r2 in non_hb[:5]:
    print(f"    {r2[:200]}")

# TEST 4: Pomelo handshake (type 1) - just to see if server responds
print(f"\n{'='*50}")
print("TEST: Pomelo handshake probe")
handshake = json.dumps({"sys": {"ver": "1.0", "type": "js-websocket"}}).encode('utf-8')
pomelo_hs = bytes([1, 0, 0, len(handshake)]) + handshake
ws_hs = build_ws(pomelo_hs)
ts = time.time()
r = active_sc.exports_sync.inject(ws_hs.hex())
print(f"  SSL_write: {r}")
time.sleep(3)
recv = decode_all_recv(ts)
non_hb = [r for r in recv if 'HEARTBEAT' not in r]
print(f"  Received: {len(recv)} total, {len(non_hb)} non-heartbeat")
for r2 in non_hb[:5]:
    print(f"    {r2[:200]}")

# TEST 5: Try getPrefsData with JSON (simple request that should work)
inject_test("getPrefsData JSON reqId=502", 502,
            "apiPlayer.playerHandler.getPrefsData",
            {"ver": 7288, "lan": "pt", "verPackage": "5"}, use_msgpack=False)

# TEST 6: Try getPrefsData with msgpack
inject_test("getPrefsData MSGPACK reqId=503", 503,
            "apiPlayer.playerHandler.getPrefsData",
            {"ver": 7288, "lan": "pt", "verPackage": "5"}, use_msgpack=True)

print("\n\nDone!")
for sess, sc, pid in sessions:
    try: sc.unload()
    except: pass
    try: sess.detach()
    except: pass
