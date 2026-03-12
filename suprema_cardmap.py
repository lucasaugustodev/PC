"""Hook card sprite loading to map card_id -> visual card name.
Also capture SSL traffic to correlate card_ids from protocol with visual sprites."""
import frida, json, time, sys, threading
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

js = r'''
var libcocos = Process.findModuleByName("libcocos2d.dll");
var exps = libcocos.enumerateExports();

// Find all SpriteFrame and Texture related exports
var spriteExports = [];
var allCardRelated = [];
for (var i = 0; i < exps.length; i++) {
    var n = exps[i].name;
    if (n.indexOf('getSpriteFrameByName') !== -1 ||
        n.indexOf('addSpriteFrame') !== -1 ||
        n.indexOf('setSpriteFrame') !== -1 ||
        n.indexOf('createWithSpriteFrameName') !== -1 ||
        n.indexOf('initWithSpriteFrameName') !== -1 ||
        n.indexOf('setDisplayFrameWithAnimationName') !== -1 ||
        n.indexOf('setTextureWithRect') !== -1 ||
        n.indexOf('addImage') !== -1) {
        spriteExports.push({name: n, addr: exps[i].address.toString()});
    }
}
send({t: "sprite_exports", count: spriteExports.length, items: spriteExports});

// Hook getSpriteFrameByName - this is called when the game loads a card sprite
for (var i = 0; i < spriteExports.length; i++) {
    var exp = spriteExports[i];
    if (exp.name.indexOf('getSpriteFrameByName') !== -1) {
        try {
            Interceptor.attach(ptr(exp.addr), {
                onEnter: function(args) {
                    // arg0 = this (SpriteFrameCache), arg1 = std::string& or const char*
                    // For MSVC std::string, try reading as pointer to string data
                    try {
                        // Try reading as const char* first
                        var name = args[1].readUtf8String();
                        if (name && name.indexOf('card') !== -1) {
                            send({t: "sprite_get", name: name, fn: "getSpriteFrameByName"});
                        }
                    } catch(e) {
                        // Try reading as std::string (MSVC layout)
                        try {
                            var strObj = args[1];
                            var len = strObj.add(16).readU32();
                            var cap = strObj.add(20).readU32();
                            var strData;
                            if (cap >= 16) {
                                strData = strObj.readPointer().readUtf8String(len);
                            } else {
                                strData = strObj.readUtf8String(len);
                            }
                            if (strData && strData.indexOf('card') !== -1) {
                                send({t: "sprite_get", name: strData, fn: "getSpriteFrameByName"});
                            }
                        } catch(e2) {}
                    }
                }
            });
            send({t: "hooked", fn: exp.name});
        } catch(e) {
            send({t: "hook_err", fn: exp.name, err: e.toString()});
        }
    }
}

// Hook initWithSpriteFrameName - called when creating a Sprite with a frame name
for (var i = 0; i < spriteExports.length; i++) {
    var exp = spriteExports[i];
    if (exp.name.indexOf('initWithSpriteFrameName') !== -1) {
        try {
            Interceptor.attach(ptr(exp.addr), {
                onEnter: function(args) {
                    try {
                        var name = args[1].readUtf8String();
                        if (name && (name.indexOf('card') !== -1 || name.indexOf('poker') !== -1 ||
                            name.indexOf('suit') !== -1 || name.indexOf('rank') !== -1)) {
                            send({t: "sprite_init", name: name, fn: "initWithSpriteFrameName"});
                        }
                    } catch(e) {
                        try {
                            var strObj = args[1];
                            var len = strObj.add(16).readU32();
                            var cap = strObj.add(20).readU32();
                            var strData;
                            if (cap >= 16) {
                                strData = strObj.readPointer().readUtf8String(len);
                            } else {
                                strData = strObj.readUtf8String(len);
                            }
                            if (strData && (strData.indexOf('card') !== -1 || strData.indexOf('poker') !== -1)) {
                                send({t: "sprite_init", name: strData, fn: "initWithSpriteFrameName"});
                            }
                        } catch(e2) {}
                    }
                }
            });
            send({t: "hooked", fn: exp.name});
        } catch(e) {
            send({t: "hook_err", fn: exp.name, err: e.toString()});
        }
    }
}

// Hook TextureCache::addImage to see all textures loaded
for (var i = 0; i < spriteExports.length; i++) {
    var exp = spriteExports[i];
    if (exp.name.indexOf('addImage') !== -1 && exp.name.indexOf('Texture') !== -1) {
        try {
            Interceptor.attach(ptr(exp.addr), {
                onEnter: function(args) {
                    try {
                        var name = args[1].readUtf8String();
                        if (name && (name.indexOf('card') !== -1 || name.indexOf('poker') !== -1 ||
                            name.indexOf('pai') !== -1 || name.indexOf('poke') !== -1)) {
                            send({t: "texture_add", name: name, fn: "addImage"});
                        }
                    } catch(e) {}
                }
            });
            send({t: "hooked", fn: exp.name});
        } catch(e) {
            send({t: "hook_err", fn: exp.name, err: e.toString()});
        }
    }
}

// Also hook SSL to capture card_ids from protocol messages
var sslmod = Process.findModuleByName("libssl-1_1.dll");
var ssl_read = sslmod.findExportByName("SSL_read");
Interceptor.attach(ssl_read, {
    onEnter: function(args) { this.buf = args[1]; },
    onLeave: function(retval) {
        var n = retval.toInt32();
        if (n > 0) { send({t: "ssl", s: n}, this.buf.readByteArray(n)); }
    }
});

send({t: "ready"});
'''

sc = sess.create_script(js)
card_sprites = []
ssl_msgs = []
running = True

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t == 'sprite_exports':
            print(f'Sprite exports found: {p["count"]}')
            for item in p['items']:
                print(f'  {item["name"]} @ {item["addr"]}')
        elif t == 'hooked':
            print(f'HOOKED: {p["fn"]}')
        elif t == 'hook_err':
            print(f'Hook error on {p["fn"]}: {p["err"]}')
        elif t in ('sprite_get', 'sprite_init', 'texture_add'):
            print(f'*** CARD SPRITE: {p["name"]} (via {p["fn"]}) ***')
            card_sprites.append(p['name'])
        elif t == 'ssl':
            # Quick parse for card-related data
            if data and len(data) > 4:
                # Look for pomelo data packets (type 4)
                if data[0] == 4 or (len(data) > 4 and data[0] & 0xF0 == 0x40):
                    pass  # Will process below
        elif t == 'ready':
            print('Ready - waiting for card actions...')
            print('Play a hand or navigate to see card sprites loaded.')
        else:
            print(json.dumps(p, indent=2))
    elif msg['type'] == 'error':
        print(f'ERR: {msg["description"]}')

sc.on('message', on_msg)
sc.load()
print("Monitoring card sprites and SSL traffic...")
print("Press Ctrl+C to stop and see results.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

print(f"\nCollected {len(card_sprites)} card sprite references")
for s in card_sprites:
    print(f"  {s}")

sc.unload()
sess.detach()
