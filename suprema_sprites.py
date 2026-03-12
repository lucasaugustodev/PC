"""List all sprite-related exports and hook the most relevant ones"""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

js = r'''
var libcocos = Process.findModuleByName("libcocos2d.dll");
var exps = libcocos.enumerateExports();

var results = [];
for (var i = 0; i < exps.length; i++) {
    var n = exps[i].name;
    if (n.indexOf('Sprite') !== -1 || n.indexOf('sprite') !== -1 ||
        n.indexOf('Texture') !== -1 || n.indexOf('texture') !== -1 ||
        n.indexOf('addImage') !== -1 || n.indexOf('Frame') !== -1) {
        results.push(n);
    }
}
send({t: "sprites", items: results});
'''

sc = sess.create_script(js)
done = False
def on_msg(msg, data):
    global done
    if msg['type'] == 'send':
        p = msg['payload']
        print(f"Found {len(p['items'])} sprite/texture exports:")
        for item in sorted(p['items']):
            print(f"  {item}")
    elif msg['type'] == 'error':
        print(f"ERR: {msg['description']}")
    done = True

sc.on('message', on_msg)
sc.load()
for i in range(30):
    time.sleep(0.2)
    if done:
        break
sc.unload()
sess.detach()
