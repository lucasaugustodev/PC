"""Find XXTEA key and eval JS in ScriptingCore"""
import frida, json, time, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

js = r'''
var libcocos = Process.findModuleByName('libcocos2d.dll');
var exports = libcocos.enumerateExports();

// Find ScriptingCore exports
var scExports = [];
for (var i = 0; i < exports.length; i++) {
    if (exports[i].name.indexOf('ScriptingCore') !== -1) {
        scExports.push({name: exports[i].name, addr: exports[i].address});
    }
}

// Send just names
var names = [];
for (var i = 0; i < scExports.length; i++) names.push(scExports[i].name);
send({t: 'sc_list', items: names});

// Find getInstance
var getInstance = null;
for (var i = 0; i < scExports.length; i++) {
    if (scExports[i].name.indexOf('getInstance') !== -1) {
        getInstance = scExports[i];
        break;
    }
}

if (getInstance) {
    send({t: 'info', msg: 'getInstance at ' + getInstance.addr});
    var fn = new NativeFunction(getInstance.addr, 'pointer', []);
    var sc = fn();
    send({t: 'info', msg: 'ScriptingCore ptr: ' + sc});

    // Dump instance memory to find key string
    try {
        var bytes = sc.readByteArray(1024);
        var arr = new Uint8Array(bytes);
        var hex = '';
        var ascii = '';
        for (var i = 0; i < arr.length; i++) {
            hex += ('0' + arr[i].toString(16)).slice(-2) + ' ';
            ascii += (arr[i] >= 32 && arr[i] < 127) ? String.fromCharCode(arr[i]) : '.';
        }
        send({t: 'mem_ascii', data: ascii});
    } catch(e) {
        send({t: 'error', msg: e.message});
    }

    // Find evalString / executeScript
    var evalFns = [];
    for (var i = 0; i < scExports.length; i++) {
        if (scExports[i].name.indexOf('eval') !== -1 ||
            scExports[i].name.indexOf('Eval') !== -1 ||
            scExports[i].name.indexOf('execute') !== -1 ||
            scExports[i].name.indexOf('Execute') !== -1 ||
            scExports[i].name.indexOf('runScript') !== -1 ||
            scExports[i].name.indexOf('compileScript') !== -1) {
            evalFns.push({name: scExports[i].name, addr: scExports[i].address.toString()});
        }
    }
    send({t: 'eval_fns', items: evalFns});
}
'''

sc = sess.create_script(js)

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t == 'sc_list':
            print('ScriptingCore exports:')
            for n in p['items']:
                print(f'  {n}')
        elif t == 'mem_ascii':
            d = p['data']
            print(f'\nScriptingCore memory dump ({len(d)} bytes):')
            for i in range(0, min(len(d), 1024), 64):
                print(f'  +{i:4d}: {d[i:i+64]}')
        elif t == 'eval_fns':
            print('\nEval/Execute functions:')
            for item in p['items']:
                print(f'  {item["name"]} @ {item["addr"]}')
        elif t == 'info':
            print(f'[INFO] {p["msg"]}')
        elif t == 'error':
            print(f'[ERR] {p["msg"]}')
        else:
            print(f'[{t}] {json.dumps(p)}')
    elif msg['type'] == 'error':
        print(f'ERROR: {msg["description"]}')

sc.on('message', on_msg)
sc.load()
time.sleep(3)
sc.unload()
sess.detach()
