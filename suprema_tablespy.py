"""Suprema Table Spy - Joins other rooms silently to gather player intel."""
import frida, json, time, sys, os, subprocess, threading, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import msgpack
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'msgpack'])
    import msgpack

def find_pid():
    r = subprocess.check_output(
        'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
        shell=True, text=True
    ).strip()
    for line in r.splitlines():
        if 'SupremaPoker' in line:
            return int(line.split(',')[1].strip('"'))
    return None

pid = find_pid()
if not pid:
    print("SupremaPoker not running!")
    sys.exit(1)

LOG_FILE = os.path.expanduser('~/suprema_tablespy.log')
lock = threading.Lock()
recv_buf = b''

def log(msg):
    """Print and log to file."""
    print(msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        # Strip ANSI color codes for file
        import re
        clean = re.sub(r'\033\[[0-9;]*m', '', msg)
        f.write(clean + '\n')

# Collected data
rooms_data = {}  # roomID -> game state
responses = {}   # store responses by route
pending_rooms = []
current_spy_room = None

def parse_ws_frames(buf):
    frames = []
    pos = 0
    while pos < len(buf):
        if pos + 1 >= len(buf):
            break
        b0 = buf[pos]
        b1 = buf[pos + 1]
        opcode = b0 & 0x0F
        if opcode not in (0x01, 0x02, 0x08, 0x09, 0x0A) and (b0 & 0x80) == 0:
            pos += 1
            continue
        masked = (b1 & 0x80) != 0
        payload_len = b1 & 0x7F
        header_len = 2
        if payload_len == 126:
            if pos + 3 >= len(buf): break
            payload_len = (buf[pos + 2] << 8) | buf[pos + 3]
            header_len = 4
        elif payload_len == 127:
            if pos + 9 >= len(buf): break
            payload_len = int.from_bytes(buf[pos + 2:pos + 10], 'big')
            header_len = 10
        if masked:
            header_len += 4
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

def decode_pomelo(payload):
    """Decode Pomelo message (type 2=response, type 4=push)."""
    if len(payload) < 2:
        return None
    ptype = payload[0]

    # Type 4: Server PUSH
    if ptype == 4 and len(payload) >= 5:
        plen = (payload[1] << 16) | (payload[2] << 8) | payload[3]
        pbody = payload[4:4 + plen]
        if len(pbody) < 2:
            return None
        rlen = pbody[1]
        off = 2 + rlen
        route = ''
        try:
            route = bytes(pbody[2:2 + rlen]).decode('utf-8', errors='replace')
        except:
            pass
        body = None
        if off < len(pbody):
            try:
                body = msgpack.unpackb(pbody[off:], raw=False)
            except:
                pass
        return {'type': 'PUSH', 'route': route, 'body': body}

    # Type 2: RESPONSE to our request
    if ptype == 2 and len(payload) >= 4:
        req_id = (payload[1] << 16) | (payload[2] << 8) | payload[3]
        body = None
        if len(payload) > 4:
            try:
                body = msgpack.unpackb(payload[4:], raw=False)
            except:
                pass
        return {'type': 'RESPONSE', 'reqId': req_id, 'body': body}

    return None

req_counter = 100

def build_pomelo_request(route, body_dict):
    """Build a Pomelo type-4 message (same format client uses).
    Wire format: [type=4] [plen_h] [plen_m] [plen_l] [flags=0x06] [route_len] [route] [msgpack]
    """
    global req_counter
    route_bytes = route.encode('utf-8')
    body_bytes = msgpack.packb(body_dict, use_bin_type=True)
    rlen = len(route_bytes)
    req_id = req_counter
    req_counter += 1
    # pbody: [flags] [route_len] [route] [msgpack]
    pbody = bytes([req_id & 0xFF, rlen]) + route_bytes + body_bytes
    plen = len(pbody)
    # header: [type=4] [len 3 bytes]
    header = bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF])
    return header + pbody

def build_ws_frame(payload, masked=True):
    """Wrap payload in a WebSocket binary frame."""
    frame = bytearray()
    frame.append(0x82)  # FIN + binary

    plen = len(payload)
    if masked:
        if plen < 126:
            frame.append(0x80 | plen)
        elif plen < 65536:
            frame.append(0x80 | 126)
            frame.extend(plen.to_bytes(2, 'big'))
        else:
            frame.append(0x80 | 127)
            frame.extend(plen.to_bytes(8, 'big'))

        # Generate mask key
        import random
        mask = bytes([random.randint(0, 255) for _ in range(4)])
        frame.extend(mask)

        # Mask payload
        masked_payload = bytearray(payload)
        for i in range(len(masked_payload)):
            masked_payload[i] ^= mask[i % 4]
        frame.extend(masked_payload)
    else:
        if plen < 126:
            frame.append(plen)
        elif plen < 65536:
            frame.append(126)
            frame.extend(plen.to_bytes(2, 'big'))
        else:
            frame.append(127)
            frame.extend(plen.to_bytes(8, 'big'))
        frame.extend(payload)

    return bytes(frame)

def process_recv(raw):
    """Process incoming data for spy responses."""
    global recv_buf
    with lock:
        recv_buf += raw
        frames, recv_buf = parse_ws_frames(recv_buf)
        for frame in frames:
            decoded = decode_pomelo(frame)
            if not decoded or not decoded.get('body'):
                continue
            body = decoded['body']
            if not isinstance(body, dict):
                continue

            msg_type = decoded.get('type', '')
            req_id = decoded.get('reqId', '')

            # Log all responses for debugging
            if msg_type == 'RESPONSE':
                log(f"  RESPONSE [#{req_id}]: {json.dumps(body, default=str, ensure_ascii=False)[:300]}")

            event = body.get('event', '')
            route = body.get('route', '')
            data = body.get('data', body.get('apiData', {}))

            # Log ALL events for debug
            if event:
                log(f"  [EVT] {event} (type={msg_type})")

            # joinGameRoom response - contains room list
            if event == 'apiPlayer.playerHandler.joinGameRoom':
                api = body.get('apiData', {})
                room_list = api.get('roomList', {})
                log(f"  Got roomList with {len(room_list)} rooms")
                for rid, rinfo in room_list.items():
                    if isinstance(rinfo, dict):
                        responses[f'roomList_{rid}'] = rinfo
                        log(f"    Room {rid}: {json.dumps(rinfo, default=str)[:200]}")

            # initinfo - full room state when entering
            if event == 'initinfo':
                room_data = data if isinstance(data, dict) else {}
                room_info = room_data.get('room', {})
                room_id = room_info.get('id', '?')
                room_name = room_info.get('name', '?')

                game_seat = room_data.get('game_seat', {})
                gamers = room_data.get('gamer', {})
                game_info = room_data.get('game_info', {})

                print(f"\n\033[93m{'='*60}")
                print(f"  MESA: {room_name} ({room_id})")
                print(f"  Jogadores: {game_info.get('gamers_count', '?')} | Pot: {game_info.get('pot', 0)} | Hand #{game_info.get('game_counter', '?')}")
                print(f"{'='*60}\033[0m")

                players = []
                for uid_str, seat_data in game_seat.items():
                    if not isinstance(seat_data, dict):
                        continue
                    gamer_info = gamers.get(uid_str, gamers.get(str(uid_str), {}))
                    if not isinstance(gamer_info, dict):
                        gamer_info = {}

                    player = {
                        'uid': uid_str,
                        'name': gamer_info.get('displayID', f'uid_{uid_str}'),
                        'country': gamer_info.get('countryCode', '?'),
                        'countryIP': gamer_info.get('countryCodeIP', '?'),
                        'coins': seat_data.get('coins', 0),
                        'winnings': seat_data.get('winnings', 0),
                        'agentID': seat_data.get('agentID', 0),
                        'seat': seat_data.get('seat', -1),
                        'sitout': seat_data.get('sitout', False),
                    }
                    players.append(player)

                # Sort by winnings
                players.sort(key=lambda p: p['winnings'])

                for p in players:
                    agent_tag = " \033[91m[BOT]\033[0m" if p['agentID'] != 0 else ""
                    vpn_tag = " \033[95m[VPN]\033[0m" if p['country'] != p['countryIP'] else ""
                    win_color = '\033[92m' if p['winnings'] > 0 else '\033[91m' if p['winnings'] < 0 else '\033[97m'

                    print(f"  Seat {p['seat']}: {p['name']:15s} | Stack: {p['coins']:6.2f} | {win_color}Win: {p['winnings']:+.2f}\033[0m | {p['country']}{agent_tag}{vpn_tag}")

                rooms_data[room_id] = {
                    'name': room_name,
                    'players': players,
                    'game_info': game_info,
                }

                # Log
                with open(LOG_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"MESA: {room_name} ({room_id})\n")
                    for p in players:
                        agent = " [BOT]" if p['agentID'] != 0 else ""
                        f.write(f"  {p['name']:15s} | Stack: {p['coins']:6.2f} | Win: {p['winnings']:+.2f} | {p['country']}{agent}\n")
                    f.write(f"{'='*60}\n\n")

            # moveturn/gamestart from spy room
            if route == 'onMsg' and isinstance(data, dict):
                event_inner = body.get('event', '')
                room_id = data.get('roomID', '')
                if event_inner in ('gamestart', 'moveturn') and room_id and current_spy_room and room_id != current_spy_room:
                    game_seat = data.get('game_seat', {})
                    if game_seat:
                        print(f"\033[96m  [{room_id}] Live update: {len(game_seat)} players\033[0m")

def on_msg(msg, data):
    if msg['type'] != 'send':
        return
    p = msg['payload']
    if p.get('t') == 'ready':
        print("\033[92mHOOK OK!\033[0m")
        return
    if p.get('t') == 'fatal':
        print(f"\033[91mFATAL: {p['e']}\033[0m")
        return
    if not data:
        return

    direction = p.get('d', 'RECV')
    if direction == 'RECV':
        process_recv(bytes(data))

# Clear log
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write(f"=== Suprema Table Spy - {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")

print(f"Connecting to SupremaPoker (PID {pid})...")
sess = frida.attach(pid)

# Frida script with ability to INJECT messages via SSL_write
js = r'''
var sslmod = Process.findModuleByName("libssl-1_1.dll");
var ssl_read = sslmod.findExportByName("SSL_read");
var ssl_write = sslmod.findExportByName("SSL_write");

// Store last SSL object for injection
var lastSSL = null;

Interceptor.attach(ssl_read, {
    onEnter: function(args) {
        this.ssl = args[0];
        this.buf = args[1];
    },
    onLeave: function(retval) {
        var n = retval.toInt32();
        if (n > 0) {
            lastSSL = this.ssl;
            send({t:"data", d:"RECV"}, this.buf.readByteArray(n));
        }
    }
});

Interceptor.attach(ssl_write, {
    onEnter: function(args) {
        var n = args[2].toInt32();
        if (n > 0) {
            lastSSL = args[0];
            send({t:"data", d:"SEND"}, args[1].readByteArray(n));
        }
    }
});

// RPC: inject raw bytes into SSL_write
var ssl_write_fn = new NativeFunction(ssl_write, 'int', ['pointer', 'pointer', 'int']);

rpc.exports = {
    inject: function(hexData) {
        if (!lastSSL) return "NO_SSL";
        var data = [];
        for (var i = 0; i < hexData.length; i += 2) {
            data.push(parseInt(hexData.substr(i, 2), 16));
        }
        var buf = Memory.alloc(data.length);
        buf.writeByteArray(data);
        var ret = ssl_write_fn(lastSSL, buf, data.length);
        return "OK:" + ret;
    }
};

send({t:"ready"});
'''

sc = sess.create_script(js)
sc.on('message', on_msg)
sc.load()

def inject_pomelo(route, body_dict):
    """Send a Pomelo message through the game's SSL connection."""
    pomelo_payload = build_pomelo_request(route, body_dict)
    ws_frame = build_ws_frame(pomelo_payload, masked=True)
    hex_data = ws_frame.hex()
    log(f"  [DEBUG] Pomelo hex: {pomelo_payload[:20].hex()}...")
    log(f"  [DEBUG] WS frame size: {len(ws_frame)}b")
    try:
        result = sc.exports_sync.inject(hex_data)
        log(f"  [DEBUG] SSL_write returned: {result}")
        return result
    except Exception as e:
        log(f"  [DEBUG] inject error: {e}")
        return f"ERROR: {e}"

log("SUPREMA TABLE SPY - MULTI-ROOM INTEL")
log(f"Log: {LOG_FILE}")

# Wait for SSL traffic so lastSSL gets populated
log("Aguardando trafico SSL pra capturar o socket...")
log("(Se nao aparecer nada, clique em algo no app Suprema)")
time.sleep(5)

# Step 1: Request room list for the Grand Union
log("[1] Requesting room list from GU...")
result = inject_pomelo("apiPlayer.playerHandler.joinGameRoom", {
    "clubID": "14625",
    "unionID": 113,
    "myClubID": 377039,
    "myUnionID": 106,
    "matchID": 0,
    "stakeRangeID": 1,
    "matchType": 1,
    "ver": 7288,
    "lan": "pt"
})
log(f"  Inject result: {result}")

# Wait for response
time.sleep(3)

# Step 2: Get match list to find specific room IDs
log("[2] Requesting match list...")
result = inject_pomelo("apiClubMatch.clubMatchHandler.matchGU", {
    "unionID": 113,
    "clubID": 14625,
    "matchID": 0,
    "myClubID": 377039,
    "myUnionID": 106,
    "stakeRangeID": 0,
    "ver": 7288,
    "lan": "pt"
})
print(f"  Inject result: {result}")

time.sleep(3)

# Step 3: Try entering specific rooms to get player data
# We'll try some known room patterns
print("\n\033[93m[3] Attempting to spy on rooms...\033[0m")

# Try entering rooms we know exist from matchesStatusPushNotify
# Room format: clubID_matchID
test_rooms = []

# Collect room IDs from responses
for key, val in responses.items():
    if key.startswith('roomList_'):
        rid = key.replace('roomList_', '')
        test_rooms.append(rid)

if not test_rooms:
    # Try common patterns based on what we've seen
    print("  No rooms found in roomList, trying known patterns...")
    # From the matchesStatusPushNotify, we saw matchIDs like 43103465, 43100186, etc.
    test_rooms = [
        "14625_43103465",
        "14625_43100186",
        "14625_43103022",
    ]

print(f"  Found {len(test_rooms)} rooms to spy on")

for room_id in test_rooms[:5]:  # Limit to 5 rooms
    print(f"\n\033[93m  Entering room {room_id}...\033[0m")
    current_spy_room = room_id

    result = inject_pomelo("room.roomHandler.clientMessage", {
        "f": "enter",
        "roomID": f"{room_id}#113@377039",
        "args": ""
    })
    print(f"    Inject: {result}")
    time.sleep(2)  # Wait for room data

    # Leave the room
    result = inject_pomelo("room.roomHandler.clientMessage", {
        "f": "leave",
        "roomID": room_id,
        "args": ""
    })
    time.sleep(1)

# Summary
print("\n\n\033[92m" + "=" * 60)
print("  RESUMO DE TODAS AS MESAS ESPIONADAS")
print("=" * 60 + "\033[0m\n")

for room_id, rdata in rooms_data.items():
    print(f"\033[97m{rdata['name']} ({room_id})\033[0m")
    players = rdata['players']
    if players:
        biggest_winner = max(players, key=lambda p: p['winnings'])
        biggest_loser = min(players, key=lambda p: p['winnings'])
        bots = [p for p in players if p['agentID'] != 0]

        print(f"  Maior ganhador: {biggest_winner['name']} ({biggest_winner['winnings']:+.2f})")
        print(f"  Maior perdedor: {biggest_loser['name']} ({biggest_loser['winnings']:+.2f})")
        if bots:
            print(f"  Bots detectados: {', '.join(b['name'] for b in bots)}")
        print()

print("\n\033[93mContinuando monitoramento... Ctrl+C para parar\033[0m")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

print("\nStopping...")
sc.unload()
sess.detach()
