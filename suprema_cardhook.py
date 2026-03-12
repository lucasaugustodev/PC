"""Hook card display functions to capture card ID -> visual mapping"""
import frida, json, time, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

# Strategy: Hook SSL_read like before to capture traffic,
# AND simultaneously hook SpiderMonkey JS calls to intercept card rendering
# The client receives card IDs via network, then converts them to sprites
# We can hook the spriteFrame setter to see which card image is loaded for which ID

js = r'''
// Hook SSL_read to capture incoming card data
var mod = Process.findModuleByName("libssl-1_1.dll");
var ssl_read = mod.findExportByName("SSL_read");

// Also find SpiderMonkey functions for JS evaluation
var mozjs = Process.findModuleByName("mozjs-52.dll");
send({type: "info", msg: "Modules found", ssl: mod.base.toString(), mozjs: mozjs ? mozjs.base.toString() : "not found"});

// Search for card-related strings being set as spriteFrame
// In cocos2d-x, cards are displayed as sprites with specific texture names
// The naming convention is usually like: "card_X.png" or "poker_X.png"

// Hook cc.Sprite.setSpriteFrame to see all sprite changes
var libcocos = Process.findModuleByName("libcocos2d.dll");
send({type: "info", msg: "libcocos2d: " + (libcocos ? libcocos.base.toString() : "not found")});

// Let's search for the actual card sprite loading pattern in memory
// The game uses card_XX format or similar for textures
// By monitoring texture/sprite loads we can correlate card IDs with images

// Alternative: Hook the JS eval/call mechanism
// SpiderMonkey's JS_CallFunction or JS::Call
if (mozjs) {
    // Look for JS_EvaluateScript, JS_CallFunctionName, etc.
    var exports = mozjs.enumerateExports();
    var cardRelated = [];
    for (var i = 0; i < exports.length; i++) {
        var name = exports[i].name;
        if (name.indexOf("Call") !== -1 || name.indexOf("Eval") !== -1 ||
            name.indexOf("Execute") !== -1 || name.indexOf("Invoke") !== -1) {
            cardRelated.push({name: name, addr: exports[i].address.toString()});
        }
    }
    send({type: "mozjs_exports", count: cardRelated.length, items: cardRelated.slice(0, 30)});

    // Also look for exports with "Property" in the name
    var propExports = [];
    for (var i = 0; i < exports.length; i++) {
        var name = exports[i].name;
        if (name.indexOf("SetProperty") !== -1 || name.indexOf("GetProperty") !== -1) {
            propExports.push({name: name, addr: exports[i].address.toString()});
        }
    }
    send({type: "mozjs_property_exports", count: propExports.length, items: propExports.slice(0, 20)});
}

// Also check libcocos2d exports for sprite-related functions
if (libcocos) {
    var cocosExports = libcocos.enumerateExports();
    var spriteExports = [];
    for (var i = 0; i < cocosExports.length; i++) {
        var name = cocosExports[i].name;
        if (name.indexOf("SpriteFrame") !== -1 && name.indexOf("set") !== -1) {
            spriteExports.push({name: name, addr: cocosExports[i].address.toString()});
        }
    }
    send({type: "cocos_sprite_exports", count: spriteExports.length, items: spriteExports.slice(0, 20)});
}

send({type: "done"});
'''

sc = sess.create_script(js)
def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('type', '?')
        if t == 'info':
            print(f'[INFO] {p["msg"]}')
        elif t in ('mozjs_exports', 'mozjs_property_exports', 'cocos_sprite_exports'):
            print(f'\n[{t}] {p["count"]} found:')
            for item in p.get('items', []):
                print(f'  {item["name"]} @ {item["addr"]}')
        elif t == 'done':
            print('\nDone scanning exports.')
        else:
            print(json.dumps(p, indent=2))
    elif msg['type'] == 'error':
        print(f'ERROR: {msg["description"]}')

sc.on('message', on_msg)
sc.load()
time.sleep(5)
sc.unload()
sess.detach()
