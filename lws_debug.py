"""Debug: trace exact sequence of events around injection."""
import frida, sys, time, json, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JS = open('C:/Users/PC/lws_debug.js', 'r').read()

r = subprocess.check_output('tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH', shell=True, text=True).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
if not pids:
    print("NOT RUNNING"); sys.exit(1)
pid = pids[0]
print(f"PID {pid}")

sess = frida.attach(pid)
sc = sess.create_script(JS)
events = []

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        events.append(p)
        t = p.get('t')
        s = p.get('s', '')
        if t == 'ready':
            print('HOOK OK')
        elif t in ('LWS_HB',):
            pass  # quiet heartbeats
        elif t == 'SSL_W':
            if p['len'] > 20:  # skip small ssl writes (TLS overhead)
                print(f"  [{s}] SSL_WRITE len={p['len']} {p['p'][:60]}")
        elif t == 'SSL_R_CLOSE':
            print(f"  [{s}] *** SSL_READ CLOSE code={p['code']} {p['p']}")
        elif t == 'SSL_R_WS':
            if p['pl'] > 10:  # skip small
                print(f"  [{s}] SSL_READ WS pl={p['pl']} {p['p'][:60]}")
        elif t == 'SSL_R':
            print(f"  [{s}] SSL_READ raw len={p['len']} {p['p'][:60]}")
        elif t in ('LWS_CLOSE',):
            print(f"  [{s}] LWS_CLOSE {p['p']}")
        elif t == 'LWS_REQ':
            print(f"  [{s}] LWS_REQ [{p['id']}] {p['r']}")
        elif t == 'LWS_HS':
            print(f"  [{s}] LWS_HANDSHAKE")
        elif t == 'LWS_ACK':
            print(f"  [{s}] LWS_HS_ACK")
        elif t == 'INJECT_START':
            print(f"  [{s}] >>> INJECT START msgId={p['mid']} len={p['len']}")
        elif t == 'INJECT_DONE':
            print(f"  [{s}] >>> INJECT DONE ret={p['ret']}")
    elif msg['type'] == 'error':
        print(f"ERROR: {msg.get('description','?')}")

sc.on('message', on_msg)
sc.load()
time.sleep(3)

state = sc.exports_sync.status()
print(f"Status: {state}")

if not state['ready']:
    print("Waiting for ready...")
    for i in range(20):
        time.sleep(1)
        state = sc.exports_sync.status()
        if state['ready']:
            break
    print(f"Status: {state}")

# Arm ONE injection
std_body = json.dumps({"ver": 7288, "lan": "pt", "verPackage": "5"})
nextId = state['rid'] + 1 if state['rid'] > 0 else 1

print(f"\n{'='*60}")
print(f"ARMING injection: getLoginInfo msgId={nextId}")
print(f"{'='*60}")
result = sc.exports_sync.arm('apiPlayer.playerHandler.getLoginInfo', std_body, nextId)
print(f"  {result}")

print(f"\nWatching event sequence for 20s...\n")
for i in range(20):
    time.sleep(1)
    if not sc.exports_sync.status()['pending']:
        print(f"  (injection delivered at ~{i+1}s)")
        # Continue watching for 10 more seconds
        for j in range(10):
            time.sleep(1)
        break

print(f"\n{'='*60}")
print(f"EVENT SEQUENCE (last 50):")
print(f"{'='*60}")
for e in events[-50:]:
    t = e.get('t')
    s = e.get('s', '')
    if t == 'LWS_HB':
        print(f"  [{s}] HEARTBEAT")
    elif t == 'SSL_W':
        print(f"  [{s}] SSL_WRITE len={e['len']}")
    elif t == 'SSL_R_CLOSE':
        print(f"  [{s}] *** SSL_READ CLOSE code={e['code']}")
    elif t == 'SSL_R_WS':
        print(f"  [{s}] SSL_READ WS pl={e['pl']}")
    elif t == 'SSL_R':
        print(f"  [{s}] SSL_READ len={e['len']}")
    elif t == 'LWS_CLOSE':
        print(f"  [{s}] LWS_WRITE_CLOSE {e['p']}")
    elif t == 'LWS_REQ':
        print(f"  [{s}] CLIENT_REQ [{e['id']}] {e['r']}")
    elif t == 'LWS_HS':
        print(f"  [{s}] HANDSHAKE_OUT")
    elif t == 'LWS_ACK':
        print(f"  [{s}] HANDSHAKE_ACK")
    elif t == 'INJECT_START':
        print(f"  [{s}] >>> INJECT_START msgId={e['mid']}")
    elif t == 'INJECT_DONE':
        print(f"  [{s}] >>> INJECT_DONE ret={e['ret']}")

try: sc.unload(); sess.detach()
except: pass
print("\nDone.")
