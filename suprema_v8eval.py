"""Use v8 debug::EvaluateGlobal to run JS in game context and extract card mapping"""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

# Hook SSL_read and when we get card data, also evaluate JS in the game
# to call the card decode function
js = r'''
// Hook SSL_read to capture card data
var sslmod = Process.findModuleByName("libssl-1_1.dll");
var ssl_read = sslmod.findExportByName("SSL_read");

Interceptor.attach(ssl_read, {
    onEnter: function(args) { this.buf = args[1]; },
    onLeave: function(retval) {
        var n = retval.toInt32();
        if (n > 0) { send({t: "ssl", s: n}, this.buf.readByteArray(n)); }
    }
});

// Search process memory for the JS card class definition
// We know the PokerCards class has COLORS, NUMBERS, CARDS, NUMBER_RANK
// It's at 0x1216a000 area in memory
// But we need to find the actual runtime values

// Let's try a different approach - search for arrays of integers 0-51
// that look like a card deck or card mapping table
// A standard deck = [0,1,2,...,51] or some permutation

// Search libcocos2d for the ScriptingCore/se::ScriptEngine
var libcocos = Process.findModuleByName("libcocos2d.dll");
var exps = libcocos.enumerateExports();

// Find se::ScriptEngine (cocos2d-x v3.17+ uses this)
var seExports = [];
for (var i = 0; i < exps.length; i++) {
    var n = exps[i].name;
    if (n.indexOf('ScriptEngine') !== -1) {
        seExports.push({name: n, addr: exps[i].address.toString()});
    }
}
send({t: "se_exports", count: seExports.length, sample: seExports.slice(0,30).map(function(e){return e.name;})});

// Find evalString in se::ScriptEngine
for (var i = 0; i < exps.length; i++) {
    var n = exps[i].name;
    if (n.indexOf('evalString') !== -1) {
        send({t: "found_eval", name: n, addr: exps[i].address.toString()});
    }
}

send({t: "ready"});
'''

sc = sess.create_script(js)
def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t','')
        if t == 'ssl':
            pass
        elif t == 'se_exports':
            print(f'ScriptEngine exports: {p["count"]}')
            for n in p.get('sample', []):
                print(f'  {n}')
        elif t == 'found_eval':
            print(f'*** EVAL: {p["name"]} @ {p["addr"]} ***')
        elif t == 'ready':
            print('Ready')
        else:
            print(json.dumps(p))
    elif msg['type'] == 'error':
        print(f'ERR: {msg["description"]}')

sc.on('message', on_msg)
sc.load()
time.sleep(3)
sc.unload()
sess.detach()
