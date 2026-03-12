"""Debug hook: log EVERY call to getSpriteFrameByName with raw arg bytes"""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 100628
sess = frida.attach(pid)

js = r'''
try {
    var libcocos = Process.findModuleByName("libcocos2d.dll");
    var exps = libcocos.enumerateExports();
    var getSFBN = null;
    for (var i = 0; i < exps.length; i++) {
        if (exps[i].name.indexOf('getSpriteFrameByName') !== -1) {
            getSFBN = exps[i].address;
            break;
        }
    }

    if (getSFBN) {
        var callCount = 0;
        Interceptor.attach(getSFBN, {
            onEnter: function(args) {
                callCount++;
                // Dump raw bytes of arg[1] to understand the layout
                try {
                    var raw = args[1].readByteArray(32);
                    send({t:"raw", c:callCount}, raw);
                } catch(e) {
                    send({t:"read_err", c:callCount, e:e.toString()});
                }
            }
        });
        send({t:"ok", msg:"Hooked getSpriteFrameByName @ " + getSFBN});
    } else {
        send({t:"err", msg:"getSpriteFrameByName NOT FOUND"});
    }

    // Also hook SSL
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    if (sslmod) {
        var ssl_read = sslmod.findExportByName("SSL_read");
        Interceptor.attach(ssl_read, {
            onEnter: function(args) { this.buf = args[1]; this.sz = args[2].toInt32(); },
            onLeave: function(retval) {
                var n = retval.toInt32();
                if (n > 0) send({t:"ssl",s:n}, this.buf.readByteArray(n));
            }
        });
        send({t:"ok", msg:"Hooked SSL_read"});
    }

    send({t:"ready"});
} catch(e) {
    send({t:"fatal",e:e.toString()});
}
'''

sc = sess.create_script(js)
f = open("C:/Users/PC/suprema_hookdebug_out.txt", "w", encoding="utf-8")

def log(s):
    print(s, flush=True)
    f.write(s + "\n")
    f.flush()

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t','')
        if t in ('ok','ready','fatal','err'):
            log(f"[{t}] {p.get('msg', p.get('e',''))}")
        elif t == 'raw':
            c = p.get('c',0)
            if data:
                hexdump = ' '.join(f'{b:02x}' for b in bytes(data))
                # Try to interpret as MSVC std::string
                d = bytes(data)
                # Try SSO: first 16 bytes are char data, bytes 16-19 = size, 20-23 = capacity
                size = int.from_bytes(d[16:20], 'little')
                cap = int.from_bytes(d[20:24], 'little')
                if cap < 16 and size > 0 and size < 16:
                    sso_str = d[:size].decode('ascii','replace')
                    log(f"[gsf #{c}] SSO str='{sso_str}' size={size} cap={cap}")
                elif cap >= 16 and size > 0 and size < 500:
                    # Heap: first 4 bytes = pointer to data
                    ptr_val = int.from_bytes(d[:4], 'little')
                    log(f"[gsf #{c}] HEAP ptr=0x{ptr_val:08x} size={size} cap={cap}")
                else:
                    log(f"[gsf #{c}] RAW: {hexdump} (size={size} cap={cap})")
                if c <= 5:
                    log(f"  hex: {hexdump}")
            else:
                log(f"[gsf #{c}] no data")
        elif t == 'read_err':
            log(f"[gsf #{p.get('c',0)}] READ ERROR: {p['e']}")
        elif t == 'ssl':
            if data and len(data) > 4:
                d = bytes(data)
                if d[0] == 4:  # pomelo data
                    log(f"[SSL] {len(d)} bytes")
    elif msg['type'] == 'error':
        log(f"[FRIDA-ERR] {msg['description']}")

sc.on('message', on_msg)
sc.load()
log("Monitoring...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

f.close()
sc.unload()
sess.detach()
