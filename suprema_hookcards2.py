"""Hook card sprite functions - step by step with error handling"""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

js = r'''
try {
    var libcocos = Process.findModuleByName("libcocos2d.dll");
    var exps = libcocos.enumerateExports();

    // Find the exports we need
    var targets = {};
    for (var i = 0; i < exps.length; i++) {
        var n = exps[i].name;
        // Sprite::setSpriteFrame with string arg
        if (n.indexOf('setSpriteFrame') !== -1 && n.indexOf('basic_string') !== -1 && n.indexOf('Sprite@cocos2d') !== -1) {
            targets['setSF'] = {name: n, addr: exps[i].address};
        }
        // getSpriteFrameByName
        if (n.indexOf('getSpriteFrameByName') !== -1) {
            targets['getSFBN'] = {name: n, addr: exps[i].address};
        }
        // Scale9SpriteV2 setSpriteFrame with string
        if (n.indexOf('setSpriteFrame') !== -1 && n.indexOf('basic_string') !== -1 && n.indexOf('Scale9SpriteV2') !== -1) {
            targets['setSF2'] = {name: n, addr: exps[i].address};
        }
        // initWithSpriteFrameName for Sprite
        if (n.indexOf('initWithSpriteFrameName') !== -1 && n.indexOf('Sprite@cocos2d') !== -1 && n.indexOf('Scale9') === -1) {
            targets['initSFN'] = {name: n, addr: exps[i].address};
        }
    }

    send({t: "targets", items: Object.keys(targets).map(function(k) {
        return k + ": " + targets[k].name + " @ " + targets[k].addr;
    })});

    function readStdString(strPtr) {
        var size = strPtr.add(16).readU32();
        var cap = strPtr.add(20).readU32();
        if (size === 0 || size > 500) return null;
        if (cap >= 16) {
            return strPtr.readPointer().readUtf8String(size);
        } else {
            return strPtr.readUtf8String(size);
        }
    }

    // Hook getSpriteFrameByName first - broadest
    if (targets['getSFBN']) {
        Interceptor.attach(targets['getSFBN'].addr, {
            onEnter: function(args) {
                try {
                    var name = readStdString(args[1]);
                    if (name) {
                        send({t: "gsf", n: name});
                    }
                } catch(e) {
                    send({t: "gsf_err", e: e.toString()});
                }
            }
        });
        send({t: "hooked", fn: "getSpriteFrameByName"});
    }

    // Hook Sprite::setSpriteFrame(string)
    if (targets['setSF']) {
        Interceptor.attach(targets['setSF'].addr, {
            onEnter: function(args) {
                try {
                    var name = readStdString(args[1]);
                    if (name) {
                        send({t: "ssf", n: name});
                    }
                } catch(e) {
                    send({t: "ssf_err", e: e.toString()});
                }
            }
        });
        send({t: "hooked", fn: "setSpriteFrame"});
    }

    send({t: "ready"});
} catch(e) {
    send({t: "fatal", e: e.toString()});
}
'''

sc = sess.create_script(js)
sprites = set()
sprite_log = []

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t == 'targets':
            print("Targets found:")
            for item in p['items']:
                print(f"  {item}")
        elif t == 'hooked':
            print(f"Hooked: {p['fn']}")
        elif t in ('gsf', 'ssf'):
            name = p['n']
            if name not in sprites:
                sprites.add(name)
                print(f"[{t}] {name}")
                sprite_log.append(name)
        elif t in ('gsf_err', 'ssf_err'):
            print(f"Hook error: {p['e']}")
        elif t == 'ready':
            print("\n=== READY - Navigate in-game to trigger card rendering ===\n")
        elif t == 'fatal':
            print(f"FATAL: {p['e']}")
        else:
            print(json.dumps(p))
    elif msg['type'] == 'error':
        print(f"ERR: {msg['description']}")

sc.on('message', on_msg)
print("Loading script...")
sc.load()
print("Waiting 20 seconds for card activity...")

try:
    for i in range(20):
        time.sleep(1)
        if i % 5 == 4:
            print(f"  ... {len(sprites)} unique sprites so far ({i+1}s)")
except KeyboardInterrupt:
    pass

print(f"\n=== RESULTS: {len(sprites)} unique sprites ===")
for s in sorted(sprite_log):
    print(f"  {s}")

sc.unload()
sess.detach()
