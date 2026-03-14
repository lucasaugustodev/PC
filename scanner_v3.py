"""Scanner v3 - trigger reconnect, wait for auth, THEN inject joinGameRoom."""
import frida, json, time, sys, os, msgpack, subprocess, threading, random
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

lock = threading.Lock()
raw_recv = []
auth_done = threading.Event()
initinfo_data = [None]

def parse_ws_frames(data):
    frames = []; pos = 0
    while pos < len(data):
        if pos + 1 >= len(data): break
        b0 = data[pos]; b1 = data[pos+1]
        op = b0 & 0x0F
        if op not in (0, 1, 2, 8, 9, 10): pos += 1; continue
        masked = (b1 & 0x80) != 0
        pl = b1 & 0x7F; hl = 2
        if pl == 126:
            if pos + 3 >= len(data): break
            pl = (data[pos+2]<<8)|data[pos+3]; hl = 4
        elif pl == 127:
            if pos + 9 >= len(data): break
            pl = int.from_bytes(data[pos+2:pos+10], 'big'); hl = 10
        if masked: hl += 4
        end = pos + hl + pl
        if end > len(data) or pl > 1000000: pos += 1; continue
        if masked:
            mk = data[pos+hl-4:pos+hl]; r = bytearray(data[pos+hl:end])
            for i in range(len(r)): r[i] ^= mk[i % 4]
            frames.append(bytes(r))
        else:
            frames.append(data[pos+hl:end])
        pos = end
    return frames

def check_for_events(raw_bytes):
    """Check raw bytes for auth completion and initinfo."""
    # Find all HTTP header ends
    crlf = b'\r\n\r\n'
    pos = 0
    while True:
        idx = raw_bytes.find(crlf, pos)
        if idx < 0: break
        ws_start = idx + 4
        # Parse WS frames from here
        frames = parse_ws_frames(raw_bytes[ws_start:ws_start+50000])
        for frame in frames:
            if len(frame) < 5 or frame[0] != 4: continue
            plen = (frame[1]<<16)|(frame[2]<<8)|frame[3]
            pb = frame[4:4+plen]
            if len(pb) < 3: continue
            try:
                body = msgpack.unpackb(pb[2:], raw=False)
            except:
                continue
            if not isinstance(body, dict): continue
            event = body.get('event', '')
            if 'connect' in event or 'entry' in event:
                auth_done.set()
            if event == 'initinfo':
                initinfo_data[0] = body
        pos = idx + 4

r = subprocess.check_output(
    'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
    shell=True, text=True).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
print(f"PIDs: {pids}")

JS = r'''
try {
    var s = Process.findModuleByName("libssl-1_1.dll");
    var wfn = new NativeFunction(s.findExportByName("SSL_write"), 'int', ['pointer', 'pointer', 'int']);
    var g = null;
    Interceptor.attach(s.findExportByName("SSL_read"), {
        onEnter: function(a) { this.ssl=a[0]; this.buf=a[1]; },
        onLeave: function(r) {
            var n=r.toInt32(); if(n>0) {
                var b0 = this.buf.readU8();
                if(b0===0x82||b0===3||b0===4||b0===2||b0===1) g=this.ssl;
                send({d:"R"}, this.buf.readByteArray(n));
            }
        }
    });
    Interceptor.attach(s.findExportByName("SSL_write"), {
        onEnter: function(a) {
            this.ssl=a[0]; var n=a[2].toInt32(); if(n>0) {
                var b0=a[1].readU8();
                if(b0===0x82||b0===3||b0===4) g=this.ssl;
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
                if msg['payload'].get('t') == 'ready':
                    print(f"  PID {p}: OK"); return
                if data and msg['payload'].get('d') == 'R':
                    with lock:
                        raw_recv.append((time.time(), bytes(data)))
            return cb
        sc.on('message', make_cb(pid))
        sc.load()
        sessions.append((sess, sc, pid))
    except: pass

time.sleep(2)
for s, sc, p in sessions:
    try:
        if sc.exports_sync.inject("03").startswith("OK"):
            active_sc = sc; print(f"Active: PID {p}"); break
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

def build_join_request(match_id, club_id, union_id, reqid):
    room_id = f"{club_id}_{match_id}#{union_id}@41157%128"
    body = json.dumps({
        "clubID": str(club_id), "unionID": union_id,
        "myClubID": 41157, "myUnionID": 128,
        "roomID": room_id,
        "privatecode": None, "ver": 7288, "lan": "pt", "verPackage": "5"
    }).encode('utf-8')
    route = b'apiPlayer.playerHandler.joinGameRoom'
    inner = bytes([(reqid >> 8) & 0xFF, reqid & 0xFF, len(route)]) + route + body
    plen = len(inner)
    return bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner

def scan_table(match_id, club_id, union_id):
    """Step 1: trigger reconnect. Step 2: wait for auth. Step 3: inject joinGameRoom."""
    global raw_recv

    with lock:
        raw_recv.clear()
    auth_done.clear()
    initinfo_data[0] = None
    ts = time.time()

    # Step 1: Inject garbage to trigger reconnection
    # Send an invalid WS close frame to force disconnect
    close_frame = build_ws(bytes([0x88, 0x00]))  # WS close
    r1 = active_sc.exports_sync.inject(close_frame.hex())
    print(f"  Step 1 (close): {r1}")

    # Wait for reconnection and auth
    print(f"  Waiting for reconnect+auth (8s)...")
    time.sleep(8)

    # Check raw data for auth completion
    with lock:
        all_bytes = b''.join([d for t, d in raw_recv if t > ts])
    print(f"  Received {len(all_bytes)} bytes")

    check_for_events(all_bytes)

    if auth_done.is_set():
        print(f"  Auth completed! Injecting joinGameRoom...")
    else:
        print(f"  Auth not detected, trying inject anyway...")

    # Step 2: Clear buffer and inject joinGameRoom
    ts2 = time.time()
    with lock:
        raw_recv.clear()

    reqid = random.randint(1, 200)
    pomelo = build_join_request(match_id, club_id, union_id, reqid)
    ws = build_ws(pomelo)
    r2 = active_sc.exports_sync.inject(ws.hex())
    print(f"  Step 2 (joinGameRoom reqId={reqid}): {r2}")

    # Wait for response
    time.sleep(8)

    with lock:
        resp_bytes = b''.join([d for t, d in raw_recv if t > ts2])
    print(f"  Response bytes: {len(resp_bytes)}")

    # Check for initinfo
    if resp_bytes:
        check_for_events(resp_bytes)

    if initinfo_data[0]:
        return initinfo_data[0]

    # Also check: search for type-2 response
    pattern = bytes([0x02, (reqid >> 16) & 0xFF, (reqid >> 8) & 0xFF, reqid & 0xFF])
    idx = resp_bytes.find(pattern)
    if idx >= 0:
        print(f"  Found type-2 response at {idx}")
        try:
            body = msgpack.unpackb(resp_bytes[idx+4:idx+500], raw=False)
            print(f"  Response body: {json.dumps(body, default=str, ensure_ascii=False)[:300]}")
        except:
            print(f"  Raw: {resp_bytes[idx+4:idx+30].hex()}")

    # Search for initinfo in raw
    if b'initinfo' in resp_bytes:
        print(f"  initinfo found in raw at {resp_bytes.find(b'initinfo')}")

    # Search for game_seat
    if b'game_seat' in resp_bytes:
        print(f"  game_seat found in raw!")

    # Also check for error
    if b'error' in resp_bytes:
        eidx = resp_bytes.find(b'error')
        print(f"  'error' at {eidx}: {resp_bytes[eidx-10:eidx+50]}")

    return None

# Test
print(f"\n{'='*50}")
print("TEST: Scan match 43107012 (Golden HU ANTE)")
print(f"{'='*50}")
info = scan_table(43107012, 14625, 113)
if info:
    data = info.get('data', {})
    gs = data.get('game_seat', {})
    gm = data.get('gamer', {})
    room = data.get('room', {})
    print(f"\n  ROOM: {room.get('name')}")
    for uk, s in gs.items():
        if not isinstance(s, dict): continue
        g = gm.get(str(s.get('uid', uk)), {})
        if not isinstance(g, dict): g = {}
        bot = " [BOT]" if s.get('agentID', 0) else ""
        print(f"    {g.get('displayID','?')}: stack={s.get('coins',0)}{bot}")
else:
    print("\n  No initinfo - server doesn't respond to post-reconnect joinGameRoom")

# Try alternative: just inject joinGameRoom WITHOUT reconnection first
print(f"\n{'='*50}")
print("TEST 2: Direct inject without reconnect (reqId=3)")
print(f"{'='*50}")
with lock:
    raw_recv.clear()
ts = time.time()

# Use very low reqId to match what real client might use
pomelo = build_join_request(43107012, 14625, 113, 3)
ws = build_ws(pomelo)
r = active_sc.exports_sync.inject(ws.hex())
print(f"  inject: {r}")
time.sleep(6)

with lock:
    resp = b''.join([d for t, d in raw_recv if t > ts])
print(f"  Received: {len(resp)} bytes")
print(f"  Has initinfo: {b'initinfo' in resp}")
print(f"  Has game_seat: {b'game_seat' in resp}")
print(f"  Has error: {b'error' in resp}")

# Search for type-2 response
for reqid_check in [3]:
    pattern = bytes([0x02, 0x00, (reqid_check >> 8) & 0xFF, reqid_check & 0xFF])
    idx = resp.find(pattern)
    if idx >= 0:
        print(f"  Type-2 response for reqId={reqid_check} at {idx}")
        try:
            body = msgpack.unpackb(resp[idx+4:idx+500], raw=False)
            print(f"  Body: {json.dumps(body, default=str, ensure_ascii=False)[:300]}")
        except:
            print(f"  Raw: {resp[idx+4:idx+30].hex()}")

for s, sc, p in sessions:
    try: sc.unload()
    except: pass
    try: s.detach()
    except: pass
print("\nDone!")
