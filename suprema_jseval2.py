"""Find JS eval functions - compatible with older Frida API"""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

js = r'''
// Use callback-based API
var found = [];
Process.enumerateModules({
    onMatch: function(mod) {
        try {
            var exports = mod.enumerateExports();
            for (var j = 0; j < exports.length; j++) {
                var n = exports[j].name;
                if (n.indexOf('evalString') !== -1 ||
                    n.indexOf('evaluateScript') !== -1 ||
                    n.indexOf('executeScript') !== -1 ||
                    n.indexOf('ScriptingCore') !== -1 ||
                    n.indexOf('ScriptEngine') !== -1 ||
                    n.indexOf('jsb_run') !== -1 ||
                    n.indexOf('JS_Evaluate') !== -1 ||
                    n.indexOf('JS_ExecuteScript') !== -1 ||
                    n.indexOf('JS_CallFunction') !== -1) {
                    found.push(mod.name + ': ' + n + ' @ ' + exports[j].address);
                }
            }
        } catch(e) {}
    },
    onComplete: function() {
        send({t: 'done', count: found.length, items: found});
    }
});
'''

sc = sess.create_script(js)

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        print(f'Found {p["count"]} matches:')
        for item in p['items']:
            print(f'  {item}')
    elif msg['type'] == 'error':
        print(f'ERROR: {msg["description"]}')

sc.on('message', on_msg)
sc.load()
time.sleep(5)
sc.unload()
sess.detach()
