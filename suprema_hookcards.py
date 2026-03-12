"""Hook Sprite::setSpriteFrame(string) and getSpriteFrameByName to capture card textures.
MSVC std::string layout: if capacity < 16, data is inline (SSO buffer);
if capacity >= 16, first 4 bytes = pointer to heap data.
Size at offset +16, capacity at offset +20."""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

js = r'''
var libcocos = Process.findModuleByName("libcocos2d.dll");

// Sprite::setSpriteFrame(const std::string&) - takes string name
var setSF = libcocos.findExportByName(
    "?setSpriteFrame@Sprite@cocos2d@@UAEXABV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@@Z"
);

// SpriteFrameCache::getSpriteFrameByName(const std::string&)
var getSFBN = libcocos.findExportByName(
    "?getSpriteFrameByName@SpriteFrameCache@cocos2d@@QAEPAVSpriteFrame@2@ABV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@@Z"
);

// Scale9SpriteV2::setSpriteFrame(const std::string&) - creator namespace
var setSF2 = libcocos.findExportByName(
    "?setSpriteFrame@Scale9SpriteV2@creator@@QAE_NABV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@@Z"
);

function readStdString(strPtr) {
    // MSVC std::string: 16 bytes SSO buffer, then size (u32), then capacity (u32)
    var size = strPtr.add(16).readU32();
    var cap = strPtr.add(20).readU32();
    if (size === 0) return "";
    if (cap >= 16) {
        // Heap allocated - first pointer is data ptr
        return strPtr.readPointer().readUtf8String(size);
    } else {
        // SSO - data is inline in the first 16 bytes
        return strPtr.readUtf8String(size);
    }
}

var seen = {};

if (setSF) {
    Interceptor.attach(setSF, {
        onEnter: function(args) {
            try {
                var name = readStdString(args[1]);
                if (name && !seen[name]) {
                    seen[name] = true;
                    send({t: "set_sf", name: name});
                }
            } catch(e) {}
        }
    });
    send({t: "hooked", fn: "Sprite::setSpriteFrame(string)", addr: setSF.toString()});
} else {
    send({t: "not_found", fn: "Sprite::setSpriteFrame(string)"});
}

if (getSFBN) {
    Interceptor.attach(getSFBN, {
        onEnter: function(args) {
            try {
                var name = readStdString(args[1]);
                if (name && !seen['g_'+name]) {
                    seen['g_'+name] = true;
                    send({t: "get_sf", name: name});
                }
            } catch(e) {}
        }
    });
    send({t: "hooked", fn: "getSpriteFrameByName", addr: getSFBN.toString()});
} else {
    send({t: "not_found", fn: "getSpriteFrameByName"});
}

if (setSF2) {
    Interceptor.attach(setSF2, {
        onEnter: function(args) {
            try {
                var name = readStdString(args[1]);
                if (name && !seen['s2_'+name]) {
                    seen['s2_'+name] = true;
                    send({t: "set_sf2", name: name});
                }
            } catch(e) {}
        }
    });
    send({t: "hooked", fn: "Scale9SpriteV2::setSpriteFrame", addr: setSF2.toString()});
}

send({t: "ready"});
'''

sc = sess.create_script(js)
all_sprites = []

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t == 'hooked':
            print(f"[OK] Hooked {p['fn']} @ {p['addr']}")
        elif t == 'not_found':
            print(f"[!!] Not found: {p['fn']}")
        elif t in ('set_sf', 'get_sf', 'set_sf2'):
            name = p['name']
            all_sprites.append(name)
            print(f"[{t}] {name}")
        elif t == 'ready':
            print("Ready - play a hand to see card sprites!")
        else:
            print(json.dumps(p))
    elif msg['type'] == 'error':
        print(f"ERR: {msg['description']}")

sc.on('message', on_msg)
sc.load()
print("Monitoring... press Ctrl+C to stop")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

print(f"\nTotal unique sprites seen: {len(all_sprites)}")
sc.unload()
sess.detach()
