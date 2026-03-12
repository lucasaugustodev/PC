"""Hook Sprite::setSpriteFrame to capture card texture names + SSL_read for card data"""
import frida, json, time, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

js = r'''
var mod = Process.findModuleByName("libssl-1_1.dll");
var ssl_read = mod.findExportByName("SSL_read");

// Hook SSL_read for card data
Interceptor.attach(ssl_read, {
    onEnter: function(args) { this.buf = args[1]; },
    onLeave: function(retval) {
        var n = retval.toInt32();
        if (n > 0) { send({t: "ssl", s: n}, this.buf.readByteArray(n)); }
    }
});

// Now hook Sprite::setSpriteFrame in libcocos2d
// The setSpriteFrame function that's most relevant is on Sprite class
var libcocos = Process.findModuleByName("libcocos2d.dll");

// Search for Sprite::setSpriteFrame(SpriteFrame*)
// In the exports we didn't see it directly, but it's likely an overridden virtual
// Let's search for setSpriteFrame with string parameter (name-based loading)
// Actually, the JS binding calls cc.Sprite.spriteFrame = X which goes through
// the JS binding layer. Let me look for the JS binding function

// Search all exports for "Sprite" + "set"
var exports = libcocos.enumerateExports();
var spriteSetters = [];
for (var i = 0; i < exports.length; i++) {
    var name = exports[i].name;
    if (name.indexOf("Sprite") !== -1 &&
        (name.indexOf("setSpriteFrame") !== -1 || name.indexOf("setTexture") !== -1)) {
        spriteSetters.push({name: name, addr: exports[i].address});
    }
}
send({t: "sprite_setters", items: spriteSetters.map(function(s) { return s.name; })});

// Hook cc.loader.loadRes or cc.resources.load - the resource loading
// Actually, simpler: hook the Texture2D::initWithImage or the image file loading
// to capture when card textures are loaded

// Search for file loading functions
var fileExports = [];
for (var i = 0; i < exports.length; i++) {
    var name = exports[i].name;
    if ((name.indexOf("addImage") !== -1 || name.indexOf("loadImage") !== -1) &&
        name.indexOf("TextureCache") !== -1) {
        fileExports.push({name: name, addr: exports[i].address});
    }
}
send({t: "file_loaders", items: fileExports.map(function(s) { return s.name; })});

// Hook TextureCache::addImage to see all image loads
for (var i = 0; i < fileExports.length; i++) {
    if (fileExports[i].name.indexOf("addImage") !== -1 &&
        fileExports[i].name.indexOf("basic_string") !== -1) {
        (function(exp) {
            Interceptor.attach(exp.addr, {
                onEnter: function(args) {
                    try {
                        // args[1] is std::string* - read the string
                        // std::string layout: ptr, size, capacity (or SSO)
                        var strPtr = args[1];
                        // Try reading as C string from the pointer
                        var size = strPtr.add(4).readU32(); // size field
                        var dataPtr;
                        if (size <= 15) {
                            // SSO: data is inline
                            dataPtr = strPtr.add(4 + 4); // after size+capacity
                        } else {
                            dataPtr = strPtr.readPointer();
                        }
                        var str = dataPtr.readUtf8String(Math.min(size, 200));
                        if (str && str.indexOf("card") !== -1) {
                            send({t: "texture_load", file: str});
                        }
                    } catch(e) {
                        // Try another layout
                        try {
                            var str = args[1].readPointer().readUtf8String(100);
                            if (str && str.indexOf("card") !== -1) {
                                send({t: "texture_load2", file: str});
                            }
                        } catch(e2) {}
                    }
                }
            });
            send({t: "hooked", fn: exp.name});
        })(fileExports[i]);
    }
}

// Also search SpriteFrameCache for getSpriteFrameByName
var sfcExports = [];
for (var i = 0; i < exports.length; i++) {
    var name = exports[i].name;
    if (name.indexOf("SpriteFrame") !== -1 &&
        (name.indexOf("getSprite") !== -1 || name.indexOf("addSprite") !== -1)) {
        sfcExports.push({name: name, addr: exports[i].address});
    }
}
send({t: "sfc_exports", items: sfcExports.map(function(s) { return s.name; })});

// Hook getSpriteFrameByName
for (var i = 0; i < sfcExports.length; i++) {
    if (sfcExports[i].name.indexOf("getSpriteFrame") !== -1 &&
        sfcExports[i].name.indexOf("basic_string") !== -1) {
        (function(exp) {
            Interceptor.attach(exp.addr, {
                onEnter: function(args) {
                    try {
                        var strPtr = args[1];
                        var str;
                        try {
                            str = strPtr.readPointer().readUtf8String(100);
                        } catch(e) {
                            str = strPtr.add(8).readUtf8String(100);
                        }
                        if (str && (str.indexOf("card") !== -1 || str.indexOf("poker") !== -1)) {
                            send({t: "sprite_frame", name: str});
                        }
                    } catch(e) {}
                }
            });
            send({t: "hooked", fn: exp.name});
        })(sfcExports[i]);
    }
}

send({t: "ready"});
'''

sc = sess.create_script(js)

card_sprites = []
ssl_events = []

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t == 'ssl':
            pass  # ignore SSL for now
        elif t in ('texture_load', 'texture_load2'):
            print(f'[TEXTURE] {p.get("file", "?")}')
            card_sprites.append(p)
        elif t == 'sprite_frame':
            print(f'[SPRITE] {p.get("name", "?")}')
            card_sprites.append(p)
        elif t == 'ready':
            print('Hooks active! Waiting for card events...')
        elif t == 'hooked':
            print(f'  Hooked: {p["fn"]}')
        else:
            items = p.get('items', [])
            if items:
                print(f'[{t}] {len(items)}: {items[:10]}')
            else:
                print(f'[{t}]')
    elif msg['type'] == 'error':
        print(f'ERROR: {msg["description"]}')

sc.on('message', on_msg)
sc.load()

print('Monitoring for 60 seconds... Play a hand to trigger card sprites!')
time.sleep(60)

print(f'\nCaptured {len(card_sprites)} card sprite events')
for s in card_sprites:
    print(f'  {s}')

sc.unload()
sess.detach()
