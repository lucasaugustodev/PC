"""Suprema Replay - Captures real joinGameRoom, then replays it."""
import frida, json, time, sys, os, subprocess, threading, re
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

LOG = os.path.expanduser('~/suprema_replay.log')
lock = threading.Lock()
send_buf = b''
recv_buf = b''

# Captured data
captured_join_pomelo = None  # Raw Pomelo bytes of joinGameRoom
captured_enter_pomelo = None  # Raw Pomelo bytes of room enter
got_response = threading.Event()
last_response_body = None
last_reqid = 0  # Track latest reqId from client

def log(msg):
    print(msg)
    with open(LOG, 'a', encoding='utf-8') as f:
        clean = re.sub(r'\033\[[0-9;]*m', '', msg)
        f.write(clean + '\n')

def parse_ws_frames(buf):
    frames = []
    pos = 0
    while pos < len(buf):
        if pos + 1 >= len(buf): break
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

def build_ws_frame(payload):
    """Wrap in masked WebSocket binary frame."""
    import random
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
    mask = bytes([random.randint(0, 255) for _ in range(4)])
    frame.extend(mask)
    masked_payload = bytearray(payload)
    for i in range(len(masked_payload)):
        masked_payload[i] ^= mask[i % 4]
    frame.extend(masked_payload)
    return bytes(frame)

def process_send(raw):
    """Capture client SEND to find joinGameRoom and enter messages."""
    global send_buf, captured_join_pomelo, captured_enter_pomelo
    with lock:
        send_buf += raw
        frames, send_buf = parse_ws_frames(send_buf)
        for frame in frames:
            if len(frame) < 8 or frame[0] != 4:
                continue
            # Parse: [type=4] [plen 3B] [reqId 2B] [flags] [routeLen] [route] [body]
            rlen = frame[7]
            if 8 + rlen > len(frame):
                continue
            try:
                route = frame[8:8+rlen].decode('utf-8', errors='replace')
            except:
                continue

            # Track reqId
            reqid = (frame[4] << 8) | frame[5]
            if reqid > last_reqid:
                last_reqid = reqid

            if 'joinGameRoom' in route and not captured_join_pomelo:
                captured_join_pomelo = frame
                body_hex = frame[8+rlen:].hex()
                log(f"  [CAPTURED] joinGameRoom ({len(frame)}b)")
                log(f"    Full hex: {frame.hex()}")
                log(f"    Route: {route}")
                log(f"    Body hex: {body_hex}")
                try:
                    body_str = frame[8+rlen:].decode('utf-8', errors='replace')
                    log(f"    Body text: {body_str}")
                except:
                    pass

            if 'clientMessage' in route:
                body_start = 8 + rlen
                try:
                    body_str = frame[body_start:].decode('utf-8', errors='replace')
                    if '"enter"' in body_str or '"f":"enter"' in body_str:
                        captured_enter_pomelo = frame
                        log(f"  [CAPTURED] enter ({len(frame)}b)")
                        log(f"    Full hex: {frame.hex()}")
                        log(f"    Body: {body_str}")
                except:
                    pass

def process_recv(raw):
    """Process server responses."""
    global recv_buf, last_response_body
    with lock:
        recv_buf += raw
        frames, recv_buf = parse_ws_frames(recv_buf)
        for frame in frames:
            if len(frame) < 5:
                continue
            ptype = frame[0]

            # Type 4: Server PUSH
            if ptype == 4:
                plen = (frame[1] << 16) | (frame[2] << 8) | frame[3]
                pbody = frame[4:4 + plen]
                if len(pbody) < 2:
                    continue
                rlen = pbody[1]
                if 2 + rlen > len(pbody):
                    continue
                try:
                    route = pbody[2:2+rlen].decode('utf-8', errors='replace')
                except:
                    continue
                body = None
                if 2 + rlen < len(pbody):
                    try:
                        body = msgpack.unpackb(pbody[2+rlen:], raw=False)
                    except:
                        pass

                if not isinstance(body, dict):
                    continue

                event = body.get('event', '')

                # Skip noise
                if event in ('countdown', 'matchesStatusPushNotify',
                            'apiClub.clubHandler.jackpot', 'clientPing'):
                    continue

                log(f"  [RECV] {event}")

                if event == 'joinGameRoom' or 'joinGameRoom' in event:
                    api = body.get('apiData', {})
                    room_list = api.get('roomList', {})
                    log(f"    GOT ROOMLIST! {len(room_list)} rooms")
                    for rid, rinfo in room_list.items():
                        log(f"      Room {rid}")
                    last_response_body = body
                    got_response.set()

                if event == 'initinfo':
                    data = body.get('data', {})
                    room_info = data.get('room', {}) if isinstance(data, dict) else {}
                    game_seat = data.get('game_seat', {}) if isinstance(data, dict) else {}
                    gamers = data.get('gamer', {}) if isinstance(data, dict) else {}

                    log(f"    INITINFO! Room: {room_info.get('name', '?')}")
                    for uid, seat in game_seat.items():
                        if isinstance(seat, dict):
                            ginfo = gamers.get(uid, gamers.get(str(uid), {}))
                            name = ginfo.get('displayID', uid) if isinstance(ginfo, dict) else uid
                            coins = seat.get('coins', 0)
                            win = seat.get('winnings', 0)
                            agent = seat.get('agentID', 0)
                            bot = " [BOT]" if agent else ""
                            log(f"      {name}: stack={coins} win={win:+.2f}{bot}")
                    last_response_body = body
                    got_response.set()

def on_msg(msg, data):
    if msg['type'] != 'send':
        return
    p = msg['payload']
    if p.get('t') == 'ready':
        log("HOOK OK!")
        return
    if p.get('t') == 'fatal':
        log(f"FATAL: {p['e']}")
        return
    if not data:
        return
    d = p.get('d', 'RECV')
    if d == 'SEND':
        process_send(bytes(data))
    elif d == 'RECV':
        process_recv(bytes(data))

# Clear log
with open(LOG, 'w', encoding='utf-8') as f:
    f.write(f"=== Suprema Replay - {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")

log(f"Connecting to SupremaPoker (PID {pid})...")
sess = frida.attach(pid)

js = r'''
var sslmod = Process.findModuleByName("libssl-1_1.dll");
var ssl_read = sslmod.findExportByName("SSL_read");
var ssl_write = sslmod.findExportByName("SSL_write");

// Track ALL SSL connections and identify the game one
var sslConnections = {};  // ptr -> {isGame: bool, lastActivity: timestamp}
var gameSSL = null;

function checkIfGameData(buf, n) {
    // Game WebSocket data starts with 0x82 (binary frame) or has Pomelo type-4 markers
    if (n < 5) return false;
    var b0 = buf.readU8();
    // WebSocket binary frame
    if (b0 === 0x82) return true;
    // Pomelo type 4 (seen in some fragmented reads)
    if (b0 === 4) return true;
    return false;
}

Interceptor.attach(ssl_read, {
    onEnter: function(args) { this.ssl = args[0]; this.buf = args[1]; },
    onLeave: function(retval) {
        var n = retval.toInt32();
        if (n > 0) {
            var ptr = this.ssl.toString();
            if (checkIfGameData(this.buf, n)) {
                gameSSL = this.ssl;
                sslConnections[ptr] = {isGame: true};
            }
            // Only send game data
            if (sslConnections[ptr] && sslConnections[ptr].isGame) {
                send({t:"data", d:"RECV"}, this.buf.readByteArray(n));
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
            if (checkIfGameData(args[1], n)) {
                gameSSL = this.ssl;
                sslConnections[ptr] = {isGame: true};
            }
            if (sslConnections[ptr] && sslConnections[ptr].isGame) {
                send({t:"data", d:"SEND"}, args[1].readByteArray(n));
            }
        }
    }
});

var ssl_write_fn = new NativeFunction(ssl_write, 'int', ['pointer', 'pointer', 'int']);
rpc.exports = {
    inject: function(hexData) {
        if (!gameSSL) return "NO_GAME_SSL";
        var data = [];
        for (var i = 0; i < hexData.length; i += 2)
            data.push(parseInt(hexData.substr(i, 2), 16));
        var buf = Memory.alloc(data.length);
        buf.writeByteArray(data);
        var ret = ssl_write_fn(gameSSL, buf, data.length);
        return "GAME_OK:" + ret;
    }
};
send({t:"ready"});
'''

sc = sess.create_script(js)
sc.on('message', on_msg)
sc.load()

def inject_raw_pomelo(pomelo_bytes):
    """Inject raw Pomelo bytes wrapped in a new WS frame."""
    ws = build_ws_frame(pomelo_bytes)
    result = sc.exports_sync.inject(ws.hex())
    return result

def replay_with_new_reqid(original_pomelo, new_reqid):
    """Replay captured Pomelo message with a different reqId."""
    modified = bytearray(original_pomelo)
    modified[4] = (new_reqid >> 8) & 0xFF
    modified[5] = new_reqid & 0xFF
    return bytes(modified)

log("")
log("=" * 50)
log("  SUPREMA REPLAY")
log("  Sai da mesa e entra de novo!")
log("  Ou clica em algo no app.")
log("=" * 50)
log("")
log("Esperando capturar joinGameRoom...")

# Wait until we capture a real joinGameRoom
for i in range(120):
    time.sleep(1)
    if captured_join_pomelo:
        log(f"Capturado em {i+1}s!")
        break
    if i % 15 == 14:
        log(f"  ... {i+1}s esperando (sai e entra numa mesa!)")

if not captured_join_pomelo:
    log("Timeout! Nao capturou joinGameRoom.")
    log("Continuando monitoramento...")
else:
    # Wait a bit more to capture the latest reqId
    log(f"  Ultimo reqId capturado: {last_reqid}")
    log("  Esperando 3s pra pegar mais reqIds...")
    time.sleep(3)
    log(f"  Ultimo reqId agora: {last_reqid}")

    # Build a simple test request: getPrefsData (always works)
    next_reqid = last_reqid + 1
    flags = captured_join_pomelo[6]  # Copy flags from real message
    log(f"\n[TEST 1] Injetando getPrefsData com reqId={next_reqid} flags={flags}")
    route = b'apiPlayer.playerHandler.getPrefsData'
    body = b'{"ver":7288,"lan":"pt","verPackage":"5"}'
    inner = bytes([(next_reqid >> 8) & 0xFF, next_reqid & 0xFF, flags, len(route)]) + route + body
    plen = len(inner)
    pomelo = bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner
    log(f"  Pomelo hex: {pomelo.hex()}")
    result = inject_raw_pomelo(pomelo)
    log(f"  SSL_write: {result}")

    log("  Esperando resposta...")
    if got_response.wait(timeout=5):
        log("  RESPOSTA RECEBIDA! Inject funciona!")
    else:
        log("  Sem resposta :(")

    # Test 2: replay joinGameRoom with sequential reqId
    got_response.clear()
    next_reqid += 1
    log(f"\n[TEST 2] Replay joinGameRoom com reqId={next_reqid}")
    replayed = replay_with_new_reqid(captured_join_pomelo, next_reqid)
    result = inject_raw_pomelo(replayed)
    log(f"  SSL_write: {result}")

    if got_response.wait(timeout=5):
        log("  RESPOSTA RECEBIDA!")
    else:
        log("  Sem resposta :(")

    # Test 3: try entering a different room
    if captured_enter_pomelo:
        got_response.clear()
        next_reqid += 1
        log(f"\n[TEST 3] Replay enter com reqId={next_reqid}")
        replayed_enter = replay_with_new_reqid(captured_enter_pomelo, next_reqid)
        result = inject_raw_pomelo(replayed_enter)
        log(f"  SSL_write: {result}")
        if got_response.wait(timeout=5):
            log("  RESPOSTA RECEBIDA!")

log("\nMonitoramento continuo... Ctrl+C para sair")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

log("Stopping...")
sc.unload()
sess.detach()
