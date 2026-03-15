"""Capture real Pomelo session reqId, then inject VIP requests with msgpack bodies."""
import frida, sys, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import msgpack

JS = open('vip_inject.js', 'r').read()

# Check if process is running
import subprocess
r = subprocess.check_output('tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH', shell=True, text=True).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
if not pids:
    print("SupremaPoker not running!"); sys.exit(1)
pid = pids[0]
print(f"Attaching to PID {pid}")

sess = frida.attach(pid)
sc = sess.create_script(JS)
srv_msgs = []
client_reqs = []

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t')
        if t == 'ready':
            print('HOOK OK')
        elif t == 'CLIENT_REQ':
            client_reqs.append(p)
            print(f">>> CLIENT [{p['reqId']}] {p['route']} ({p['bodyLen']}b) {p['bodyStr'][:150]}")
        elif t == 'SRV_MSG' and data:
            raw = bytes(data)
            ptype = raw[0]
            body = raw[4:]

            # Try decode as msgpack at various offsets
            for offset in range(0, min(15, len(body))):
                try:
                    obj = msgpack.unpackb(body[offset:], raw=False, strict_map_key=False)
                    if isinstance(obj, dict):
                        event = str(obj.get('event', obj.get('route', '?')))
                        srv_msgs.append((ptype, event, obj))
                        if ptype == 2:
                            reqId = (raw[1]<<16)|(raw[2]<<8)|raw[3]
                            print(f"<<< RESP [{reqId}] {json.dumps(obj, default=str, ensure_ascii=False)[:800]}")
                        elif any(kw in event.lower() for kw in ['vip','login','reward','luck','title','achieve','update','level','draw']):
                            print(f"<<< PUSH [{event}] {json.dumps(obj, default=str, ensure_ascii=False)[:800]}")
                        break
                except:
                    continue

sc.on('message', on_msg)
sc.load()
time.sleep(2)

# Phase 1: Monitor for real client traffic
print('\n' + '='*60)
print('PHASE 1: Monitoring real client traffic for 30s')
print('Navigate SupremaPoker menus to generate requests!')
print('='*60 + '\n')

for i in range(30):
    time.sleep(1)
    if i % 10 == 9:
        try:
            state = sc.exports_sync.get_state()
            print(f"  [{i+1}s] lastReqId={state['lastReqId']} reqs={len(client_reqs)}")
        except:
            pass

state = sc.exports_sync.get_state()
lastId = state['lastReqId']

# If no client requests, we'll try starting from a reasonable ID
if lastId == 0:
    # Try to find reqId from server push messages
    # Use a high starting ID to avoid conflicts
    lastId = 100
    print(f"\nNo client requests seen. Using starting reqId={lastId+1}")
else:
    print(f"\nLast client reqId: {lastId}")

nextId = lastId + 1

# Phase 2: Inject with msgpack bodies
print(f'\n{"="*60}')
print(f'PHASE 2: INJECTION (starting reqId={nextId})')
print(f'{"="*60}\n')

# msgpack encode empty object: {} = 0x80
empty_msgpack = msgpack.packb({})
empty_hex = ' '.join(f'{b:02x}' for b in empty_msgpack)

# Various body formats to test
tests = [
    # Route, body description, hex body
    ('apiPlayer.playerHandler.getVipLevelRemainDays', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.getVipLevelRemainDays', 'empty body', ''),
    ('apiPlayer.playerHandler.syncVipLevel', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.updateVipLevel', 'msgpack {level:3}',
     ' '.join(f'{b:02x}' for b in msgpack.packb({"level": 3}))),
    ('apiPlayer.playerHandler.luckDraw', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.receiveTheReward', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.getAchievementRewards', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.setTitle', 'msgpack {titleId:1}',
     ' '.join(f'{b:02x}' for b in msgpack.packb({"titleId": 1}))),
]

for route, desc, body_hex in tests:
    print(f"\n>>> INJECT [{nextId}] {route} ({desc})")
    try:
        result = sc.exports_sync.inject_raw(route, body_hex, nextId)
        print(f"  {result}")
    except Exception as e:
        print(f"  ERROR: {e}")
    nextId += 1
    time.sleep(3)

print(f'\nWaiting 20s for responses...')
for i in range(20):
    time.sleep(1)

# Results
print(f'\n{"="*60}')
print(f'RESULTS')
print(f'{"="*60}')
print(f'Client reqs captured: {len(client_reqs)}')
print(f'Server msgs received: {len(srv_msgs)}')

print('\nAll server events:')
for ptype, event, obj in srv_msgs:
    code = obj.get('code', '?')
    is_interesting = any(kw in event.lower() for kw in ['vip','login','reward','luck','title','achieve','update','level','draw'])
    prefix = 'RESP' if ptype == 2 else 'PUSH'
    print(f"  {prefix} {event} code={code}")
    if is_interesting:
        print(f"    FULL: {json.dumps(obj, default=str, ensure_ascii=False)[:600]}")

# Check if any direct responses (type=2) were received
resp_count = sum(1 for p, _, _ in srv_msgs if p == 2)
print(f"\nDirect responses (type=2): {resp_count}")
print(f"Push messages (type=4): {len(srv_msgs) - resp_count}")

sc.unload()
sess.detach()
print("\nDone.")
