import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sess = frida.attach(100628)

js = r'''
var sslmod = Process.findModuleByName("libssl-1_1.dll");
var ssl_read = sslmod.findExportByName("SSL_read");
var count = 0;
Interceptor.attach(ssl_read, {
    onEnter: function(args) { this.buf = args[1]; },
    onLeave: function(retval) {
        var n = retval.toInt32();
        if (n > 0) {
            count++;
            if (count <= 30) {
                send({t:"d",c:count,s:n}, this.buf.readByteArray(Math.min(n, 200)));
            }
        }
    }
});
send({t:"ready"});
'''

sc = sess.create_script(js)
def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        if p.get('t') == 'ready':
            print("Ready", flush=True)
        elif p.get('t') == 'd':
            d = bytes(data) if data else b''
            hexd = ' '.join(f'{b:02x}' for b in d[:60])
            ascii_d = ''.join(chr(b) if 32<=b<127 else '.' for b in d[:60])
            print(f"[#{p['c']} {p['s']}B] {hexd}", flush=True)
            print(f"  ASCII: {ascii_d}", flush=True)

sc.on('message', on_msg)
sc.load()
for i in range(15):
    time.sleep(1)
sc.unload()
sess.detach()
