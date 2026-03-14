"""Smart injection - capture real requests, replay with modifications."""
import frida, json, time, sys, os, msgpack, subprocess, threading, random, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Track multiple SSL connections separately
ssl_conns = {}  # ssl_ptr -> {'recv': [], 'send': [], 'type': 'unknown'}
lock = threading.Lock()
captured_requests = {}  # route -> (ssl_ptr, raw_pomelo_bytes)
last_reqid = 0
responses = {}  # reqId -> decoded body
got_response = threading.Event()

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

def process(raw, d, ssl_ptr):
    global last_reqid
    with lock:
        if ssl_ptr not in ssl_conns:
            ssl_conns[ssl_ptr] = {'recv_buf': b'', 'send_buf': b'', 'type': 'unknown',
                                   'heartbeats': 0, 'pomelo_frames': 0, 'routes': []}
        conn = ssl_conns[ssl_ptr]

        if d == 'RECV':
            conn['recv_buf'] += raw
            frames, conn['recv_buf'] = parse_ws(conn['recv_buf'])
        else:
            conn['send_buf'] += raw
            frames, conn['send_buf'] = parse_ws(conn['send_buf'])

    for frame in frames:
        if len(frame) < 1: continue
        ptype = frame[0]

        # Track heartbeats to identify game connection
        if ptype == 3:
            conn['heartbeats'] += 1
            conn['type'] = 'game'
            continue

        if ptype == 4:
            conn['pomelo_frames'] += 1
            conn['type'] = 'game'
            if len(frame) < 4: continue
            plen = (frame[1]<<16)|(frame[2]<<8)|frame[3]
            pb = frame[4:4+plen]

            if d == 'SEND':
                # Client request: [reqId 2B] [routeLen 1B] [route] [body]
                if len(pb) < 3: continue
                rid = (pb[0]<<8)|pb[1]
                if rid > last_reqid:
                    last_reqid = rid
                rl = pb[2]
                if 3+rl > len(pb): continue
                route = bytes(pb[3:3+rl]).decode('utf-8', errors='replace')
                body_bytes = pb[3+rl:]

                # Store the COMPLETE frame for replay
                captured_requests[route] = (ssl_ptr, frame, rid)

                # Try decode body
                try:
                    body = json.loads(body_bytes.decode('utf-8'))
                    print(f"  >>> [{rid}] {route} body={json.dumps(body, ensure_ascii=False)[:200]}")
                except:
                    try:
                        body = msgpack.unpackb(body_bytes, raw=False)
                        print(f"  >>> [{rid}] {route} msgpack_body={body}")
                    except:
                        print(f"  >>> [{rid}] {route} raw={body_bytes[:30].hex()}")

            else:
                # Server push: [flags 1B] [routeLen/routeCode] [body]
                if len(pb) < 1: continue
                flags = pb[0]
                if (flags & 1) == 0:
                    # Compressed route
                    if len(pb) >= 3:
                        rc = (pb[1]<<8)|pb[2]
                        body = None
                        if len(pb) > 3:
                            try: body = msgpack.unpackb(pb[3:], raw=False)
                            except: body = None
                        if isinstance(body, dict):
                            event = body.get('event', '')
                            if event == 'initinfo':
                                data = body.get('data', {})
                                room = data.get('room', {}) if isinstance(data, dict) else {}
                                gs = data.get('game_seat', {}) if isinstance(data, dict) else {}
                                gm = data.get('gamer', {}) if isinstance(data, dict) else {}
                                print(f"\n  *** INITINFO: {room.get('name','?')} ({len(gs)} seats) ***")
                                for uid, seat in gs.items():
                                    if not isinstance(seat, dict): continue
                                    g = gm.get(str(seat.get('uid', uid)), {})
                                    if not isinstance(g, dict): g = {}
                                    bot = " [BOT]" if seat.get('agentID', 0) else ""
                                    print(f"    {g.get('displayID','?')}: stack={seat.get('coins',0):.2f} win={seat.get('winnings',0):+.2f}{bot}")
                                got_response.set()
                            elif event == 'error':
                                print(f"  *** PUSH ERROR: {body.get('errorMessage', body)} ***")
                                got_response.set()
                            elif event not in ('countdown', 'clientPing', 'gameinfo',
                                             'matchesStatusPushNotify', 'apiClub.clubHandler.jackpot'):
                                print(f"  <<< PUSH rc={rc} event={event}")
                else:
                    # String route
                    if len(pb) < 2: continue
                    rl = pb[1]; off2 = 2+rl
                    route = bytes(pb[2:2+rl]).decode('utf-8', errors='replace')
                    body = None
                    if off2 < len(pb):
                        try: body = msgpack.unpackb(pb[off2:], raw=False)
                        except: pass
                    if isinstance(body, dict):
                        event = body.get('event', '')
                        if event == 'initinfo':
                            data = body.get('data', {})
                            room = data.get('room', {}) if isinstance(data, dict) else {}
                            gs = data.get('game_seat', {}) if isinstance(data, dict) else {}
                            gm = data.get('gamer', {}) if isinstance(data, dict) else {}
                            print(f"\n  *** INITINFO: {room.get('name','?')} ({len(gs)} seats) ***")
                            for uid, seat in gs.items():
                                if not isinstance(seat, dict): continue
                                g = gm.get(str(seat.get('uid', uid)), {})
                                if not isinstance(g, dict): g = {}
                                bot = " [BOT]" if seat.get('agentID', 0) else ""
                                print(f"    {g.get('displayID','?')}: stack={seat.get('coins',0):.2f} win={seat.get('winnings',0):+.2f}{bot}")
                            got_response.set()

        elif ptype == 2 and d == 'RECV':
            # Response to request
            if len(frame) < 4: continue
            req_id = (frame[1]<<16)|(frame[2]<<8)|frame[3]
            body = None
            if len(frame) > 4:
                try: body = msgpack.unpackb(frame[4:], raw=False)
                except: body = frame[4:30].hex()
            print(f"\n  *** RESPONSE [#{req_id}]: {body} ***")
            responses[req_id] = body
            got_response.set()

    sys.stdout.flush()

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

    // Track ALL SSL connections
    var sslPtrs = {};

    Interceptor.attach(ssl_read, {
        onEnter: function(a) { this.ssl = a[0]; this.buf = a[1]; },
        onLeave: function(r) {
            var n = r.toInt32();
            if (n > 0) {
                var ptr = this.ssl.toString();
                sslPtrs[ptr] = this.ssl;
                send({t:"d", d:"RECV", p:ptr}, this.buf.readByteArray(n));
            }
        }
    });

    Interceptor.attach(ssl_write, {
        onEnter: function(a) {
            this.ssl = a[0];
            var n = a[2].toInt32();
            if (n > 0) {
                var ptr = this.ssl.toString();
                sslPtrs[ptr] = this.ssl;
                send({t:"d", d:"SEND", p:ptr}, a[1].readByteArray(n));
            }
        }
    });

    rpc.exports = {
        inject: function(hexData, targetPtr) {
            // Find the right SSL pointer
            var ssl = null;
            if (targetPtr && sslPtrs[targetPtr]) {
                ssl = sslPtrs[targetPtr];
            } else {
                // Try all known game connections
                for (var p in sslPtrs) {
                    ssl = sslPtrs[p];
                    break;
                }
            }
            if (!ssl) return "NO_SSL";
            var data = [];
            for (var i = 0; i < hexData.length; i += 2)
                data.push(parseInt(hexData.substr(i, 2), 16));
            var buf = Memory.alloc(data.length);
            buf.writeByteArray(data);
            var ret = ssl_write_fn(ssl, buf, data.length);
            return "OK:" + ret + " ptr=" + ssl.toString();
        },
        listssl: function() {
            var ptrs = [];
            for (var p in sslPtrs) ptrs.push(p);
            return JSON.stringify(ptrs);
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
                    print(f"  PID {p}: HOOK OK")
                    sys.stdout.flush()
                    return
                if payload.get('t') == 'fatal':
                    print(f"  PID {p}: FATAL {payload.get('e')}")
                    return
                if payload.get('t') == 'd' and data:
                    process(bytes(data), payload.get('d', 'RECV'), payload.get('p', '?'))
            return cb
        sc.on('message', make_cb(pid))
        sc.load()
        sessions.append((sess, sc, pid))
        print(f"  Hooked PID {pid}")
    except Exception as e:
        print(f"  PID {pid}: {e}")

print("\nEsperando trafego (5s)...")
time.sleep(5)

# Identify game connections
print("\n=== SSL CONNECTIONS ===")
game_ssl_ptrs = []
for ptr, conn in ssl_conns.items():
    status = f"hb={conn['heartbeats']} pomelo={conn['pomelo_frames']} type={conn['type']}"
    print(f"  {ptr}: {status}")
    if conn['type'] == 'game':
        game_ssl_ptrs.append(ptr)

print(f"\nGame connections: {len(game_ssl_ptrs)}")
print(f"Captured routes: {list(captured_requests.keys())}")
print(f"Last reqId: {last_reqid}")

def build_ws_frame(payload):
    frame = bytearray([0x82])
    plen = len(payload)
    if plen < 126:
        frame.append(0x80 | plen)
    elif plen < 65536:
        frame.append(0x80 | 126)
        frame.extend(plen.to_bytes(2, 'big'))
    else:
        frame.append(0x80 | 127)
        frame.extend(plen.to_bytes(8, 'big'))
    mask = bytes([random.randint(0,255) for _ in range(4)])
    frame.extend(mask)
    masked = bytearray(payload)
    for i in range(len(masked)):
        masked[i] ^= mask[i % 4]
    frame.extend(masked)
    return bytes(frame)

def build_pomelo_request(reqid, route, body_json):
    route_bytes = route.encode('utf-8')
    body_bytes = body_json.encode('utf-8')
    inner = bytes([(reqid >> 8) & 0xFF, reqid & 0xFF, len(route_bytes)]) + route_bytes + body_bytes
    plen = len(inner)
    pomelo = bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner
    return pomelo

def inject_to_game(pomelo_bytes, target_ptr=None):
    ws = build_ws_frame(pomelo_bytes)
    for sess, sc, pid in sessions:
        try:
            ptrs = json.loads(sc.exports_sync.listssl())
            if not ptrs: continue
            # Try each SSL ptr on this PID
            for ptr in ptrs:
                if ptr in game_ssl_ptrs or target_ptr == ptr:
                    result = sc.exports_sync.inject(ws.hex(), ptr)
                    return result, ptr
            # Fallback: try first ptr
            result = sc.exports_sync.inject(ws.hex(), ptrs[0])
            return result, ptrs[0]
        except Exception as e:
            continue
    return "NO_SESSION", None

# Now test injection with proper SSL targeting
print("\n" + "="*60)
print("PHASE 1: Capture a real joinGameRoom request")
print("="*60)
print("Navega no app e entra numa mesa pra eu capturar o request real.")
print("Esperando 15s...")
sys.stdout.flush()

time.sleep(15)

print(f"\nCaptured routes after navigation:")
for route, (ptr, frame, rid) in captured_requests.items():
    print(f"  [{rid}] {route} -> SSL {ptr} ({len(frame)}b)")

# Check if we captured a joinGameRoom
if 'apiPlayer.playerHandler.joinGameRoom' in captured_requests:
    ptr, frame, orig_rid = captured_requests['apiPlayer.playerHandler.joinGameRoom']
    print(f"\n*** CAPTURED joinGameRoom on SSL {ptr} ***")
    print(f"  Original frame ({len(frame)}b): {frame.hex()}")

    # Parse it to understand the body format
    plen = (frame[1]<<16)|(frame[2]<<8)|frame[3]
    pb = frame[4:4+plen]
    rid = (pb[0]<<8)|pb[1]
    rl = pb[2]
    route = bytes(pb[3:3+rl]).decode('utf-8')
    body_raw = pb[3+rl:]
    print(f"  reqId={rid} route={route}")
    print(f"  Body bytes ({len(body_raw)}b): {body_raw.hex()}")

    # Try JSON decode
    try:
        body = json.loads(body_raw.decode('utf-8'))
        print(f"  Body (JSON): {json.dumps(body, ensure_ascii=False)}")
    except:
        try:
            body = msgpack.unpackb(body_raw, raw=False)
            print(f"  Body (msgpack): {body}")
        except:
            print(f"  Body: could not decode")

    # Now replay with modified reqId to a DIFFERENT match
    print("\n" + "="*60)
    print("PHASE 2: Replay captured request with new reqId")
    print("="*60)

    # Use next reqId
    new_rid = last_reqid + 10
    # Rebuild with same body but new reqId
    new_inner = bytes([(new_rid >> 8) & 0xFF, new_rid & 0xFF, rl]) + pb[3:3+rl] + body_raw
    new_plen = len(new_inner)
    new_pomelo = bytes([4, (new_plen >> 16) & 0xFF, (new_plen >> 8) & 0xFF, new_plen & 0xFF]) + new_inner

    print(f"  Replaying with reqId={new_rid} to SSL {ptr}")
    got_response.clear()
    responses.clear()

    result, used_ptr = inject_to_game(new_pomelo, ptr)
    print(f"  Result: {result}")
    sys.stdout.flush()

    if got_response.wait(timeout=8):
        print("  RESPONSE RECEIVED!")
    else:
        print("  No response after 8s")

    # Also try on ALL game SSL connections
    print("\n  Trying ALL SSL connections:")
    for gptr in game_ssl_ptrs:
        if gptr == used_ptr: continue
        new_rid += 1
        new_inner = bytes([(new_rid >> 8) & 0xFF, new_rid & 0xFF, rl]) + pb[3:3+rl] + body_raw
        new_plen = len(new_inner)
        new_pomelo = bytes([4, (new_plen >> 16) & 0xFF, (new_plen >> 8) & 0xFF, new_plen & 0xFF]) + new_inner

        got_response.clear()
        result, _ = inject_to_game(new_pomelo, gptr)
        print(f"    SSL {gptr}: {result}")
        if got_response.wait(timeout=5):
            print(f"    *** GOT RESPONSE ON {gptr}! ***")
            break
else:
    print("\nNo joinGameRoom captured. Trying manual injection on each game SSL...")

    # Load scanner data for target matches
    scanner_file = os.path.expanduser('~/suprema_scanner.json')
    if os.path.exists(scanner_file):
        with open(scanner_file, 'r', encoding='utf-8') as f:
            sdata = json.load(f)
        cash = [(k, m) for k, m in sdata.get('matches', {}).items()
                if m.get('!!', 0) > 0 and not m.get('prizePool')]
        if cash:
            mid_str, m = cash[0]
            cid = m['clubID']
            uid = m['unionID']
            room_id = f"{cid}_{m['matchID']}#{uid}@41157%128"
            body = json.dumps({
                "clubID": str(cid), "unionID": uid,
                "myClubID": 41157, "myUnionID": 128,
                "roomID": room_id,
                "privatecode": None, "ver": 7288, "lan": "pt", "verPackage": "5"
            })
            print(f"\n  Target: match={m['matchID']} room={room_id}")

            for i, gptr in enumerate(game_ssl_ptrs):
                new_rid = last_reqid + 20 + i
                pomelo = build_pomelo_request(new_rid, "apiPlayer.playerHandler.joinGameRoom", body)
                print(f"\n  Trying SSL {gptr} (reqId={new_rid})...")
                got_response.clear()
                result, _ = inject_to_game(pomelo, gptr)
                print(f"    Result: {result}")
                if got_response.wait(timeout=5):
                    print(f"    *** GOT RESPONSE! ***")
                    break
                else:
                    print(f"    No response")
        else:
            print("  No active cash tables in scanner data")
    else:
        print("  No scanner data file")

# Monitor for a bit more
print("\nMonitorando mais 10s...")
sys.stdout.flush()
time.sleep(10)

# Final status
print("\n=== FINAL STATUS ===")
print(f"SSL connections: {len(ssl_conns)}")
for ptr, conn in ssl_conns.items():
    print(f"  {ptr}: hb={conn['heartbeats']} pomelo={conn['pomelo_frames']} type={conn['type']}")
print(f"Captured routes: {list(captured_requests.keys())}")
print(f"Responses: {responses}")

for sess, sc, pid in sessions:
    try: sc.unload()
    except: pass
    try: sess.detach()
    except: pass
print("Done.")
