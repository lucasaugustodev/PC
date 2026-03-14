"""Capture all raw bytes from injection, then parse offline."""
import frida, json, time, sys, os, msgpack, subprocess, threading, random, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

lock = threading.Lock()
raw_chunks = []  # (timestamp, direction, raw_bytes)

r = subprocess.check_output(
    'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
    shell=True, text=True
).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
print(f"PIDs: {pids}")

JS = r'''
try {
    var s = Process.findModuleByName("libssl-1_1.dll");
    var wfn = new NativeFunction(s.findExportByName("SSL_write"), 'int', ['pointer', 'pointer', 'int']);
    var g = null; var c = {};
    Interceptor.attach(s.findExportByName("SSL_read"), {
        onEnter: function(a) { this.ssl=a[0]; this.buf=a[1]; },
        onLeave: function(r) {
            var n=r.toInt32(); if(n>0) {
                var p=this.ssl.toString();
                c[p]=true; g=this.ssl;
                send({d:"R"}, this.buf.readByteArray(n));
            }
        }
    });
    Interceptor.attach(s.findExportByName("SSL_write"), {
        onEnter: function(a) {
            this.ssl=a[0]; var n=a[2].toInt32(); if(n>0) {
                var p=this.ssl.toString();
                c[p]=true; g=this.ssl;
                send({d:"S"}, a[1].readByteArray(n));
            }
        }
    });
    rpc.exports = {
        inject: function(hex) {
            if(!g) return "NO_SSL";
            var d=[]; for(var i=0;i<hex.length;i+=2) d.push(parseInt(hex.substr(i,2),16));
            var b=Memory.alloc(d.length); b.writeByteArray(d);
            return "OK:"+wfn(g,b,d.length);
        }
    };
    send({t:"ready"});
} catch(e) { send({t:"fatal", e:e.toString()}); }
'''

sessions = []
active_sc = None

for pid in pids:
    try:
        sess = frida.attach(pid)
        sc = sess.create_script(JS)
        def make_cb(p):
            def cb(msg, data):
                if msg['type'] != 'send': return
                pl = msg['payload']
                if pl.get('t') == 'ready':
                    print(f"  PID {p}: OK"); return
                if data:
                    with lock:
                        raw_chunks.append((time.time(), pl.get('d','?'), bytes(data)))
            return cb
        sc.on('message', make_cb(pid))
        sc.load()
        sessions.append((sess, sc, pid))
    except Exception as e:
        print(f"  PID {pid}: {e}")

time.sleep(2)
for sess, sc, pid in sessions:
    try:
        r = sc.exports_sync.inject("03")  # heartbeat probe
        if r.startswith("OK"):
            active_sc = sc; print(f"Active: PID {pid}"); break
    except: pass

if not active_sc:
    print("No active!"); sys.exit(1)

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

# Mark start
print("\nInjetando joinGameRoom...")
body = json.dumps({
    "clubID": "14625", "unionID": 113, "myClubID": 41157, "myUnionID": 128,
    "roomID": "14625_43107012#113@41157%128",
    "privatecode": None, "ver": 7288, "lan": "pt", "verPackage": "5"
}).encode('utf-8')
route = b'apiPlayer.playerHandler.joinGameRoom'
reqid = 500
inner = bytes([(reqid >> 8) & 0xFF, reqid & 0xFF, len(route)]) + route + body
plen = len(inner)
pomelo = bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner

inject_ts = time.time()
r = active_sc.exports_sync.inject(build_ws(pomelo).hex())
print(f"SSL_write: {r}")

print("Capturando 10s...")
time.sleep(10)

# Now parse all captured data OFFLINE
print("\n" + "="*60)
print("PARSING CAPTURED DATA")
print("="*60)

with lock:
    chunks = list(raw_chunks)

# Separate recv chunks after inject
recv_after = [raw for ts, d, raw in chunks if d == 'R' and ts > inject_ts]
print(f"Recv chunks after inject: {len(recv_after)}")

# Concatenate ALL recv bytes
all_bytes = b''.join(recv_after)
print(f"Total recv bytes: {len(all_bytes)}")

# Save raw for debug
with open(os.path.expanduser('~/inject_raw.bin'), 'wb') as f:
    f.write(all_bytes)
print("Saved to ~/inject_raw.bin")

# Find HTTP headers (they end with \r\n\r\n)
http_end = all_bytes.find(b'\r\n\r\n')
if http_end >= 0:
    http_headers = all_bytes[:http_end+4].decode('ascii', errors='replace')
    print(f"\nHTTP Headers:\n{http_headers[:500]}")
    ws_data = all_bytes[http_end+4:]
    print(f"\nWS data after headers: {len(ws_data)} bytes")
else:
    ws_data = all_bytes
    print("No HTTP headers found")

# Try to find WS frames in the data
def find_ws_frames(data):
    frames = []
    pos = 0
    while pos < len(data):
        if pos + 1 >= len(data): break
        b0 = data[pos]
        b1 = data[pos+1]

        # Check if this looks like a WS frame
        op = b0 & 0x0F
        fin = (b0 & 0x80) != 0

        if op not in (0, 1, 2, 8, 9, 10):
            pos += 1
            continue

        masked = (b1 & 0x80) != 0
        pl = b1 & 0x7F
        hl = 2

        if pl == 126:
            if pos + 3 >= len(data): break
            pl = (data[pos+2] << 8) | data[pos+3]
            hl = 4
        elif pl == 127:
            if pos + 9 >= len(data): break
            pl = int.from_bytes(data[pos+2:pos+10], 'big')
            hl = 10

        if masked:
            hl += 4

        end = pos + hl + pl
        if end > len(data) or pl > 1000000:
            pos += 1
            continue

        if masked:
            mk = data[pos+hl-4:pos+hl]
            payload = bytearray(data[pos+hl:end])
            for i in range(len(payload)):
                payload[i] ^= mk[i % 4]
            frames.append((pos, bytes(payload)))
        else:
            frames.append((pos, data[pos+hl:end]))

        pos = end

    return frames

# Find frames in WS data
ws_frames = find_ws_frames(ws_data)
print(f"\nFound {len(ws_frames)} WS frames in data after HTTP")

# Also try to find Pomelo frames directly (without WS wrapper)
def find_pomelo_in_bytes(data):
    """Search for msgpack maps containing game data."""
    results = []

    # Try to find msgpack-encoded initinfo
    # Look for "initinfo" string in msgpack: a8696e6974696e666f
    needle = b'\xa8initinfo'
    pos = 0
    while True:
        idx = data.find(needle, pos)
        if idx < 0: break

        # Found initinfo marker, try to decode msgpack around it
        # Search backwards for a map header
        for start in range(max(0, idx-200), idx):
            try:
                obj = msgpack.unpackb(data[start:], raw=False)
                if isinstance(obj, dict) and 'event' in obj:
                    results.append(('initinfo_map', start, obj))
                    break
            except:
                continue
        pos = idx + 1

    # Look for game_seat data
    needle2 = b'\xa9game_seat'
    pos = 0
    while True:
        idx = data.find(needle2, pos)
        if idx < 0: break
        for start in range(max(0, idx-500), idx):
            try:
                obj = msgpack.unpackb(data[start:], raw=False)
                if isinstance(obj, dict):
                    results.append(('game_seat_map', start, obj))
                    break
            except:
                continue
        pos = idx + 1

    return results

# Parse WS frames
for i, (offset, payload) in enumerate(ws_frames):
    if len(payload) < 2: continue
    ptype = payload[0]

    if ptype == 2:
        # Pomelo response
        if len(payload) >= 4:
            rid = (payload[1]<<16)|(payload[2]<<8)|payload[3]
            body = None
            if len(payload) > 4:
                try: body = msgpack.unpackb(payload[4:], raw=False)
                except: body = payload[4:40].hex()
            print(f"\n  WS[{i}] RESPONSE reqId={rid}: {json.dumps(body, default=str, ensure_ascii=False)[:500]}")

    elif ptype == 4:
        # Pomelo push
        if len(payload) >= 4:
            pplen = (payload[1]<<16)|(payload[2]<<8)|payload[3]
            pb = payload[4:4+pplen]

            # Try all decode strategies
            decoded = False

            # Strategy: [flags 1B] [routeLen 1B] [route] [msgpack]
            if len(pb) >= 3:
                flags = pb[0]
                rl = pb[1]
                if rl > 0 and rl < 100 and 2+rl <= len(pb):
                    route = bytes(pb[2:2+rl]).decode('utf-8', errors='replace')
                    off = 2+rl
                    if off < len(pb):
                        try:
                            body = msgpack.unpackb(pb[off:], raw=False)
                            if isinstance(body, dict):
                                event = body.get('event', '')
                                if event == 'initinfo':
                                    data = body.get('data', {})
                                    room = data.get('room', {}) if isinstance(data, dict) else {}
                                    gs = data.get('game_seat', {}) if isinstance(data, dict) else {}
                                    gm = data.get('gamer', {}) if isinstance(data, dict) else {}
                                    print(f"\n  *** INITINFO: {room.get('name','?')} ***")
                                    print(f"      blinds={room.get('options',{}).get('blinds','?')}")
                                    for uid, seat in gs.items():
                                        if not isinstance(seat, dict): continue
                                        g = gm.get(str(seat.get('uid', uid)), {})
                                        if not isinstance(g, dict): g = {}
                                        bot = " [BOT]" if seat.get('agentID', 0) else ""
                                        print(f"      {g.get('displayID','?')}: stack={seat.get('coins',0):.2f} win={seat.get('winnings',0):+.2f}{bot}")
                                    decoded = True
                                elif event not in ('countdown', 'clientPing', 'gameinfo',
                                                   'matchesStatusPushNotify', 'apiClub.clubHandler.jackpot'):
                                    print(f"\n  WS[{i}] PUSH route={route} event={event}")
                                    if event in ('joinGameRoom', 'error'):
                                        print(f"    {json.dumps(body, default=str, ensure_ascii=False)[:500]}")
                                    decoded = True
                        except: pass

            # Strategy: [flags 1B] [routeCode 2B] [msgpack]
            if not decoded and len(pb) >= 4:
                flags = pb[0]
                rc = (pb[1]<<8)|pb[2]
                try:
                    body = msgpack.unpackb(pb[3:], raw=False)
                    if isinstance(body, dict):
                        event = body.get('event', '')
                        if event == 'initinfo':
                            data = body.get('data', {})
                            room = data.get('room', {}) if isinstance(data, dict) else {}
                            gs = data.get('game_seat', {}) if isinstance(data, dict) else {}
                            gm = data.get('gamer', {}) if isinstance(data, dict) else {}
                            print(f"\n  *** INITINFO (compressed): {room.get('name','?')} ***")
                            for uid, seat in gs.items():
                                if not isinstance(seat, dict): continue
                                g = gm.get(str(seat.get('uid', uid)), {})
                                if not isinstance(g, dict): g = {}
                                bot = " [BOT]" if seat.get('agentID', 0) else ""
                                print(f"      {g.get('displayID','?')}: stack={seat.get('coins',0):.2f} win={seat.get('winnings',0):+.2f}{bot}")
                            decoded = True
                        elif event == 'error':
                            print(f"  WS[{i}] ERROR: {body}")
                            decoded = True
                except: pass

    elif ptype == 1:
        # Handshake response
        if len(payload) >= 4:
            hlen = (payload[1]<<16)|(payload[2]<<8)|payload[3]
            try:
                hs = json.loads(payload[4:4+hlen])
                print(f"\n  WS[{i}] HANDSHAKE: {json.dumps(hs, ensure_ascii=False)[:300]}")
            except:
                print(f"\n  WS[{i}] HANDSHAKE: {payload[4:40].hex()}")

# Also search directly in raw bytes for game data
print("\n\n=== DIRECT BYTE SEARCH ===")
pomelo_data = find_pomelo_in_bytes(all_bytes)
for label, offset, obj in pomelo_data:
    if label == 'initinfo_map':
        data = obj.get('data', {})
        room = data.get('room', {}) if isinstance(data, dict) else {}
        gs = data.get('game_seat', {}) if isinstance(data, dict) else {}
        gm = data.get('gamer', {}) if isinstance(data, dict) else {}
        print(f"\n  FOUND initinfo @ offset {offset}: {room.get('name','?')}")
        for uid, seat in gs.items():
            if not isinstance(seat, dict): continue
            g = gm.get(str(seat.get('uid', uid)), {})
            if not isinstance(g, dict): g = {}
            bot = " [BOT]" if seat.get('agentID', 0) else ""
            print(f"    {g.get('displayID','?')}: stack={seat.get('coins',0):.2f} win={seat.get('winnings',0):+.2f}{bot}")
    elif label == 'game_seat_map':
        print(f"\n  FOUND game_seat @ offset {offset}: keys={list(obj.keys())[:10]}")

# Also do ASCII search for known strings
print("\n=== ASCII SEARCH ===")
for pattern in [b'initinfo', b'game_seat', b'displayID', b'agentID', b'joinGameRoom', b'error']:
    count = all_bytes.count(pattern)
    if count:
        idx = all_bytes.find(pattern)
        ctx = all_bytes[max(0,idx-20):idx+50]
        print(f"  '{pattern.decode()}' found {count}x, first at offset {idx}")
        print(f"    context: ...{ctx.hex()}...")

print("\n\nDone!")
for sess, sc, pid in sessions:
    try: sc.unload()
    except: pass
    try: sess.detach()
    except: pass
