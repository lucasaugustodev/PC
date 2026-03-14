"""Test protocol injection - send joinGameRoom without UI."""
import frida, json, time, sys, os, subprocess, msgpack, threading, random
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

recv_buf = b''
send_buf = b''
lock = threading.Lock()
last_reqid = 0
responses = {}  # reqId -> response body
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

def process(raw, d):
    global recv_buf, send_buf, last_reqid
    with lock:
        if d == 'RECV':
            recv_buf += raw
            frames, recv_buf = parse_ws(recv_buf)
        else:
            send_buf += raw
            frames, send_buf = parse_ws(send_buf)

    for frame in frames:
        if len(frame) < 4: continue
        ptype = frame[0]

        if d == 'SEND' and ptype == 4:
            plen = (frame[1]<<16)|(frame[2]<<8)|frame[3]
            pb = frame[4:4+plen]
            if len(pb) >= 3:
                rid = (pb[0]<<8)|pb[1]
                if rid > last_reqid:
                    last_reqid = rid
                rl = pb[2]
                if 3+rl <= len(pb):
                    route = bytes(pb[3:3+rl]).decode('utf-8', errors='replace')
                    print(f"  >>> [{rid}] {route}")

        elif d == 'RECV' and ptype == 4:
            plen = (frame[1]<<16)|(frame[2]<<8)|frame[3]
            pb = frame[4:4+plen]
            if len(pb) < 2: continue
            rl = pb[1]; off = 2+rl
            route = bytes(pb[2:2+rl]).decode('utf-8', errors='replace')
            body = None
            if off < len(pb):
                try: body = msgpack.unpackb(pb[off:], raw=False)
                except: continue
            if not isinstance(body, dict): continue
            event = body.get('event', '')

            if event == 'initinfo':
                data = body.get('data', {})
                room = data.get('room', {}) if isinstance(data, dict) else {}
                gs = data.get('game_seat', {}) if isinstance(data, dict) else {}
                gm = data.get('gamer', {}) if isinstance(data, dict) else {}
                print(f"\n  *** INITINFO: {room.get('name','?')} ***")
                for uid, seat in gs.items():
                    if not isinstance(seat, dict): continue
                    g = gm.get(str(seat.get('uid', uid)), {})
                    if not isinstance(g, dict): g = {}
                    bot = " [BOT]" if seat.get('agentID', 0) else ""
                    print(f"    {g.get('displayID','?')}: stack={seat.get('coins',0):.2f} win={seat.get('winnings',0):+.2f}{bot}")
                got_response.set()

            elif event == 'joinGameRoom':
                api = body.get('apiData', {})
                rl2 = api.get('roomList', {})
                print(f"\n  *** JOINGAMEROOM RESPONSE: {len(rl2)} rooms ***")
                for rid, rinfo in rl2.items():
                    print(f"    Room {rid}: {rinfo}")
                got_response.set()

            elif event == 'error':
                print(f"\n  *** ERROR: {body.get('errorMessage', body)} ***")
                got_response.set()

            elif event not in ('countdown', 'clientPing', 'gameinfo',
                               'matchesStatusPushNotify', 'apiClub.clubHandler.jackpot'):
                print(f"  <<< {event}")

        sys.stdout.flush()

# Find PIDs
r = subprocess.check_output(
    'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
    shell=True, text=True
).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
print(f"PIDs: {pids}")

# Frida script with RPC inject function
JS = r'''
try {
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    var ssl_read = sslmod.findExportByName("SSL_read");
    var ssl_write = sslmod.findExportByName("SSL_write");
    var ssl_write_fn = new NativeFunction(ssl_write, 'int', ['pointer', 'pointer', 'int']);

    var gameSSL = null;
    var sslConns = {};

    Interceptor.attach(ssl_read, {
        onEnter: function(args) { this.ssl = args[0]; this.buf = args[1]; },
        onLeave: function(retval) {
            var n = retval.toInt32();
            if (n > 0) {
                var ptr = this.ssl.toString();
                // Detect game connection by looking for Pomelo/WS data
                var b0 = this.buf.readU8();
                if (b0 === 0x82 || b0 === 4) {
                    gameSSL = this.ssl;
                    sslConns[ptr] = true;
                }
                if (sslConns[ptr]) {
                    send({t:"d", d:"RECV"}, this.buf.readByteArray(n));
                }
            }
        }
    });

    Interceptor.attach(ssl_write, {
        onEnter: function(args) {
            this.ssl = args[0];
            var n = args[2].toInt32();
            if (n > 0) {
                var ptr = this.ssl.toString();
                var b0 = args[1].readU8();
                if (b0 === 0x82 || b0 === 4) {
                    gameSSL = this.ssl;
                    sslConns[ptr] = true;
                }
                if (sslConns[ptr]) {
                    send({t:"d", d:"SEND"}, args[1].readByteArray(n));
                }
            }
        }
    });

    rpc.exports = {
        inject: function(hexData) {
            if (!gameSSL) return "NO_GAME_SSL";
            var data = [];
            for (var i = 0; i < hexData.length; i += 2)
                data.push(parseInt(hexData.substr(i, 2), 16));
            var buf = Memory.alloc(data.length);
            buf.writeByteArray(data);
            var ret = ssl_write_fn(gameSSL, buf, data.length);
            return "OK:" + ret;
        },
        hasssl: function() {
            return gameSSL ? "YES" : "NO";
        }
    };
    send({t:"ready"});
} catch(e) { send({t:"fatal", e:e.toString()}); }
'''

# Hook all PIDs and find the one with inject capability
active_sc = None
sessions = []

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
                if payload.get('t') == 'd' and data:
                    process(bytes(data), payload.get('d', 'RECV'))
            return cb
        sc.on('message', make_cb(pid))
        sc.load()
        sessions.append((sess, sc, pid))
        print(f"  Hooked PID {pid}")
    except Exception as e:
        print(f"  PID {pid}: {e}")

# Wait for traffic to establish gameSSL
print("\nEsperando detectar conexao SSL do jogo (3s)...")
time.sleep(3)

# Find which PID has gameSSL
for sess, sc, pid in sessions:
    try:
        r = sc.exports_sync.hasssl()
        if r == "YES":
            active_sc = sc
            print(f"  PID {pid}: gameSSL FOUND!")
            break
    except:
        pass

if not active_sc:
    print("Nenhum gameSSL encontrado. Navega no app e tenta de novo.")
    sys.exit(1)

def build_ws_frame(payload):
    """Build masked WebSocket binary frame."""
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
    """Build Pomelo type-4 client request: [4][plen 3B][reqId 2B][routeLen 1B][route][JSON body]"""
    route_bytes = route.encode('utf-8')
    body_bytes = body_json.encode('utf-8')
    inner = bytes([(reqid >> 8) & 0xFF, reqid & 0xFF, len(route_bytes)]) + route_bytes + body_bytes
    plen = len(inner)
    pomelo = bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner
    return pomelo

def inject(pomelo_bytes):
    """Wrap in WS frame and inject via SSL_write."""
    ws = build_ws_frame(pomelo_bytes)
    result = active_sc.exports_sync.inject(ws.hex())
    return result

# Wait to capture current reqId
print(f"\nUltimo reqId capturado: {last_reqid}")
print("Esperando 5s pra pegar mais reqIds do trafego real...")
time.sleep(5)
print(f"Ultimo reqId agora: {last_reqid}")

# Get match IDs from the scanner data
scanner_file = os.path.expanduser('~/suprema_scanner.json')
target_matches = []
if os.path.exists(scanner_file):
    with open(scanner_file, 'r', encoding='utf-8') as f:
        sdata = json.load(f)
    for mid, m in sdata.get('matches', {}).items():
        players = m.get('!!', 0)
        prize = m.get('prizePool', 0)
        if players > 0 and not prize:  # Active cash tables only
            target_matches.append(m)
    print(f"\nFound {len(target_matches)} active cash tables to scan")
else:
    print("No scanner data found. Run scanner_quick.py first.")

# Test injection with a simple request first
print("\n" + "="*50)
print("TEST 1: Injetando joinGameRoom...")
print("="*50)

if target_matches:
    m = target_matches[0]
    mid = m['matchID']
    cid = m['clubID']
    uid = m['unionID']

    next_reqid = last_reqid + 1
    room_id = f"{cid}_{mid}#{uid}@41157%128"
    body = json.dumps({
        "clubID": str(cid),
        "unionID": uid,
        "myClubID": 41157,
        "myUnionID": 128,
        "roomID": room_id,
        "privatecode": None,
        "ver": 7288,
        "lan": "pt",
        "verPackage": "5"
    })

    print(f"  Target: match={mid} roomID={room_id}")
    print(f"  reqId={next_reqid}")

    pomelo = build_pomelo_request(
        next_reqid,
        "apiPlayer.playerHandler.joinGameRoom",
        body
    )
    print(f"  Pomelo ({len(pomelo)}b): {pomelo[:30].hex()}...")

    got_response.clear()
    result = inject(pomelo)
    print(f"  SSL_write result: {result}")

    print("  Esperando resposta (10s)...")
    if got_response.wait(timeout=10):
        print("  RESPOSTA RECEBIDA!")
    else:
        print("  Sem resposta :(")

    # Try enter too
    next_reqid += 1
    enter_body = json.dumps({
        "f": "enter",
        "roomID": room_id,
        "ver": 7288,
        "lan": "pt",
        "verPackage": "5"
    })
    print(f"\nTEST 2: Injetando clientMessage enter (reqId={next_reqid})...")
    pomelo2 = build_pomelo_request(
        next_reqid,
        "room.roomHandler.clientMessage",
        enter_body
    )
    got_response.clear()
    result2 = inject(pomelo2)
    print(f"  SSL_write result: {result2}")

    if got_response.wait(timeout=10):
        print("  RESPOSTA RECEBIDA!")
    else:
        print("  Sem resposta :(")

print("\nMonitorando mais 10s...")
time.sleep(10)

print("\nDone.")
for sess, sc, pid in sessions:
    try: sc.unload()
    except: pass
    try: sess.detach()
    except: pass
