"""Find XXTEA key by reading xxtea_decrypt code"""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

js = r'''
// Read xxtea_decrypt disassembly to find key reference
var xxtea = ptr('0x500ebb10');
var code = xxtea.readByteArray(128);
send({t: 'xxtea_bytes'}, code);

// Also search all of libcocos2d for js_ or jsb_ exports
var libcocos = Process.findModuleByName('libcocos2d.dll');
var exports = libcocos.enumerateExports();
var interesting = [];
for (var i = 0; i < exports.length; i++) {
    var n = exports[i].name;
    if (n.indexOf('jsb_') === 0 || n.indexOf('js_cocos') === 0) {
        interesting.push(n + ' @ ' + exports[i].address);
    }
}
send({t: 'jsb', data: interesting.slice(0, 50).join('\n')});

// Find evaluate/run script functions
var evalFns = [];
for (var i = 0; i < exports.length; i++) {
    var n = exports[i].name;
    if (n.indexOf('evalString') !== -1 || n.indexOf('EvalString') !== -1 ||
        n.indexOf('evaluateScript') !== -1 || n.indexOf('executeScript') !== -1 ||
        n.indexOf('runScript') !== -1 || n.indexOf('RunScript') !== -1 ||
        n.indexOf('compileScript') !== -1) {
        evalFns.push(n + ' @ ' + exports[i].address);
    }
}
send({t: 'eval', data: evalFns.join('\n')});
'''

sc = sess.create_script(js)

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t == 'xxtea_bytes' and data:
            arr = bytes(data)
            hexstr = ' '.join(f'{b:02x}' for b in arr)
            print(f'xxtea_decrypt bytes:\n{hexstr}')
        elif t == 'jsb':
            print(f'\njsb exports:\n{p["data"]}')
        elif t == 'eval':
            print(f'\nEval functions:\n{p["data"]}')
    elif msg['type'] == 'error':
        print(f'ERROR: {msg["description"]}')

sc.on('message', on_msg)
sc.load()
time.sleep(3)
sc.unload()
sess.detach()
