"""Decode ALL incoming traffic to understand push format and find responses."""
import frida, json, time, sys, os, msgpack, subprocess, threading, random
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

lock = threading.Lock()
all_frames = []  # (timestamp, direction, raw_pomelo_frame)

def parse_ws(buf):
    frames = []; pos = 0
    while pos < len(buf):
        if pos + 1 >= len(buf): break
        b0 = buf[pos]; b1 = buf[pos+1]; op = b0 & 0xF
        if op not in (1,2,8,9,10) and (b0&0x80)==0: pos += 1; continue
        m = (b1&0x80) != 0; pl = b1 & 0x7F; hl = 2
        if pl == 126:
            if pos+3 >= len(buf): break
            pl = (buf[pos+2]<<8)|buf[pos+3]; hl = 4
        elif pl == 127:
            if pos+9 >= len(buf): break
            pl = int.from_bytes(buf[pos+2:pos+10],'big'); hl = 10
        if m: hl += 4
        t = pos + hl + pl
        if t > len(buf): break
        if m:
            mk = buf[pos+hl-4:pos+hl]; r = bytearray(buf[pos+hl:t])
            for i in range(len(r)): r[i] ^= mk[i%4]
            frames.append(bytes(r))
        else:
            frames.append(buf[pos+hl:t])
        pos = t
    return frames, buf[pos:]

recv_buf = b''
send_buf = b''

def process(raw, d):
    global recv_buf, send_buf
    with lock:
        if d == 'R':
            recv_buf += raw
            frames, recv_buf = parse_ws(recv_buf)
        else:
            send_buf += raw
            frames, send_buf = parse_ws(send_buf)

    for frame in frames:
        with lock:
            all_frames.append((time.time(), d, frame))

r = subprocess.check_output(
    'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
    shell=True, text=True
).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
print(f"PIDs: {pids}")

JS = r'''
try {
    var s = Process.findModuleByName("libssl-1_1.dll");
    var ssl_write_fn = new NativeFunction(s.findExportByName("SSL_write"), 'int', ['pointer', 'pointer', 'int']);
    var gameSSL = null; var conns = {};
    Interceptor.attach(s.findExportByName("SSL_read"), {
        onEnter: function(a) { this.ssl=a[0]; this.buf=a[1]; },
        onLeave: function(r) {
            var n=r.toInt32(); if(n>0) {
                var p=this.ssl.toString(); var b0=this.buf.readU8();
                if(b0===0x82||b0===4||b0===3){gameSSL=this.ssl;conns[p]=true;}
                if(conns[p]) send({d:"R"}, this.buf.readByteArray(n));
            }
        }
    });
    Interceptor.attach(s.findExportByName("SSL_write"), {
        onEnter: function(a) {
            this.ssl=a[0]; var n=a[2].toInt32(); if(n>0) {
                var p=this.ssl.toString(); var b0=a[1].readU8();
                if(b0===0x82||b0===4||b0===3){gameSSL=this.ssl;conns[p]=true;}
                if(conns[p]) send({d:"S"}, a[1].readByteArray(n));
            }
        }
    });
    rpc.exports = {
        inject: function(hex) {
            if(!gameSSL) return "NO_SSL";
            var d=[]; for(var i=0;i<hex.length;i+=2) d.push(parseInt(hex.substr(i,2),16));
            var b=Memory.alloc(d.length); b.writeByteArray(d);
            return "OK:"+ssl_write_fn(gameSSL,b,d.length);
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
                payload = msg['payload']
                if payload.get('t') == 'ready':
                    print(f"  PID {p}: HOOK OK"); return
                if data:
                    process(bytes(data), payload.get('d', 'R'))
            return cb
        sc.on('message', make_cb(pid))
        sc.load()
        sessions.append((sess, sc, pid))
    except Exception as e:
        print(f"  PID {pid}: {e}")

print("Esperando (3s)...")
time.sleep(3)

for sess, sc, pid in sessions:
    try:
        if sc.exports_sync.inject("03").startswith("OK"):
            active_sc = sc
            print(f"Active: PID {pid}")
            break
    except: pass

if not active_sc:
    print("No active!"); sys.exit(1)

# Dump ALL frames from last N seconds
def dump_frames(since_ts, label=""):
    with lock:
        recent = [(t, d, f) for t, d, f in all_frames if t > since_ts]

    print(f"\n--- {label} ({len(recent)} frames) ---")
    for ts, d, frame in recent:
        if len(frame) < 1: continue
        ptype = frame[0]

        if ptype == 3:
            # Heartbeat - just note it
            pass
        elif ptype == 1 or ptype == 2:
            # Handshake / Response
            if ptype == 2 and len(frame) >= 4:
                rid = (frame[1]<<16)|(frame[2]<<8)|frame[3]
                body_hex = frame[4:60].hex() if len(frame) > 4 else ""
                # Try msgpack at different offsets
                body_decoded = None
                for off in range(4, min(len(frame), 10)):
                    try:
                        body_decoded = msgpack.unpackb(frame[off:], raw=False)
                        print(f"  {d} TYPE-2 RESP reqId={rid} (msgpack@{off}): {json.dumps(body_decoded, default=str, ensure_ascii=False)[:500]}")
                        break
                    except: pass
                if body_decoded is None:
                    print(f"  {d} TYPE-2 RESP reqId={rid} hex={body_hex}")
            else:
                print(f"  {d} TYPE-{ptype}: {frame[:40].hex()}")
        elif ptype == 4:
            if len(frame) < 4: continue
            plen = (frame[1]<<16)|(frame[2]<<8)|frame[3]
            pb = frame[4:4+plen]

            # Show raw bytes for analysis
            pb_hex = pb[:80].hex()

            if d == 'S':
                # Client send - we know the format
                if len(pb) >= 3:
                    rid = (pb[0]<<8)|pb[1]
                    rl = pb[2]
                    if 3+rl <= len(pb):
                        route = bytes(pb[3:3+rl]).decode('utf-8', errors='replace')
                        body_raw = pb[3+rl:]
                        try:
                            body = json.loads(body_raw)
                            print(f"  S REQ [{rid}] {route} = {json.dumps(body, ensure_ascii=False)[:200]}")
                        except:
                            print(f"  S REQ [{rid}] {route} body={body_raw[:40].hex()}")
            else:
                # Server push - try multiple decode strategies
                print(f"  R PUSH raw({len(pb)}b): {pb_hex}")

                # Strategy 1: [flags 1B] [routeCode 2B] [msgpack body]
                if len(pb) >= 3:
                    flags = pb[0]
                    rc = (pb[1]<<8)|pb[2]
                    for off in [3, 4, 5, 6]:
                        if off >= len(pb): break
                        try:
                            body = msgpack.unpackb(pb[off:], raw=False)
                            print(f"    Decode A (flags={flags} rc={rc} msgpack@{off}): {json.dumps(body, default=str, ensure_ascii=False)[:400]}")
                            break
                        except:
                            pass

                # Strategy 2: [routeLen 1B] [route] [msgpack body]
                if len(pb) >= 2:
                    rl = pb[0]
                    if rl < len(pb) and rl > 0 and rl < 100:
                        route = bytes(pb[1:1+rl]).decode('utf-8', errors='replace')
                        off2 = 1+rl
                        if off2 < len(pb):
                            try:
                                body = msgpack.unpackb(pb[off2:], raw=False)
                                print(f"    Decode B (routeLen={rl} route={route}): {json.dumps(body, default=str, ensure_ascii=False)[:400]}")
                            except:
                                pass

                # Strategy 3: [flags 1B] [routeLen 1B] [route] [msgpack body]
                if len(pb) >= 3:
                    flags = pb[0]
                    rl = pb[1]
                    if rl > 0 and rl < 100 and 2+rl <= len(pb):
                        route = bytes(pb[2:2+rl]).decode('utf-8', errors='replace')
                        off3 = 2+rl
                        if off3 < len(pb):
                            try:
                                body = msgpack.unpackb(pb[off3:], raw=False)
                                print(f"    Decode C (flags={flags} routeLen={rl} route={route}): {json.dumps(body, default=str, ensure_ascii=False)[:400]}")
                            except:
                                pass

                # Strategy 4: entire pb as msgpack
                try:
                    body = msgpack.unpackb(pb, raw=False)
                    print(f"    Decode D (full msgpack): {json.dumps(body, default=str, ensure_ascii=False)[:400]}")
                except:
                    pass
        else:
            print(f"  {d} UNK type={ptype}: {frame[:30].hex()}")

    sys.stdout.flush()

# First, just observe traffic for 5s without injecting
print("\n=== PASSIVE OBSERVATION (5s) ===")
ts0 = time.time()
time.sleep(5)
dump_frames(ts0, "Passive traffic")

# Now inject a request and see what comes back
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

print("\n=== INJECT joinGameRoom ===")
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

ts1 = time.time()
r = active_sc.exports_sync.inject(build_ws(pomelo).hex())
print(f"SSL_write: {r}")
time.sleep(6)
dump_frames(ts1, "After joinGameRoom inject")

print("\n\nDone!")
for sess, sc, pid in sessions:
    try: sc.unload()
    except: pass
    try: sess.detach()
    except: pass
