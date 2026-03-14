"""Injection test v2 - try simple requests first, then joinGameRoom."""
import frida, time, sys, json, random, msgpack
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sess = frida.attach(15020)
sc = sess.create_script(r'''
var sslmod = Process.findModuleByName("libssl-1_1.dll");
var ssl_write = sslmod.findExportByName("SSL_write");
var ssl_write_fn = new NativeFunction(ssl_write, "int", ["pointer", "pointer", "int"]);
var gameSSL = null; var conns = {};
Interceptor.attach(sslmod.findExportByName("SSL_read"), {
    onEnter: function(a) { this.ssl=a[0]; this.buf=a[1]; },
    onLeave: function(r) {
        var n=r.toInt32(); if(n>0) {
            var p=this.ssl.toString(); var b0=this.buf.readU8();
            if(b0===0x82||b0===4){gameSSL=this.ssl;conns[p]=true;}
            if(conns[p]) send({d:"R"}, this.buf.readByteArray(n));
        }
    }
});
Interceptor.attach(ssl_write, {
    onEnter: function(a) {
        this.ssl=a[0]; var n=a[2].toInt32(); if(n>0) {
            var p=this.ssl.toString(); var b0=a[1].readU8();
            if(b0===0x82||b0===4){gameSSL=this.ssl;conns[p]=true;}
            if(conns[p]) send({d:"S"}, a[1].readByteArray(n));
        }
    }
});
rpc.exports = {
    inject: function(hex) {
        if(!gameSSL) return "NO_SSL";
        var d=[]; for(var i=0;i<hex.length;i+=2) d.push(parseInt(hex.substr(i,2),16));
        var b=Memory.alloc(d.length); b.writeByteArray(d);
        return "OK:"+ssl_write_fn(gameSSL,b,d.length);
    }
};
send({t:"ready"});
''')

results = []

def on_msg(msg, data):
    if msg['type'] != 'send': return
    p = msg['payload']
    if p.get('t') == 'ready': print('HOOK OK'); return
    if not data: return
    results.append((p.get('d','?'), bytes(data)))

sc.on('message', on_msg)
sc.load()
time.sleep(3)

def build_ws(payload):
    f = bytearray([0x82])
    pl = len(payload)
    if pl < 126: f.append(0x80 | pl)
    elif pl < 65536: f.append(0x80 | 126); f.extend(pl.to_bytes(2, 'big'))
    m = bytes([random.randint(0, 255) for _ in range(4)])
    f.extend(m)
    mp = bytearray(payload)
    for i in range(len(mp)): mp[i] ^= m[i % 4]
    f.extend(mp)
    return bytes(f)

def build_req(reqid, route_str, body_dict):
    route = route_str.encode('utf-8')
    body = json.dumps(body_dict).encode('utf-8')
    inner = bytes([(reqid >> 8) & 0xFF, reqid & 0xFF, len(route)]) + route + body
    plen = len(inner)
    pomelo = bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner
    return pomelo

def decode_response(raw):
    """Try to decode a server response."""
    # Unframe WS
    if len(raw) < 2 or raw[0] != 0x82: return f"not-ws: {raw[:20].hex()}"
    pl = raw[1] & 0x7F; off = 2
    if pl == 126: pl = (raw[2]<<8)|raw[3]; off = 4
    elif pl == 127: pl = int.from_bytes(raw[2:10], 'big'); off = 10
    payload = raw[off:off+pl]
    if len(payload) < 4: return f"short: {payload.hex()}"

    ptype = payload[0]
    if ptype == 3: return "HEARTBEAT"
    if ptype == 4:
        pplen = (payload[1]<<16)|(payload[2]<<8)|payload[3]
        pb = payload[4:4+pplen]
        if len(pb) < 2: return f"type4-short: {pb.hex()}"
        flags = pb[0]
        # Check if compressed route (bit 0 not set)
        if (flags & 1) == 0:
            # Compressed: [flags 1B] [routeCode 2B] [msgpack]
            if len(pb) >= 3:
                route_code = (pb[1] << 8) | pb[2]
                body = None
                if len(pb) > 3:
                    try: body = msgpack.unpackb(pb[3:], raw=False)
                    except: body = pb[3:30].hex()
                return f"PUSH(compressed) flags={flags} routeCode={route_code} body={body}"
        else:
            # String route: [flags 1B] [routeLen 1B] [route] [msgpack]
            rl = pb[1]; off2 = 2+rl
            route = bytes(pb[2:2+rl]).decode('utf-8', errors='replace')
            body = None
            if off2 < len(pb):
                try: body = msgpack.unpackb(pb[off2:], raw=False)
                except: body = pb[off2:off2+30].hex()
            return f"PUSH route={route} body={body}"
    if ptype == 2:
        reqid = (payload[1]<<16)|(payload[2]<<8)|payload[3]
        body = None
        if len(payload) > 4:
            try: body = msgpack.unpackb(payload[4:], raw=False)
            except: body = payload[4:30].hex()
        return f"RESPONSE reqId={reqid} body={body}"
    return f"UNK type={ptype} hex={payload[:30].hex()}"

def inject_and_wait(reqid, route, body, label, wait=5):
    print(f"\n{'='*50}")
    print(f"TEST: {label}")
    print(f"  route: {route}")
    print(f"  reqId: {reqid}")
    print(f"  body: {json.dumps(body)[:200]}")

    results.clear()
    pomelo = build_req(reqid, route, body)
    ws = build_ws(pomelo)
    r = sc.exports_sync.inject(ws.hex())
    print(f"  SSL_write: {r}")
    sys.stdout.flush()

    time.sleep(wait)
    # Check responses
    recv_count = 0
    for d, raw in results:
        if d == 'R':
            recv_count += 1
            decoded = decode_response(raw)
            # Skip heartbeats and periodic pushes
            if 'HEARTBEAT' in decoded: continue
            if 'matchesStatus' in str(decoded): continue
            if 'jackpot' in str(decoded): continue
            print(f"  RECV: {decoded[:400]}")
    print(f"  ({recv_count} total recv packets)")
    sys.stdout.flush()

# TEST 1: getPrefsData (simple, should always work)
inject_and_wait(200, "apiPlayer.playerHandler.getPrefsData",
    {"ver": 7288, "lan": "pt", "verPackage": "5"},
    "getPrefsData")

# TEST 2: joinGameRoom with a fresh match
# First let's try the same format as captured
inject_and_wait(201, "apiPlayer.playerHandler.joinGameRoom",
    {"clubID": "14625", "unionID": 113, "myClubID": 41157, "myUnionID": 128,
     "roomID": "14625_43107012#113@41157%128",
     "privatecode": None, "ver": 7288, "lan": "pt", "verPackage": "5"},
    "joinGameRoom (match 43107012)")

# TEST 3: clubHandler.info (should return club data)
inject_and_wait(202, "apiClub.clubHandler.info",
    {"unionID": 128, "clubID": 41157, "matchID": 0, "tableID": 0,
     "myClubID": 41157, "myUnionID": 128,
     "roomID": "41157_0#128@41157%128",
     "ver": 7288, "lan": "pt", "verPackage": "5"},
    "clubHandler.info")

# TEST 4: matchHandler.match (list matches)
inject_and_wait(203, "apiClubMatch.clubMatchHandler.match",
    {"unionID": 128, "clubID": 41157, "matchID": 0, "tableID": 0,
     "myClubID": 41157, "myUnionID": 128,
     "roomID": "41157_0#128@41157%128",
     "ver": 7288, "lan": "pt", "verPackage": "5"},
    "clubMatchHandler.match")

print("\n\nDone!")
sc.unload()
sess.detach()
