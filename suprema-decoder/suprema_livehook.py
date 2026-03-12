"""Live hook: captures card sprite names + SSL card data simultaneously."""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

js = r'''
try {
    var libcocos = Process.findModuleByName("libcocos2d.dll");
    var exps = libcocos.enumerateExports();
    var getSFBN = null, setSF = null;
    for (var i = 0; i < exps.length; i++) {
        var n = exps[i].name;
        if (n.indexOf('getSpriteFrameByName') !== -1) getSFBN = exps[i].address;
        if (n.indexOf('setSpriteFrame') !== -1 && n.indexOf('basic_string') !== -1 && n.indexOf('Sprite@cocos2d') !== -1) setSF = exps[i].address;
    }
    function readStdString(strPtr) {
        var size = strPtr.add(16).readU32();
        var cap = strPtr.add(20).readU32();
        if (size === 0 || size > 500) return null;
        if (cap >= 16) return strPtr.readPointer().readUtf8String(size);
        return strPtr.readUtf8String(size);
    }
    if (getSFBN) {
        Interceptor.attach(getSFBN, {
            onEnter: function(args) {
                try { var name = readStdString(args[1]); if (name) send({t:"gsf",n:name}); } catch(e) {}
            }
        });
        send({t:"info",msg:"Hooked getSpriteFrameByName"});
    }
    if (setSF) {
        Interceptor.attach(setSF, {
            onEnter: function(args) {
                try { var name = readStdString(args[1]); if (name) send({t:"ssf",n:name}); } catch(e) {}
            }
        });
        send({t:"info",msg:"Hooked setSpriteFrame"});
    }
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    var ssl_read = sslmod.findExportByName("SSL_read");
    Interceptor.attach(ssl_read, {
        onEnter: function(args) { this.buf = args[1]; },
        onLeave: function(retval) {
            var n = retval.toInt32();
            if (n > 0) send({t:"ssl",s:n}, this.buf.readByteArray(n));
        }
    });
    send({t:"info",msg:"Hooked SSL_read"});
    send({t:"ready"});
} catch(e) {
    send({t:"fatal",e:e.toString()});
}
'''

sc = sess.create_script(js)
seen = set()
log = []

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t','')
        if t == 'info':
            print(p['msg'], flush=True)
        elif t in ('gsf','ssf'):
            name = p['n']
            if name not in seen:
                seen.add(name)
                log.append(name)
                print(f"[SPRITE] {name}", flush=True)
        elif t == 'ssl':
            if data and len(data) > 4:
                d = bytes(data)
                try:
                    import msgpack
                    if d[0] == 4:
                        body = d[4:]
                        if len(body) > 2:
                            flag = body[0]
                            mt = (flag >> 1) & 0x07
                            off = 1
                            if mt in (0,1):
                                while off < len(body):
                                    b = body[off]; off += 1
                                    if not (b & 0x80): break
                            if mt in (0,2):
                                if flag & 1: off += 2
                                else:
                                    if off < len(body):
                                        rlen = body[off]; off += 1; off += rlen
                            pl = msgpack.unpackb(body[off:], raw=False)
                            if isinstance(pl, dict):
                                for key in ['cards','handCards','lightcards','publicCards','boardCards']:
                                    if key in pl:
                                        print(f"[CARDS] {key}={pl[key]}", flush=True)
                except: pass
        elif t == 'ready':
            print("\nPRONTO - jogue pra capturar!\n", flush=True)
        elif t == 'fatal':
            print(f"FATAL: {p['e']}", flush=True)
    elif msg['type'] == 'error':
        print(f"ERR: {msg['description']}", flush=True)

sc.on('message', on_msg)
sc.load()
print("Monitorando...", flush=True)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
print(f"\nSprites: {len(log)}")
for s in log: print(f"  {s}")
sc.unload()
sess.detach()
