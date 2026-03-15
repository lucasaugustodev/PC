"""Pull table/lobby data from clubs without entering tables."""
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
                results.append((msgId, event, code, decoded))
                s = json.dumps(decoded, default=str, ensure_ascii=False)[:800]
                if 'jackpot' not in event and 'matchesStatus' not in event:
                    print(f"<<< [{msgId}] [{event}] code={code}")
                    print(f"    {s}")
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

nextId = 400

std = {"ver": 7288, "lan": "pt", "verPackage": "5"}

# First get login info to see clubs
tests = [
    # Get player info (shows joinClubCount=2)
    ("apiPlayer.playerHandler.getLoginInfo", std),

    # Get clubs addon info (lists clubs player is in)
    ("apiPlayer.playerHandler.getClubsAddonInfo", std),

    # Get lobby lists for known club 14625
    ("apiClub.clubHandler.getLobbyLists", {**std, "clubID": 14625}),

    # Get lobby coins for club 14625
    ("apiClub.clubHandler.getLobbyCoins", {**std, "clubID": 14625}),

    # Get members of club
    ("apiClub.clubHandler.members", {**std, "clubID": 14625}),

    # Get trade history
    ("apiClub.clubHandler.requestTradeHistory", {**std, "clubID": 14625}),
    ("apiClub.clubHandler.requestTradeHistoryPublic", {**std, "clubID": 14625}),

    # Match data - try getting active matches/tables
    ("apiClubMatch.clubMatchHandler.match", {**std, "clubID": 14625}),
    ("apiClubMatch.clubMatchHandler.matchSlim", {**std, "clubID": 14625}),
    ("apiClubMatch.clubMatchHandler.matchGU", {**std, "clubID": 14625}),

    # Check if player is at another table
    ("apiClub.clubHandler.getPlayerOtherTableID", {**std, "clubID": 14625}),

    # Ticket player
    ("apiClub.clubHandler.getTicketPlayer", {**std, "clubID": 14625}),
]

for route, body in tests:
    body_json = json.dumps(body)
    print(f"\n>>> [{nextId}] {route}")
    try:
        result = sc.exports_sync.inject(route, body_json, nextId)
        print(f"    {result}")
    except Exception as e:
        print(f"    ERROR: {e}")
    nextId += 1
    time.sleep(3)

# Now check if getLoginInfo returned other club IDs
club_ids = set()
club_ids.add(14625)  # known club
for mid, event, code, obj in results:
    if 'clubList' in json.dumps(obj):
        # Extract club IDs from response
        api = obj.get('apiData', {})
        for key in api:
            if isinstance(api[key], list):
                for item in api[key]:
                    if isinstance(item, dict) and 'clubID' in item:
                        cid = item['clubID']
                        if cid not in club_ids:
                            club_ids.add(cid)
                            print(f"\n=== Found club {cid}, querying tables ===")
                            for extra_route in [
                                "apiClub.clubHandler.getLobbyLists",
                                "apiClubMatch.clubMatchHandler.matchSlim",
                                "apiClub.clubHandler.members",
                            ]:
                                body_json = json.dumps({**std, "clubID": cid})
                                print(f"\n>>> [{nextId}] {extra_route} clubID={cid}")
                                try:
                                    result = sc.exports_sync.inject(extra_route, body_json, nextId)
                                    print(f"    {result}")
                                except Exception as e:
                                    print(f"    ERROR: {e}")
                                nextId += 1
                                time.sleep(3)

print(f'\nWaiting 10s for remaining responses...')
for i in range(10): time.sleep(1)

print(f'\n{"="*60}')
print(f'ALL RESULTS ({len(results)} messages)')
print(f'{"="*60}')
for mid, event, code, obj in results:
    if 'jackpot' in event or 'matchesStatus' in event:
        continue
    s = json.dumps(obj, default=str, ensure_ascii=False)[:1000]
    print(f"\n  [{mid}] [{event}] code={code}")
    print(f"    {s}")

try: sc.unload(); sess.detach()
except: pass
print("\nDone.")
