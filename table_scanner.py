"""Automated table scanner - injects joinGameRoom for each table and captures initinfo.
Uses the reconnection trick: injecting a request causes WS reconnect + auto-join."""
import frida, json, time, sys, os, msgpack, subprocess, threading, random
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

lock = threading.Lock()
raw_recv_chunks = []  # (timestamp, bytes)
inject_ts = 0
table_results = {}  # matchID -> {room, players, ...}

def parse_ws_frames(data):
    """Parse WS frames from raw data."""
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
        if end > len(data) or pl > 1000000:
            pos += 1; continue
        if masked:
            mk = data[pos+hl-4:pos+hl]
            payload = bytearray(data[pos+hl:end])
            for i in range(len(payload)): payload[i] ^= mk[i % 4]
            frames.append(bytes(payload))
        else:
            frames.append(data[pos+hl:end])
        pos = end
    return frames

def extract_initinfo(raw_bytes):
    """Extract initinfo from raw captured bytes."""
    # Find HTTP header end
    http_end = raw_bytes.find(b'\r\n\r\n')
    if http_end >= 0:
        ws_data = raw_bytes[http_end+4:]
    else:
        ws_data = raw_bytes

    frames = parse_ws_frames(ws_data)

    for frame in frames:
        if len(frame) < 5 or frame[0] != 4: continue
        plen = (frame[1]<<16)|(frame[2]<<8)|frame[3]
        pb = frame[4:4+plen]
        if len(pb) < 3: continue

        # Format: [flags 1B] [routeCode 1B] [msgpack body]
        try:
            body = msgpack.unpackb(pb[2:], raw=False)
        except:
            # Also try offset 3 (2-byte routeCode) just in case
            try:
                body = msgpack.unpackb(pb[3:], raw=False)
            except:
                continue

        if not isinstance(body, dict): continue
        event = body.get('event', '')

        if event == 'initinfo':
            return body

    return None

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
                if data and pl.get('d') == 'R':
                    with lock:
                        raw_recv_chunks.append((time.time(), bytes(data)))
            return cb
        sc.on('message', make_cb(pid))
        sc.load()
        sessions.append((sess, sc, pid))
    except Exception as e:
        print(f"  PID {pid}: {e}")

time.sleep(2)
for sess, sc, pid in sessions:
    try:
        r = sc.exports_sync.inject("03")
        if r.startswith("OK"):
            active_sc = sc; print(f"Active: PID {pid}"); break
    except: pass

if not active_sc:
    print("No active connection!"); sys.exit(1)

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

def scan_table(match_id, club_id, union_id, reqid=500):
    """Inject joinGameRoom and capture initinfo from reconnection."""
    global raw_recv_chunks

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
    pomelo = bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner

    # Clear recv buffer
    with lock:
        raw_recv_chunks.clear()

    inject_ts = time.time()
    r = active_sc.exports_sync.inject(build_ws(pomelo).hex())
    if not r.startswith("OK"):
        return None

    # Wait for reconnection and data
    time.sleep(8)

    # Collect all recv bytes after inject
    with lock:
        recv_after = [raw for ts, raw in raw_recv_chunks if ts > inject_ts]

    all_bytes = b''.join(recv_after)
    if len(all_bytes) < 100:
        return None

    return extract_initinfo(all_bytes)

# Load match data
scanner_file = os.path.expanduser('~/suprema_scanner.json')
if not os.path.exists(scanner_file):
    print("Run scanner_quick.py first to get match list!")
    sys.exit(1)

with open(scanner_file, 'r', encoding='utf-8') as f:
    sdata = json.load(f)

# Get active cash tables
cash_tables = []
for mid_str, m in sdata.get('matches', {}).items():
    players = m.get('!!', 0)
    if players > 0 and not m.get('prizePool'):
        cash_tables.append(m)

cash_tables.sort(key=lambda x: x.get('!!', 0), reverse=True)
print(f"\nActive cash tables: {len(cash_tables)}")
for t in cash_tables[:10]:
    print(f"  match={t['matchID']} club={t['clubID']} players={t.get('!!',0)} blinds={t.get('blinds','?')}")

# Scan each table
print(f"\n{'='*60}")
print("SCANNING TABLES")
print(f"{'='*60}")

for i, table in enumerate(cash_tables[:5]):  # Start with first 5
    mid = table['matchID']
    cid = table['clubID']
    uid = table['unionID']
    blinds = table.get('blinds', '?')

    print(f"\n[{i+1}/{min(len(cash_tables),5)}] Scanning match {mid} (club={cid} blinds={blinds})...")
    sys.stdout.flush()

    initinfo = scan_table(mid, cid, uid, reqid=500+i)

    if initinfo:
        data = initinfo.get('data', {})
        room = data.get('room', {})
        gs = data.get('game_seat', {})
        gm = data.get('gamer', {})

        print(f"  Room: {room.get('name', '?')}")
        players = []
        for uk, seat in gs.items():
            if not isinstance(seat, dict): continue
            u = seat.get('uid', uk)
            g = gm.get(str(u), {}) if isinstance(gm, dict) else {}
            if not isinstance(g, dict): g = {}
            agent = seat.get('agentID', 0)
            is_bot = agent != 0
            pinfo = {
                'name': g.get('displayID', '?'),
                'uid': u,
                'stack': seat.get('coins', 0),
                'winnings': seat.get('winnings', 0),
                'agentID': agent,
                'bot': is_bot,
                'club': g.get('clubID', 0),
                'country': g.get('countryCode', ''),
            }
            players.append(pinfo)
            bot_tag = " [BOT]" if is_bot else ""
            print(f"    {pinfo['name']}: stack={pinfo['stack']:.2f} win={pinfo['winnings']:+.2f}{bot_tag}")

        table_results[mid] = {
            'matchID': mid,
            'clubID': cid,
            'roomName': room.get('name', '?'),
            'blinds': room.get('options', {}).get('blinds', '?'),
            'maxPlayer': room.get('options', {}).get('maxPlayer', '?'),
            'players': players,
            'scanned_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
    else:
        print(f"  No initinfo received")

    # Wait between scans for connection to stabilize
    time.sleep(3)

# Save results
output_file = os.path.expanduser('~/table_scan_results.json')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(table_results, f, indent=2, default=str, ensure_ascii=False)

print(f"\n{'='*60}")
print(f"SCAN COMPLETE")
print(f"{'='*60}")
print(f"Tables scanned: {len(table_results)}/{min(len(cash_tables), 5)}")

# Summary
total_bots = 0
total_humans = 0
for mid, info in table_results.items():
    bots = sum(1 for p in info['players'] if p['bot'])
    humans = len(info['players']) - bots
    total_bots += bots
    total_humans += humans
    print(f"  {info['roomName']}: {len(info['players'])} players ({humans} human, {bots} bot)")

print(f"\nTotal: {total_humans} humans, {total_bots} bots")
print(f"Results saved to {output_file}")

for sess, sc, pid in sessions:
    try: sc.unload()
    except: pass
    try: sess.detach()
    except: pass
