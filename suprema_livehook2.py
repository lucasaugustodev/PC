"""Live hook v2: log ALL sprite names + SSL traffic. No filtering."""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 100628
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

    // Try multiple ways to read the string argument
    function tryReadStr(arg) {
        // Method 1: direct UTF8 (if const char*)
        try {
            var s = arg.readUtf8String();
            if (s && s.length > 0 && s.length < 300) return "m1:" + s;
        } catch(e) {}
        // Method 2: MSVC std::string SSO
        try {
            var size = arg.add(16).readU32();
            var cap = arg.add(20).readU32();
            if (size > 0 && size < 300) {
                if (cap >= 16) {
                    return "m2h:" + arg.readPointer().readUtf8String(size);
                } else {
                    return "m2s:" + arg.readUtf8String(size);
                }
            }
        } catch(e) {}
        // Method 3: pointer to char*
        try {
            var p = arg.readPointer();
            var s = p.readUtf8String();
            if (s && s.length > 0 && s.length < 300) return "m3:" + s;
        } catch(e) {}
        return null;
    }

    var count = 0;
    if (getSFBN) {
        Interceptor.attach(getSFBN, {
            onEnter: function(args) {
                try {
                    var s = tryReadStr(args[1]);
                    if (s) { count++; send({t:"gsf",n:s,c:count}); }
                } catch(e) { send({t:"gerr",e:e.toString()}); }
            }
        });
        send({t:"ok",msg:"getSpriteFrameByName hooked"});
    }
    if (setSF) {
        Interceptor.attach(setSF, {
            onEnter: function(args) {
                try {
                    var s = tryReadStr(args[1]);
                    if (s) { count++; send({t:"ssf",n:s,c:count}); }
                } catch(e) { send({t:"serr",e:e.toString()}); }
            }
        });
        send({t:"ok",msg:"setSpriteFrame hooked"});
    }

    // SSL
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    var ssl_read = sslmod.findExportByName("SSL_read");
    Interceptor.attach(ssl_read, {
        onEnter: function(args) { this.buf = args[1]; },
        onLeave: function(retval) {
            var n = retval.toInt32();
            if (n > 0) send({t:"ssl",s:n}, this.buf.readByteArray(n));
        }
    });

    send({t:"ready"});
} catch(e) {
    send({t:"fatal",e:e.toString()});
}
'''

sc = sess.create_script(js)
outf = open("C:/Users/PC/suprema_livehook2_out.txt", "w", encoding="utf-8")

def log(s):
    print(s, flush=True)
    outf.write(s + "\n")
    outf.flush()

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t','')
        if t in ('ok','ready','fatal'):
            log(f"[{t}] {p.get('msg', p.get('e',''))}")
        elif t in ('gsf','ssf'):
            log(f"[{t} #{p.get('c',0)}] {p['n']}")
        elif t in ('gerr','serr'):
            log(f"[ERR] {p['e']}")
        elif t == 'ssl':
            if data and len(data) > 4:
                d = bytes(data)
                try:
                    import msgpack
                    if d[0] == 4:
                        body = d[4:]
                        flag = body[0]
                        mt = (flag >> 1) & 0x07
                        off = 1
                        if mt in (0,1):
                            while off < len(body):
                                b = body[off]; off += 1
                                if not (b & 0x80): break
                        route = ""
                        if mt in (0,2):
                            if flag & 1: off += 2
                            else:
                                rlen = body[off]; off += 1
                                route = body[off:off+rlen].decode('ascii','replace')
                                off += rlen
                        pl = msgpack.unpackb(body[off:], raw=False)
                        if isinstance(pl, dict):
                            for key in ['cards','handCards','lightcards','publicCards','boardCards','curCards']:
                                if key in pl:
                                    log(f"[CARDS] route={route} {key}={pl[key]}")
                except: pass
    elif msg['type'] == 'error':
        log(f"[FRIDA-ERR] {msg['description']}")

sc.on('message', on_msg)
sc.load()
log("Monitorando tudo...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

outf.close()
sc.unload()
sess.detach()
