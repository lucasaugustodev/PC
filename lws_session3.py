"""Inject VIP requests via lws_write with correct Pomelo Package format."""
import frida, sys, time, json, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import msgpack

JS = open('C:/Users/PC/lws_inject3.js', 'r').read()

r = subprocess.check_output('tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH', shell=True, text=True).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
if not pids:
    print("SupremaPoker not running!"); sys.exit(1)
pid = pids[0]
print(f"Attaching to PID {pid}")

sess = frida.attach(pid)
sc = sess.create_script(JS)
srv_msgs = []

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t')
        if t == 'ready':
            print('HOOK OK')
        elif t == 'REQ':
            print(f">>> REQ [{p['id']}] flag=0x{p['flag']:02x} {p['r']} ({p['bl']}b) {p['bh']}")
        elif t == 'HS':
            print(f"--- HANDSHAKE OUT")
        elif t == 'ACK':
            print(f"--- HANDSHAKE ACK (session ready)")
        elif t == 'CLOSE':
            print(f"!!! CLOSE {p['p']}")
        elif t == 'KICK':
            print(f"!!! KICK from server")
        elif t == 'SRV' and data:
            raw = bytes(data)
            if len(raw) < 1:
                return
            msgFlag = raw[0]
            msgType = (msgFlag >> 1) & 0x07

            # Decode msgId for response type
            pos = 1
            msgId = 0
            shift = 0
            if msgType == 0 or msgType == 1:  # request/notify have msgId
                while pos < len(raw):
                    b = raw[pos]
                    msgId = msgId | ((b & 0x7F) << shift)
                    pos += 1
                    if (b & 0x80) == 0:
                        break
                    shift += 7

            body = raw[pos:]

            # Try msgpack decode
            decoded = None
            for off in range(min(15, len(body))):
                try:
                    obj = msgpack.unpackb(body[off:], raw=False, strict_map_key=False)
                    if isinstance(obj, dict):
                        decoded = obj
                        break
                except:
                    continue

            if decoded:
                event = str(decoded.get('event', decoded.get('route', '?')))
                code = decoded.get('code', '?')
                srv_msgs.append((msgType, msgId, event, decoded))
                s = json.dumps(decoded, default=str, ensure_ascii=False)[:600]
                if msgType == 1:  # response
                    print(f"<<< RESP [{msgId}] code={code} {s}")
                elif any(kw in event.lower() for kw in ['vip','login','reward','luck','title','achieve','update','level','draw','color','prefs']):
                    print(f"<<< PUSH [{event}] {s}")
    elif msg['type'] == 'error':
        print(f"FRIDA ERROR: {msg.get('description','?')}")

sc.on('message', on_msg)
sc.load()
time.sleep(2)

# Phase 1: Wait for session and observe client traffic
print('\n' + '='*60)
print('PHASE 1: Waiting for session + capturing client requests...')
print('='*60 + '\n')

for i in range(15):
    time.sleep(1)
    if i % 5 == 4:
        try:
            state = sc.exports_sync.status()
            print(f"  [{i+1}s] wsi={state['wsi']} ready={state['ready']} rid={state['rid']} writes={state['wc']}")
        except Exception as e:
            print(f"  [{i+1}s] error: {e}")

state = sc.exports_sync.status()
if not state['wsi']:
    print("FAILED: No WSI"); sc.unload(); sess.detach(); sys.exit(1)

lastId = state['rid']
if lastId == 0:
    lastId = 200
    print(f"No client requests captured. Using starting msgId={lastId+1}")
else:
    print(f"Last client msgId: {lastId}")

nextId = lastId + 1

# Phase 2: Inject with proper Package+Message format
print(f'\n{"="*60}')
print(f'PHASE 2: INJECTION with Package type=4 wrapping')
print(f'Starting msgId={nextId}')
print(f'{"="*60}\n')

empty_mp = msgpack.packb({})
empty_hex = ' '.join(f'{b:02x}' for b in empty_mp)

tests = [
    ('apiPlayer.playerHandler.getLoginInfo', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.getPrefsData', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.getVipLevelRemainDays', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.syncVipLevel', 'msgpack {}', empty_hex),
    ('apiPlayer.playerHandler.updateVipLevel', 'msgpack {level:3}',
     ' '.join(f'{b:02x}' for b in msgpack.packb({"level": 3}))),
]

for route, desc, body_hex in tests:
    try:
        state = sc.exports_sync.status()
        if not state['ready']:
            print(f"  Waiting for session ready...")
            for w in range(20):
                time.sleep(1)
                state = sc.exports_sync.status()
                if state['ready']:
                    break
            if not state['ready']:
                print(f"  Session not ready, skipping {route}")
                continue
            nextId = max(nextId, state['rid'] + 1) if state['rid'] > 0 else nextId
    except:
        time.sleep(5)
        continue

    print(f"\n>>> INJECT [{nextId}] {route} ({desc})")
    try:
        result = sc.exports_sync.inject(route, body_hex, nextId)
        print(f"  {result}")
    except Exception as e:
        print(f"  ERROR: {e}")
    nextId += 1
    time.sleep(8)

print(f'\nWaiting 10s...')
for i in range(10):
    time.sleep(1)

# Results
print(f'\n{"="*60}')
print(f'RESULTS')
print(f'{"="*60}')
print(f'Server msgs: {len(srv_msgs)}')
resp_count = sum(1 for mt, _, _, _ in srv_msgs if mt == 1)
print(f'Responses: {resp_count}')
print(f'Pushes: {len(srv_msgs) - resp_count}')

for mt, mid, event, obj in srv_msgs:
    prefix = 'RESP' if mt == 1 else 'PUSH'
    code = obj.get('code', '?')
    s = json.dumps(obj, default=str, ensure_ascii=False)[:400]
    if mt == 1 or any(kw in event.lower() for kw in ['vip','login','reward','luck','title','achieve','update','level','draw','color','prefs']):
        print(f"  {prefix} [{mid}] code={code} {s}")

sc.unload()
sess.detach()
print("\nDone.")
