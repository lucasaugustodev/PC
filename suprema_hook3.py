import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sess = frida.attach(100628)

js = r'''
try {
    var libcocos = Process.findModuleByName("libcocos2d.dll");
    if (!libcocos) { send({t:"err",m:"no libcocos2d"}); }
    else {
        send({t:"info",m:"libcocos2d @ "+libcocos.base+" size="+libcocos.size});
        
        var getSFBN = null;
        var exps = libcocos.enumerateExports();
        send({t:"info",m:"exports: "+exps.length});
        
        for (var i = 0; i < exps.length; i++) {
            if (exps[i].name.indexOf("getSpriteFrameByName") !== -1) {
                getSFBN = exps[i].address;
            }
        }
        
        if (getSFBN) {
            send({t:"info",m:"getSFBN @ "+getSFBN});
            var cc = 0;
            Interceptor.attach(getSFBN, {
                onEnter: function(args) {
                    cc++;
                    if (cc <= 50) send({t:"call",c:cc});
                }
            });
            send({t:"info",m:"Interceptor attached OK"});
        }
    }
    
    // SSL
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    if (sslmod) {
        send({t:"info",m:"libssl @ "+sslmod.base});
        var ssl_read = sslmod.findExportByName("SSL_read");
        var sslcc = 0;
        Interceptor.attach(ssl_read, {
            onEnter: function(args) { this.buf = args[1]; },
            onLeave: function(retval) {
                var n = retval.toInt32();
                if (n > 0) { sslcc++; if (sslcc <= 100) send({t:"ssl",s:n}); }
            }
        });
        send({t:"info",m:"SSL hooked"});
    } else {
        send({t:"err",m:"no libssl-1_1.dll"});
    }
    
    send({t:"ready"});
} catch(e) {
    send({t:"fatal",e:e.toString()});
}
'''

sc = sess.create_script(js)
def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t','')
        if t in ('info','err','ready','fatal'):
            print(f"[{t}] {p.get('m',p.get('e',''))}", flush=True)
        elif t == 'call':
            print(f"[SPRITE CALL #{p['c']}]", flush=True)
        elif t == 'ssl':
            print(f"[SSL] {p['s']} bytes", flush=True)
    elif msg['type'] == 'error':
        print(f"FRIDA-ERR: {msg['description']}", flush=True)

sc.on('message', on_msg)
sc.load()
print("Waiting 30s...", flush=True)
for i in range(30):
    time.sleep(1)
    if i % 10 == 9:
        print(f"  ...{i+1}s", flush=True)

sc.unload()
sess.detach()
print("Done", flush=True)
