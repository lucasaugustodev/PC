"""Scanner v2 - track SSL pointer changes and force reconnections."""
import frida, json, time, sys, os, msgpack, subprocess, threading, random
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

lock = threading.Lock()
raw_recv = []  # (timestamp, bytes)
ssl_ptr_log = []  # track SSL pointer changes
current_ssl = [None]  # mutable ref

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
    var g = null;
    var lastPtr = "";

    Interceptor.attach(s.findExportByName("SSL_read"), {
        onEnter: function(a) { this.ssl=a[0]; this.buf=a[1]; },
        onLeave: function(r) {
            var n=r.toInt32(); if(n>0) {
                var ptr = this.ssl.toString();
                // Only track game connections (Pomelo/WS traffic)
                var b0 = this.buf.readU8();
                if (b0 === 0x82 || b0 === 3 || b0 === 4 || b0 === 2 || b0 === 1) {
                    if (ptr !== lastPtr) {
                        send({t:"ssl", p:ptr, old:lastPtr});
                        lastPtr = ptr;
                    }
                    g = this.ssl;
                }
                send({d:"R", p:ptr}, this.buf.readByteArray(n));
            }
        }
    });

    Interceptor.attach(s.findExportByName("SSL_write"), {
        onEnter: function(a) {
            this.ssl=a[0]; var n=a[2].toInt32(); if(n>0) {
                var ptr = this.ssl.toString();
                var b0 = a[1].readU8();
                if (b0 === 0x82 || b0 === 3 || b0 === 4) {
                    g = this.ssl;
                }
                send({d:"S", p:ptr}, a[1].readByteArray(n));
            }
        }
    });

    rpc.exports = {
        inject: function(hex) {
            if(!g) return "NO_SSL";
            var ptr = g.toString();
            var d=[]; for(var i=0;i<hex.length;i+=2) d.push(parseInt(hex.substr(i,2),16));
            var b=Memory.alloc(d.length); b.writeByteArray(d);
            var ret = wfn(g,b,d.length);
            return "OK:" + ret + " @" + ptr;
        },
        getptr: function() {
            return g ? g.toString() : "null";
        }
    };
    send({t:"ready"});
} catch(e) { send({t:"fatal", e:e.toString()}); }
'''

sessions = []
active_sc = None
active_pid = None

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
                if pl.get('t') == 'ssl':
                    print(f"  SSL CHANGE on PID {p}: {pl.get('old','')} -> {pl.get('p','')}")
                    with lock:
                        ssl_ptr_log.append((time.time(), pl.get('p','')))
                    return
                if data and pl.get('d') == 'R':
                    with lock:
                        raw_recv.append((time.time(), bytes(data)))
            return cb
        sc.on('message', make_cb(pid))
        sc.load()
        sessions.append((sess, sc, pid))
    except Exception as e:
        print(f"  PID {pid}: {e}")

time.sleep(3)
for sess, sc, pid in sessions:
    try:
        ptr = sc.exports_sync.getptr()
        if ptr != "null":
            active_sc = sc; active_pid = pid
            print(f"Active: PID {pid} SSL={ptr}")
            break
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

def parse_ws_frames(data):
    frames = []; pos = 0
    while pos < len(data):
        if pos + 1 >= len(data): break
        b0 = data[pos]; b1 = data[pos+1]
        op = b0 & 0x0F
        if op not in (0, 1, 2, 8, 9, 10):
            pos += 1; continue
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

def extract_initinfo(raw_bytes):
    http_end = raw_bytes.find(b'\r\n\r\n')
    ws_data = raw_bytes[http_end+4:] if http_end >= 0 else raw_bytes
    frames = parse_ws_frames(ws_data)
    for frame in frames:
        if len(frame) < 5 or frame[0] != 4: continue
        plen = (frame[1]<<16)|(frame[2]<<8)|frame[3]
        pb = frame[4:4+plen]
        if len(pb) < 3: continue
        try: body = msgpack.unpackb(pb[2:], raw=False)
        except:
            try: body = msgpack.unpackb(pb[3:], raw=False)
            except: continue
        if isinstance(body, dict) and body.get('event') == 'initinfo':
            return body
    return None

def inject_and_capture(match_id, club_id, union_id, wait=10):
    """Inject joinGameRoom, wait for reconnection, extract initinfo."""
    room_id = f"{club_id}_{match_id}#{union_id}@41157%128"
    body = json.dumps({
        "clubID": str(club_id), "unionID": union_id,
        "myClubID": 41157, "myUnionID": 128,
        "roomID": room_id,
        "privatecode": None, "ver": 7288, "lan": "pt", "verPackage": "5"
    }).encode('utf-8')
    route = b'apiPlayer.playerHandler.joinGameRoom'
    reqid = random.randint(500, 60000)
    inner = bytes([(reqid >> 8) & 0xFF, reqid & 0xFF, len(route)]) + route + body
    plen = len(inner)
    pomelo = bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner
    ws = build_ws(pomelo)

    with lock:
        raw_recv.clear()

    ts = time.time()
    result = active_sc.exports_sync.inject(ws.hex())
    print(f"    inject: {result}")

    time.sleep(wait)

    # Check SSL pointer
    new_ptr = active_sc.exports_sync.getptr()
    print(f"    SSL ptr now: {new_ptr}")

    with lock:
        recv_after = [raw for t, raw in raw_recv if t > ts]
    all_bytes = b''.join(recv_after)
    print(f"    recv: {len(recv_after)} chunks, {len(all_bytes)} bytes")

    if len(all_bytes) < 100:
        return None

    return extract_initinfo(all_bytes)

# Test: scan the table we know works
print("\n=== TEST: Scan match 43107012 (Golden HU ANTE) ===")
info = inject_and_capture(43107012, 14625, 113)
if info:
    data = info.get('data', {})
    room = data.get('room', {})
    gs = data.get('game_seat', {})
    gm = data.get('gamer', {})
    print(f"  Room: {room.get('name')}")
    for uk, s in gs.items():
        if not isinstance(s, dict): continue
        g = gm.get(str(s.get('uid', uk)), {})
        if not isinstance(g, dict): g = {}
        bot = " [BOT]" if s.get('agentID', 0) else ""
        print(f"    {g.get('displayID','?')}: stack={s.get('coins',0)}{bot}")
else:
    print("  No initinfo!")

# Wait and check SSL state
print(f"\nWaiting 5s for connection to stabilize...")
time.sleep(5)
ptr = active_sc.exports_sync.getptr()
print(f"SSL ptr: {ptr}")

# Try second scan
print("\n=== TEST 2: Scan match 43099979 ===")
info2 = inject_and_capture(43099979, 14625, 113)
if info2:
    data = info2.get('data', {})
    room = data.get('room', {})
    gs = data.get('game_seat', {})
    gm = data.get('gamer', {})
    print(f"  Room: {room.get('name')}")
    for uk, s in gs.items():
        if not isinstance(s, dict): continue
        g = gm.get(str(s.get('uid', uk)), {})
        if not isinstance(g, dict): g = {}
        bot = " [BOT]" if s.get('agentID', 0) else ""
        print(f"    {g.get('displayID','?')}: stack={s.get('coins',0)}{bot}")
else:
    print("  No initinfo!")

print("\nSSL pointer changes:")
for ts, ptr in ssl_ptr_log:
    print(f"  {time.strftime('%H:%M:%S', time.localtime(ts))}: {ptr}")

print("\nDone!")
for sess, sc, pid in sessions:
    try: sc.unload()
    except: pass
    try: sess.detach()
    except: pass
