"""Inject VIP requests via lws_write (proper WebSocket path)."""
import frida, sys, time, json, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import msgpack

JS = open('C:/Users/PC/lws_inject.js', 'r').read()

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
        elif t == 'WSI_CAPTURED':
            print(f"WSI CAPTURED: {p['addr']}")
        elif t == 'LWS_WRITE':
            print(f"  lws_write #{p['n']} len={p['len']} wp={p['wp']} {p['preview']}")
        elif t == 'CLIENT_REQ':
            client_reqs.append(p)
            print(f">>> CLIENT [{p['reqId']}] {p['route']} ({p['bodyLen']}b)")
        elif t == 'SRV_MSG' and data:
            raw = bytes(data)
            ptype = raw[0]
            reqId = (raw[1]<<16)|(raw[2]<<8)|raw[3]
            body = raw[4:]
            for offset in range(0, min(15, len(body))):
                try:
                    obj = msgpack.unpackb(body[offset:], raw=False, strict_map_key=False)
                    if isinstance(obj, dict):
                        event = str(obj.get('event', obj.get('route', '?')))
                        srv_msgs.append((ptype, reqId, event, obj))
                        prefix = 'RESP' if ptype == 2 else 'PUSH'
                        s = json.dumps(obj, default=str, ensure_ascii=False)[:800]
                        if ptype == 2 or any(kw in event.lower() for kw in ['vip','login','reward','luck','title','achieve','update','level','draw']):
                            print(f"<<< {prefix} [{reqId}] {s}")
                        break
                except:
                    continue
    elif msg['type'] == 'error':
        print(f"FRIDA ERROR: {msg.get('description','?')}")

sc.on('message', on_msg)
sc.load()
time.sleep(2)

# Phase 1: Wait for WSI capture (heartbeats should give us one)
print('\n' + '='*60)
print('PHASE 1: Waiting for lws_write activity (heartbeats)...')
print('='*60 + '\n')

for i in range(15):
    time.sleep(1)
    if i % 5 == 4:
        try:
            state = sc.exports_sync.status()
            print(f"  [{i+1}s] has_wsi={state['wsi']} writes={state['writes']} lastReqId={state['rid']}")
        except Exception as e:
            print(f"  [{i+1}s] state error: {e}")

state = sc.exports_sync.status()
if not state['wsi']:
    print("FAILED: No WSI captured. lws_write not called.")
    print("Client may not be sending through lws_write.")
    sc.unload()
    sess.detach()
    sys.exit(1)

lastId = state['rid']
if lastId == 0:
    lastId = 100
    print(f"No client requests seen. Using starting reqId={lastId+1}")
else:
    print(f"Last client reqId: {lastId}")

nextId = lastId + 1

# Phase 2: Inject VIP requests via lws_write
print(f'\n{"="*60}')
print(f'PHASE 2: INJECTION via lws_write (starting reqId={nextId})')
print(f'{"="*60}\n')

empty_mp = msgpack.packb({})
empty_hex = ' '.join(f'{b:02x}' for b in empty_mp)

tests = [
    ('apiPlayer.playerHandler.getVipLevelRemainDays', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.syncVipLevel', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.getLoginInfo', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.getPrefsData', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.getTheColorTag', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.updateVipLevel', 'msgpack {level:3}',
     ' '.join(f'{b:02x}' for b in msgpack.packb({"level": 3}))),
    ('apiPlayer.playerHandler.luckDraw', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.receiveTheReward', 'msgpack {}', empty_hex),
]

for route, desc, body_hex in tests:
    print(f"\n>>> INJECT [{nextId}] {route} ({desc})")
    try:
        result = sc.exports_sync.injectPomelo(route, body_hex, nextId)
        print(f"  result: {result}")
    except Exception as e:
        print(f"  ERROR: {e}")
    nextId += 1
    time.sleep(4)

print(f'\nWaiting 15s for remaining responses...')
for i in range(15):
    time.sleep(1)

# Results
print(f'\n{"="*60}')
print(f'RESULTS')
print(f'{"="*60}')
print(f'Client reqs captured: {len(client_reqs)}')
print(f'Server msgs received: {len(srv_msgs)}')

for ptype, reqId, event, obj in srv_msgs:
    code = obj.get('code', '?')
    prefix = 'RESP' if ptype == 2 else 'PUSH'
    print(f"  {prefix} [{reqId}] event={event} code={code}")
    s = json.dumps(obj, default=str, ensure_ascii=False)[:600]
    print(f"    {s}")

resp_count = sum(1 for p, _, _, _ in srv_msgs if p == 2)
print(f"\nDirect responses (type=2): {resp_count}")
print(f"Push messages (type=4): {len(srv_msgs) - resp_count}")

sc.unload()
sess.detach()
print("\nDone.")
