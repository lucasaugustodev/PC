"""Suprema Table Scanner - Collects all table/match data from SupremaPoker.
Hooks all PIDs, collects matchesStatusPushNotify + initinfo data,
and presents a live dashboard of all tables with player info."""
import frida, json, time, sys, os, subprocess, threading
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import msgpack
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'msgpack'])
    import msgpack

# ============ STATE ============
lock = threading.Lock()
send_buf = b''
recv_buf = b''

# Collected data
matches = {}       # matchID -> match info from matchesStatusPushNotify
rooms = {}         # roomID -> {players, seats, game_info, room_config}
all_routes = set() # All unique routes seen
client_requests = [] # All client requests captured

LOG_FILE = os.path.expanduser('~/suprema_scanner.log')

# ============ WS + POMELO PARSING ============
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
            if len(pbody) < 3: return None
            reqId = (pbody[0] << 8) | pbody[1]
            rlen = pbody[2]
            if 3 + rlen > len(pbody): return None
            route = bytes(pbody[3:3+rlen]).decode('utf-8', errors='replace')
            body = None
            body_raw = pbody[3+rlen:]
            if body_raw:
                try: body = json.loads(body_raw.decode('utf-8', errors='replace'))
                except:
                    try: body = msgpack.unpackb(body_raw, raw=False)
                    except: body = None
            return {'type': 'REQUEST', 'reqId': reqId, 'route': route, 'body': body}
        else:
            if len(pbody) < 2: return None
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
    if ptype == 3: return {'type': 'HEARTBEAT'}
    return None

# ============ DATA PROCESSING ============
def process_match_status(data):
    """Process matchesStatusPushNotify to collect all match info."""
    api = data.get('apiData', data)
    status = api.get('matchesStatus', {})
    match_list = status.get('matches', [])

    with lock:
        for m in match_list:
            mid = m.get('matchID', 0)
            if not mid: continue
            matches[mid] = {
                'matchID': mid,
                'clubID': m.get('clubID', 0),
                'unionID': m.get('unionID', 0),
                'queueCount': m.get('queueCount', 0),
                'players': m.get('!!', 0),  # Player count
                'prizePool': m.get('prizePool', 0),
                'bountyPool': m.get('bountyPool', 0),
                'pinToSpecial': m.get('pinToSpecial', 0),
                'unionWhiteList': m.get('unionWhiteList', []),
                'running': m.get('!$', False),
                'started': m.get('!%', False),
                'totalPlayers': m.get('!f', 0),
                'maxPlayers': m.get('!g', 0),
                'remainingPlayers': m.get('!R', 0),
                'tables': m.get('!S', 0),
                'updated': time.strftime('%H:%M:%S'),
                'raw': m,
            }

def process_initinfo(data, room_id=None):
    """Process initinfo to collect room/player details."""
    info = data.get('data', {})
    if not isinstance(info, dict): return

    room_info = info.get('room', {})
    game_seat = info.get('game_seat', {})
    gamers = info.get('gamer', {})
    game_info = info.get('game_info', {})

    rid = room_id or room_info.get('id', 'unknown')

    players = []
    for uid_str, seat in game_seat.items():
        if not isinstance(seat, dict): continue
        uid = seat.get('uid', uid_str)
        gamer = gamers.get(str(uid), gamers.get(uid, {}))
        if not isinstance(gamer, dict): gamer = {}
        players.append({
            'uid': uid,
            'name': gamer.get('displayID', str(uid)),
            'clubID': gamer.get('clubID', 0),
            'seat': seat.get('seat', -1),
            'coins': seat.get('coins', 0),
            'winnings': seat.get('winnings', 0),
            'agentID': seat.get('agentID', 0),
            'isBot': seat.get('agentID', 0) != 0,
            'sitout': seat.get('sitout', False),
            'ready': seat.get('ready', False),
        })

    with lock:
        rooms[rid] = {
            'roomID': rid,
            'name': room_info.get('name', '?'),
            'type': room_info.get('type', 0),
            'players': players,
            'gamers_count': game_info.get('gamers_count', 0),
            'pot': game_info.get('pot', 0),
            'state': game_info.get('state', 0),
            'running': game_info.get('running', False),
            'options': room_info.get('options', {}),
            'updated': time.strftime('%H:%M:%S'),
        }

def process_updateseat(data):
    """Update seat info for a room."""
    room_id = data.get('roomID', '')
    game_seat = data.get('game_seat', {})
    gamers = data.get('gamer', {})

    with lock:
        if room_id not in rooms:
            rooms[room_id] = {'roomID': room_id, 'players': [], 'updated': time.strftime('%H:%M:%S')}

        room = rooms[room_id]
        for uid_str, seat in game_seat.items():
            if not isinstance(seat, dict): continue
            uid = seat.get('uid', uid_str)
            gamer = gamers.get(str(uid), {}) if isinstance(gamers, dict) else {}

            # Update or add player
            found = False
            for p in room['players']:
                if p['uid'] == uid:
                    p['coins'] = seat.get('coins', p.get('coins', 0))
                    p['winnings'] = seat.get('winnings', p.get('winnings', 0))
                    p['agentID'] = seat.get('agentID', p.get('agentID', 0))
                    p['isBot'] = seat.get('agentID', 0) != 0
                    p['sitout'] = seat.get('sitout', False)
                    p['ready'] = seat.get('ready', False)
                    if isinstance(gamer, dict) and gamer.get('displayID'):
                        p['name'] = gamer.get('displayID', p.get('name', ''))
                    found = True
                    break
            if not found and isinstance(gamer, dict):
                room['players'].append({
                    'uid': uid,
                    'name': gamer.get('displayID', str(uid)),
                    'clubID': gamer.get('clubID', 0),
                    'seat': seat.get('seat', -1),
                    'coins': seat.get('coins', 0),
                    'winnings': seat.get('winnings', 0),
                    'agentID': seat.get('agentID', 0),
                    'isBot': seat.get('agentID', 0) != 0,
                    'sitout': seat.get('sitout', False),
                    'ready': seat.get('ready', False),
                })
        room['updated'] = time.strftime('%H:%M:%S')

def handle_decoded(direction, decoded):
    """Route decoded messages to appropriate handlers."""
    if not decoded or decoded.get('type') == 'HEARTBEAT': return

    route = decoded.get('route', '')
    body = decoded.get('body', {})

    if route: all_routes.add(f"{direction}:{route}")

    if direction == 'SEND':
        client_requests.append({
            'time': time.strftime('%H:%M:%S'),
            'reqId': decoded.get('reqId', 0),
            'route': route,
            'body': body,
        })

    if not isinstance(body, dict): return
    event = body.get('event', '')
    data = body.get('data', body.get('apiData', body))

    if event == 'matchesStatusPushNotify' or 'matchesStatusPushNotify' in str(event):
        process_match_status(body)
    elif event == 'initinfo':
        process_initinfo(body)
    elif event == 'updateseat':
        process_updateseat(body.get('data', {}))
    elif event == 'updategamer':
        # Track gamer updates
        pass

# ============ FRIDA HOOKS ============
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
        if decoded:
            handle_decoded(direction, decoded)

def find_pids():
    r = subprocess.check_output(
        'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
        shell=True, text=True
    ).strip()
    pids = []
    for line in r.splitlines():
        if 'SupremaPoker' in line:
            pids.append(int(line.split(',')[1].strip('"')))
    return pids

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

# ============ DISPLAY ============
def print_dashboard():
    """Print current state."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"\033[93m{'='*70}")
    print(f"  SUPREMA TABLE SCANNER - {time.strftime('%H:%M:%S')}")
    print(f"  Matches: {len(matches)} | Rooms: {len(rooms)} | Routes: {len(all_routes)}")
    print(f"{'='*70}\033[0m")

    # Show rooms with player details
    with lock:
        if rooms:
            print(f"\n\033[96m--- ROOMS (entered) ---\033[0m")
            for rid, room in rooms.items():
                name = room.get('name', rid)
                opts = room.get('options', {})
                blinds = opts.get('blinds', opts.get('smallblinds', '?'))
                print(f"\n  \033[93m{name}\033[0m ({rid})")
                if opts:
                    print(f"    Blinds: {blinds} | MaxPlayers: {opts.get('maxPlayer', '?')} | Fee: {opts.get('feeRate', '?')}%")
                for p in room.get('players', []):
                    bot_tag = " \033[91m[BOT]\033[0m" if p.get('isBot') else ""
                    sit_tag = " [SITOUT]" if p.get('sitout') else ""
                    print(f"    Seat {p.get('seat','-')}: \033[97m{p.get('name','?')}\033[0m"
                          f" stack={p.get('coins',0):.2f} win={p.get('winnings',0):+.2f}"
                          f" club={p.get('clubID',0)}{bot_tag}{sit_tag}")

        # Show match summary
        if matches:
            # Group by type
            cash_matches = []
            mtt_matches = []
            for mid, m in matches.items():
                if m.get('prizePool', 0) > 0 or m.get('bountyPool', 0) > 0:
                    mtt_matches.append(m)
                else:
                    cash_matches.append(m)

            if cash_matches:
                print(f"\n\033[92m--- CASH TABLES ({len(cash_matches)}) ---\033[0m")
                for m in sorted(cash_matches, key=lambda x: -x.get('players', 0))[:15]:
                    p = m.get('players', 0)
                    if p == 0: continue
                    print(f"  Match {m['matchID']}: {p} players | club={m.get('clubID',0)}")

            if mtt_matches:
                print(f"\n\033[95m--- MTT TOURNAMENTS ({len(mtt_matches)}) ---\033[0m")
                for m in sorted(mtt_matches, key=lambda x: -x.get('players', 0))[:10]:
                    p = m.get('players', 0)
                    prize = m.get('prizePool', 0)
                    bounty = m.get('bountyPool', 0)
                    remain = m.get('remainingPlayers', 0)
                    tables = m.get('tables', 0)
                    running = "RUNNING" if m.get('running') else "waiting"
                    print(f"  Match {m['matchID']}: {p} entries, {remain} remain, {tables} tables"
                          f" | prize={prize:.0f} bounty={bounty:.0f} | {running}")

    # Show unique routes
    if all_routes:
        print(f"\n\033[90m--- Routes seen: {', '.join(sorted(all_routes)[:20])}\033[0m")

    # Log to file
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"=== Suprema Scanner - {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
        f.write(f"Matches: {len(matches)} | Rooms: {len(rooms)}\n\n")

        for rid, room in rooms.items():
            f.write(f"Room: {room.get('name', rid)} ({rid})\n")
            for p in room.get('players', []):
                bot = " [BOT]" if p.get('isBot') else ""
                f.write(f"  {p.get('name','?')}: stack={p.get('coins',0):.2f} win={p.get('winnings',0):+.2f}{bot}\n")
            f.write("\n")

        f.write(f"\nAll matches ({len(matches)}):\n")
        f.write(json.dumps(list(matches.values()), indent=2, default=str, ensure_ascii=False))

# ============ MAIN ============
pids = find_pids()
if not pids:
    print("SupremaPoker not running!")
    sys.exit(1)

print(f"Found {len(pids)} SupremaPoker processes: {pids}")

sessions = []
scripts = []

def make_handler(pid):
    def on_msg(msg, data):
        if msg['type'] != 'send': return
        p = msg['payload']
        if p.get('t') == 'ready':
            print(f"  PID {pid}: HOOK OK!")
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

print(f"\nScanning {len(scripts)} processes...")
print("Navigate in the app - data appears automatically!")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        time.sleep(3)
        print_dashboard()
except KeyboardInterrupt:
    pass

print("\nSaving final state...")
print_dashboard()

for sc in scripts:
    try: sc.unload()
    except: pass
for sess in sessions:
    try: sess.detach()
    except: pass
print("Done.")
