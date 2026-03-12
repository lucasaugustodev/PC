"""Use Frida to evaluate JS in the game's SpiderMonkey context"""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

# The game uses cocos2d-x with SpiderMonkey (mozjs-52)
# There's a global JS context we can use to evaluate code
# The ScriptingCore singleton has evalString method
# But we didn't find it in exports - it might be in the exe itself

js = r'''
// Find all modules and look for evalString/executeScript in ALL of them
var modules = Process.enumerateModulesSync();
var found = [];
for (var i = 0; i < modules.length; i++) {
    var mod = modules[i];
    try {
        var exports = mod.enumerateExports();
        for (var j = 0; j < exports.length; j++) {
            var n = exports[j].name;
            if (n.indexOf('evalString') !== -1 ||
                n.indexOf('evaluateScript') !== -1 ||
                n.indexOf('executeScript') !== -1 ||
                n.indexOf('executeLine') !== -1 ||
                n.indexOf('ScriptingCore') !== -1 ||
                n.indexOf('jsb_run_script') !== -1 ||
                n.indexOf('JS_Evaluate') !== -1 ||
                n.indexOf('JS_ExecuteScript') !== -1) {
                found.push({mod: mod.name, fn: n, addr: exports[j].address.toString()});
            }
        }
    } catch(e) {}
}
send({t: 'eval_search', count: found.length, items: found});

// Also look for se::ScriptEngine which is the newer cocos2d-x binding
for (var i = 0; i < modules.length; i++) {
    var mod = modules[i];
    try {
        var exports = mod.enumerateExports();
        for (var j = 0; j < exports.length; j++) {
            var n = exports[j].name;
            if (n.indexOf('ScriptEngine') !== -1 &&
                (n.indexOf('eval') !== -1 || n.indexOf('Eval') !== -1 ||
                 n.indexOf('exec') !== -1 || n.indexOf('Exec') !== -1)) {
                found.push({mod: mod.name, fn: n, addr: exports[j].address.toString()});
            }
        }
    } catch(e) {}
}
send({t: 'script_engine', count: found.length, items: found});
'''

sc = sess.create_script(js)

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        print(f'\n[{p["t"]}] Found {p["count"]}:')
        for item in p.get('items', []):
            print(f'  [{item["mod"]}] {item["fn"]} @ {item["addr"]}')
    elif msg['type'] == 'error':
        print(f'ERROR: {msg["description"]}')

sc.on('message', on_msg)
sc.load()
time.sleep(3)
sc.unload()
sess.detach()
