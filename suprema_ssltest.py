import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 100628
print(f"Attaching to {pid}...")
sess = frida.attach(pid)

js = r'''
try {
    // List all loaded modules to verify
    var mods = [];
    Process.enumerateModules({
        onMatch: function(m) { mods.push(m.name + " @ " + m.base + " (" + m.size + ")"); },
        onComplete: function() { send({t:"mods", items: mods}); }
    });
} catch(e) {
    // Fallback
    var ssl = Process.findModuleByName("libssl-1_1.dll");
    if (ssl) {
        send({t:"ssl_found", base: ssl.base.toString(), size: ssl.size});
    } else {
        send({t:"no_ssl"});
    }
}
'''

sc = sess.create_script(js)
def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        if p.get('t') == 'mods':
            print(f"Modules: {len(p['items'])}")
            for m in p['items']:
                if 'ssl' in m.lower() or 'cocos' in m.lower() or 'v8' in m.lower():
                    print(f"  {m}")
        else:
            print(json.dumps(p))
    elif msg['type'] == 'error':
        print(f"ERR: {msg['description']}")

sc.on('message', on_msg)
sc.load()
time.sleep(3)
sc.unload()
sess.detach()
