"""Capture real Pomelo session reqId sequence, then inject VIP requests with valid IDs."""
import frida, sys, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import msgpack

JS = open('vip_inject.js', 'r').read()

sess = frida.attach(67560)
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
            print(f">>> CLIENT [{p['reqId']}] {p['route']} ({p['bodyLen']}b) body={p['bodyStr'][:150]}")
        elif t == 'SRV_MSG' and data:
            raw = bytes(data)
            ptype = raw[0]
            body = raw[4:]
            for offset in range(0, min(15, len(body))):
                try:
                    obj = msgpack.unpackb(body[offset:], raw=False, strict_map_key=False)
                    if isinstance(obj, dict):
                        event = str(obj.get('event', obj.get('route', '?')))
                        srv_msgs.append((ptype, event, obj))
                        if ptype == 2:
                            reqId = (raw[1]<<16)|(raw[2]<<8)|raw[3]
                            print(f"<<< RESP [{reqId}] {json.dumps(obj, default=str, ensure_ascii=False)[:500]}")
                        elif any(kw in event for kw in ['Vip','vip','Login','login','reward','Reward','luck','Luck','Title','title','Achievement','achievement','update','Update']):
                            print(f"<<< PUSH [{event}] {json.dumps(obj, default=str, ensure_ascii=False)[:500]}")
                        break
                except:
                    continue

sc.on('message', on_msg)
sc.load()
time.sleep(2)

print('\nMonitoring client requests for 45s...')
print('USE SUPREMAPOKER NORMALLY - click around, open menus, navigate!')
print('This captures the real reqId sequence.\n')

for i in range(45):
    time.sleep(1)
    if i % 15 == 14:
        try:
            state = sc.exports_sync.get_state()
            print(f"  [{i+1}s] lastReqId={state['lastReqId']} SSL={'yes' if state['hasSSL'] else 'no'} client_reqs={len(client_reqs)}")
        except:
            pass

# Now inject with the next reqId in sequence
try:
    state = sc.exports_sync.get_state()
    nextId = state['lastReqId'] + 1
    print(f"\n{'='*60}")
    print(f"INJECTION PHASE")
    print(f"Last client reqId: {state['lastReqId']}")
    print(f"Using reqId: {nextId} onwards")
    print(f"{'='*60}")

    tests = [
        ('apiPlayer.playerHandler.getVipLevelRemainDays', '{}'),
        ('apiPlayer.playerHandler.syncVipLevel', '{}'),
        ('apiPlayer.playerHandler.updateVipLevel', '{"level":3}'),
        ('apiPlayer.playerHandler.getAchievementRewards', '{}'),
        ('apiPlayer.playerHandler.luckDraw', '{}'),
        ('apiPlayer.playerHandler.receiveTheReward', '{}'),
    ]

    for route, body in tests:
        print(f"\n>>> INJECT [{nextId}] {route} body={body}")
        result = sc.exports_sync.inject_with_id(route, body, nextId)
        print(f"  {result}")
        nextId += 1
        time.sleep(4)

    print('\nWaiting 20s for all responses...')
    for i in range(20):
        time.sleep(1)

except Exception as e:
    print(f'Error: {e}')

print(f"\n{'='*60}")
print(f"RESULTS")
print(f"{'='*60}")
print(f"Total client reqs captured: {len(client_reqs)}")
print(f"Total server msgs: {len(srv_msgs)}")
print('\nAll server events (last 30):')
for ptype, event, obj in srv_msgs[-30:]:
    code = obj.get('code', '?')
    snippet = json.dumps(obj, default=str, ensure_ascii=False)[:200]
    print(f"  {'RESP' if ptype==2 else 'PUSH'} {event} code={code}")
    if any(kw in event for kw in ['Vip','vip','Login','reward','luck','Title','achieve','update']):
        print(f"    {snippet}")

sc.unload()
sess.detach()
