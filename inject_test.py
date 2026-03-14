"""Raw injection test - see if server responds at all."""
import frida, time, sys, json, random, msgpack
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sess = frida.attach(15020)
sc = sess.create_script(r'''
var sslmod = Process.findModuleByName("libssl-1_1.dll");
var ssl_write = sslmod.findExportByName("SSL_write");
var ssl_write_fn = new NativeFunction(ssl_write, "int", ["pointer", "pointer", "int"]);
var gameSSL = null;
var conns = {};
Interceptor.attach(sslmod.findExportByName("SSL_read"), {
    onEnter: function(a) { this.ssl=a[0]; this.buf=a[1]; },
    onLeave: function(r) {
        var n=r.toInt32();
        if(n>0) {
            var p=this.ssl.toString();
            var b0=this.buf.readU8();
            if(b0===0x82||b0===4){gameSSL=this.ssl;conns[p]=true;}
            if(conns[p]) send({d:"R",n:n}, this.buf.readByteArray(n));
        }
    }
});
Interceptor.attach(ssl_write, {
    onEnter: function(a) {
        this.ssl=a[0]; var n=a[2].toInt32();
        if(n>0){var p=this.ssl.toString();var b0=a[1].readU8();
        if(b0===0x82||b0===4){gameSSL=this.ssl;conns[p]=true;}
        if(conns[p]) send({d:"S",n:n}, a[1].readByteArray(n));}
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

traffic_after = []
injected = False

def on_msg(msg, data):
    if msg['type'] != 'send':
        return
    p = msg['payload']
    if p.get('t') == 'ready':
        print('HOOK OK')
        return
    if not data:
        return
    d = p.get('d', '?')
    raw = bytes(data)
    if injected:
        traffic_after.append((d, raw))
        print(f'  {d} {len(raw)}b: {raw[:50].hex()}')
    sys.stdout.flush()

sc.on('message', on_msg)
sc.load()
time.sleep(3)

# Build WS frame
def build_ws(payload):
    f = bytearray([0x82])
    pl = len(payload)
    if pl < 126:
        f.append(0x80 | pl)
    elif pl < 65536:
        f.append(0x80 | 126)
        f.extend(pl.to_bytes(2, 'big'))
    m = bytes([random.randint(0, 255) for _ in range(4)])
    f.extend(m)
    mp = bytearray(payload)
    for i in range(len(mp)):
        mp[i] ^= m[i % 4]
    f.extend(mp)
    return bytes(f)

# Build Pomelo request
route = b'apiPlayer.playerHandler.joinGameRoom'
body = json.dumps({
    "clubID": "14625", "unionID": 113, "myClubID": 41157, "myUnionID": 128,
    "roomID": "14625_43107012#113@41157%128",
    "privatecode": None, "ver": 7288, "lan": "pt", "verPackage": "5"
}).encode()
inner = bytes([0, 200, len(route)]) + route + body  # reqId=200
plen = len(inner)
pomelo = bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner
ws = build_ws(pomelo)

print(f'\nInjecting joinGameRoom ({len(ws)}b)...')
injected = True
result = sc.exports_sync.inject(ws.hex())
print(f'SSL_write: {result}')

print('Esperando 8s...')
sys.stdout.flush()
time.sleep(8)
print(f'\nTotal packets after inject: {len(traffic_after)}')
for d, raw in traffic_after:
    print(f'  {d} {len(raw)}b')
    # Try to decode
    if d == 'R' and len(raw) > 4:
        # Try unframe WS
        if raw[0] == 0x82:
            pl = raw[1] & 0x7F
            off = 2
            if pl == 126:
                pl = (raw[2] << 8) | raw[3]
                off = 4
            payload = raw[off:off+pl]
            if len(payload) > 0:
                pt = payload[0]
                if pt == 2 and len(payload) >= 4:
                    rid = (payload[1]<<16)|(payload[2]<<8)|payload[3]
                    print(f'    RESPONSE type=2 reqId={rid}')
                    if len(payload) > 4:
                        try:
                            b = msgpack.unpackb(payload[4:], raw=False)
                            bs = json.dumps(b, default=str, ensure_ascii=False)
                            print(f'    body: {bs[:300]}')
                        except:
                            print(f'    raw: {payload[4:50].hex()}')
                elif pt == 4 and len(payload) >= 4:
                    pplen = (payload[1]<<16)|(payload[2]<<8)|payload[3]
                    pb = payload[4:4+pplen]
                    if len(pb) >= 2:
                        rl = pb[1]
                        route = bytes(pb[2:2+rl]).decode('utf-8', errors='replace')
                        print(f'    PUSH route={route}')
                        if 2+rl < len(pb):
                            try:
                                b = msgpack.unpackb(pb[2+rl:], raw=False)
                                if isinstance(b, dict):
                                    print(f'    event={b.get("event","")}')
                                    bs = json.dumps(b, default=str, ensure_ascii=False)
                                    print(f'    body: {bs[:300]}')
                            except:
                                pass

sc.unload()
sess.detach()
print('Done')
