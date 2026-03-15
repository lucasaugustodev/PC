"""Capture the full login/reconnect sequence to understand request format."""
import frida, sys, time, json, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import msgpack

JS = r'''
var sslmod = Process.findModuleByName('libssl-1_1.dll');
var ssl_write = sslmod.findExportByName('SSL_write');
var ssl_read = sslmod.findExportByName('SSL_read');

Interceptor.attach(ssl_write, {
    onEnter: function(args) {
        var n = args[2].toInt32();
        if (n > 10 && n < 50000) {
            try {
                var raw = args[1].readByteArray(n);
                send({t:'W', len:n}, raw);
            } catch(e) {}
        }
    }
});

Interceptor.attach(ssl_read, {
    onEnter: function(a) { this.buf = a[1]; },
    onLeave: function(r) {
        var n = r.toInt32();
        if (n > 10 && n < 50000) {
            try {
                var raw = this.buf.readByteArray(n);
                send({t:'R', len:n}, raw);
            } catch(e) {}
        }
    }
});

send({t:'ready'});
'''

# Find PID
r = subprocess.check_output('tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH', shell=True, text=True).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
if not pids:
    print("SupremaPoker not running!")
    sys.exit(1)
pid = pids[0]
print(f"PID {pid}")

sess = frida.attach(pid)
sc = sess.create_script(JS)

client_requests = []
server_responses = []

def parse_ws(raw):
    if raw[0] not in (0x82, 0x81):
        return None
    masked = (raw[1] & 0x80) != 0
    pl = raw[1] & 0x7F
    hl = 2
    if pl == 126:
        pl = (raw[2]<<8)|raw[3]
        hl = 4
    elif pl == 127:
        hl = 10
        pl = int.from_bytes(raw[2:10], 'big')
    if masked:
        hl += 4
    if hl + pl > len(raw):
        return None
    if masked:
        mk = raw[hl-4:hl]
        payload = bytearray(raw[hl:hl+pl])
        for i in range(len(payload)):
            payload[i] ^= mk[i%4]
        payload = bytes(payload)
    else:
        payload = raw[hl:hl+pl]
    return payload

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        if p['t'] == 'ready':
            print('HOOK OK')
            return
        if not data:
            return
        raw = bytes(data)
        direction = 'SEND' if p['t'] == 'W' else 'RECV'
        payload = parse_ws(raw)
        if not payload or len(payload) < 4:
            return

        ptype = payload[0]
        f123 = (payload[1]<<16)|(payload[2]<<8)|payload[3]
        body = payload[4:]
        pnames = {0:'REQ', 1:'HANDSHAKE', 2:'RESP', 3:'HB', 4:'PUSH', 5:'KICK'}
        pname = pnames.get(ptype, f'T{ptype}')

        if ptype == 3:
            return  # skip heartbeats

        if ptype == 0:  # CLIENT REQUEST
            route = '?'
            body_data = body
            if len(payload) > 4:
                rlen = payload[4]
                if 5 + rlen <= len(payload):
                    route = payload[5:5+rlen].decode('ascii', errors='replace')
                    body_data = payload[5+rlen:]

            # Decode body
            decoded = None
            for attempt in [
                lambda: msgpack.unpackb(body_data, raw=False),
                lambda: json.loads(body_data),
            ]:
                try:
                    decoded = attempt()
                    break
                except:
                    pass

            entry = {
                'reqId': f123,
                'route': route,
                'bodyLen': len(body_data),
                'bodyHex': body_data[:50].hex(),
                'decoded': decoded
            }
            client_requests.append(entry)
            dec_str = json.dumps(decoded, default=str)[:200] if decoded else body_data[:50].hex()
            print(f">>> [{f123}] {route} ({len(body_data)}b) {dec_str}")

        elif ptype == 1:  # HANDSHAKE
            try:
                hs = json.loads(body.decode('utf-8'))
                print(f"{direction} HANDSHAKE: {json.dumps(hs)}")
            except:
                print(f"{direction} HANDSHAKE ({len(body)}b)")

        elif ptype == 2:  # RESPONSE
            decoded = None
            for off in range(min(10, len(body))):
                try:
                    decoded = msgpack.unpackb(body[off:], raw=False, strict_map_key=False)
                    if isinstance(decoded, dict):
                        break
                except:
                    decoded = None
            dec_str = json.dumps(decoded, default=str)[:300] if decoded else body[:50].hex()
            print(f"<<< RESP [{f123}] {dec_str}")
            server_responses.append({'reqId': f123, 'decoded': decoded})

        elif ptype == 4:  # PUSH
            decoded = None
            for off in range(min(10, len(body))):
                try:
                    decoded = msgpack.unpackb(body[off:], raw=False, strict_map_key=False)
                    if isinstance(decoded, dict):
                        break
                except:
                    decoded = None
            if decoded:
                event = decoded.get('event', '?')
                if 'jackpot' not in str(event):
                    dec_str = json.dumps(decoded, default=str)[:400]
                    print(f"<<< PUSH [{event}] {dec_str}")

sc.on('message', on_msg)
sc.load()

print('\nCapturing for 60s... CLICK AROUND IN SUPREMAPOKER!\n')

for i in range(60):
    time.sleep(1)
    if i % 15 == 14:
        print(f"  [{i+1}s] client_reqs={len(client_requests)} server_resps={len(server_responses)}")

print(f"\n{'='*60}")
print(f"CAPTURED {len(client_requests)} client requests:")
for req in client_requests:
    print(f"  [{req['reqId']}] {req['route']} ({req['bodyLen']}b)")
    if req['decoded']:
        print(f"    body: {json.dumps(req['decoded'], default=str)[:300]}")
    else:
        print(f"    hex: {req['bodyHex']}")

print(f"\nCAPTURED {len(server_responses)} direct responses:")
for resp in server_responses:
    dec_str = json.dumps(resp['decoded'], default=str)[:300] if resp['decoded'] else '?'
    print(f"  [{resp['reqId']}] {dec_str}")

sc.unload()
sess.detach()
