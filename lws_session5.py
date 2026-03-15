"""Inject by replacing heartbeat writes (thread-safe approach)."""
import frida, sys, time, json, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import msgpack

JS = open('C:/Users/PC/lws_inject6.js', 'r').read()

r = subprocess.check_output('tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH', shell=True, text=True).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
if not pids:
    print("SupremaPoker not running!"); sys.exit(1)
pid = pids[0]
print(f"Attaching to PID {pid}")

sess = frida.attach(pid)
sc = sess.create_script(JS)
srv_msgs = []
responses = []

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t')
        if t == 'ready':
            print('HOOK OK')
        elif t == 'REQ':
            print(f">>> REQ [{p['id']}] {p['r']} ({p['bl']}b) {p['bs'][:120]}")
        elif t == 'INJECTED':
            print(f"*** INJECTED #{p['n']} ({p['len']}b) via heartbeat replacement")
        elif t == 'HS':
            print(f"--- HANDSHAKE")
        elif t == 'ACK':
            print(f"--- HS ACK")
        elif t == 'CLOSE':
            print(f"!!! CLOSE")
        elif t == 'KICK':
            print(f"!!! KICK")
        elif t == 'ERR':
            print(f"JS ERROR: {p['m']}")
        elif t == 'SRV' and data:
            raw = bytes(data)
            if len(raw) < 1:
                return
            msgFlag = raw[0]
            msgType = (msgFlag >> 1) & 0x07

            pos = 1
            msgId = 0
            if msgType == 0 or msgType == 1:
                shift = 0
                while pos < len(raw):
                    b = raw[pos]
                    msgId = msgId | ((b & 0x7F) << shift)
                    pos += 1
                    if (b & 0x80) == 0:
                        break
                    shift += 7

            body = raw[pos:]
            decoded = None
            try:
                decoded = json.loads(body)
            except:
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
                type_names = {0:'REQ', 1:'RESP', 2:'NOTIFY', 3:'PUSH'}
                prefix = type_names.get(msgType, f'T{msgType}')
                if msgType == 1:
                    responses.append((msgId, decoded))
                    print(f"<<< RESP [{msgId}] code={code} {s}")
                elif any(kw in event.lower() for kw in ['vip','login','reward','luck','title','achieve','update','level','draw','color','prefs']):
                    print(f"<<< {prefix} [{event}] {s}")
    elif msg['type'] == 'error':
        print(f"FRIDA ERROR: {msg.get('description','?')}")

sc.on('message', on_msg)
sc.load()
time.sleep(3)

# Wait for heartbeats to establish session
print('\n' + '='*60)
print('PHASE 1: Monitoring for 15s...')
print('='*60 + '\n')

for i in range(15):
    time.sleep(1)
    if i % 5 == 4:
        try:
            state = sc.exports_sync.status()
            print(f"  [{i+1}s] ready={state['ready']} rid={state['rid']} writes={state['wc']}")
        except Exception as e:
            print(f"  [{i+1}s] error: {e}")

state = sc.exports_sync.status()
lastId = state['rid']
if lastId == 0:
    lastId = 200
nextId = lastId + 1

# Enqueue requests one at a time and wait for heartbeat to deliver them
print(f'\n{"="*60}')
print(f'PHASE 2: Enqueue + heartbeat replacement')
print(f'Starting msgId={nextId}')
print(f'{"="*60}\n')

std_body = json.dumps({"ver": 7288, "lan": "pt", "verPackage": "5"})

tests = [
    ('apiPlayer.playerHandler.getLoginInfo', std_body),
    ('apiPlayer.playerHandler.getPrefsData', std_body),
    ('apiPlayer.playerHandler.getTheColorTag', std_body),
    ('apiPlayer.playerHandler.getVipLevelRemainDays', std_body),
    ('apiPlayer.playerHandler.syncVipLevel', std_body),
    ('apiPlayer.playerHandler.updateVipLevel',
     json.dumps({"level": 3, "ver": 7288, "lan": "pt", "verPackage": "5"})),
]

for route, body_json in tests:
    # Check state first
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
            # After reconnection, update msgId
            if state['rid'] > 0:
                nextId = state['rid'] + 1
    except:
        time.sleep(3)
        continue

    print(f"\n>>> ENQUEUE [{nextId}] {route}")
    try:
        result = sc.exports_sync.enqueue(route, body_json, nextId)
        print(f"    {result}")
    except Exception as e:
        print(f"    ERROR: {e}")
    nextId += 1

    # Wait for heartbeat to deliver it (heartbeats every ~2s)
    time.sleep(5)

    # Check if it was delivered
    try:
        state = sc.exports_sync.status()
        print(f"    status: done={state['done']} queue={state['queue']} rid={state['rid']}")
    except:
        pass

# Wait for responses
print(f'\nWaiting 15s for responses...')
for i in range(15):
    time.sleep(1)

# Results
print(f'\n{"="*60}')
print(f'RESULTS')
print(f'{"="*60}')
print(f'Server msgs: {len(srv_msgs)}')
print(f'Direct responses: {len(responses)}')

if responses:
    print('\nRESPONSES:')
    for mid, obj in responses:
        s = json.dumps(obj, default=str, ensure_ascii=False)[:600]
        print(f"  [{mid}] {s}")
else:
    print('\nNo direct responses received.')

# Show all interesting pushes
interesting = [(mt, mid, ev, obj) for mt, mid, ev, obj in srv_msgs
               if any(kw in ev.lower() for kw in ['vip','login','reward','luck','title','achieve','update','level','draw','color','prefs'])]
if interesting:
    print(f'\nInteresting pushes ({len(interesting)}):')
    for mt, mid, ev, obj in interesting:
        code = obj.get('code', '?')
        s = json.dumps(obj, default=str, ensure_ascii=False)[:400]
        print(f"  [{mid}] {ev} code={code} {s}")

try:
    sc.unload()
    sess.detach()
except:
    pass
print("\nDone.")
