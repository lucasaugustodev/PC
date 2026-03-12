import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import msgpack

sess = frida.attach(100628)

js = r'''
var sslmod = Process.findModuleByName("libssl-1_1.dll");
var ssl_read = sslmod.findExportByName("SSL_read");
Interceptor.attach(ssl_read, {
    onEnter: function(args) { this.buf = args[1]; },
    onLeave: function(retval) {
        var n = retval.toInt32();
        if (n > 0) send({s:n}, this.buf.readByteArray(n));
    }
});
send("ready");
'''

sc = sess.create_script(js)
f = open("C:/Users/PC/suprema_traffic3.log", "w", encoding="utf-8")
count = 0

def log(s):
    f.write(s + "\n")
    f.flush()
    print(s, flush=True)

def find_cards_recursive(obj, path=""):
    """Recursively search for card-related fields"""
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ('cards','handCards','lightcards','publicCards','boardCards',
                      'curCards','showCards','bestCards','handType','cardtype',
                      'gamestage','stage','handid','gameover','winners',
                      'game_stage','hand_id','game_over'):
                results.append((path+"."+k if path else k, v))
            if isinstance(v, (dict, list)):
                results.extend(find_cards_recursive(v, path+"."+k if path else k))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, (dict, list)):
                results.extend(find_cards_recursive(item, f"{path}[{i}]"))
    return results

def on_msg(msg, data):
    global count
    if msg['type'] == 'send':
        if msg['payload'] == 'ready':
            log("READY")
            return
        if not data: return
        d = bytes(data)
        try:
            # The outer layer is msgpack itself
            outer = msgpack.unpackb(d, raw=False)
            count += 1
            
            # Find event name and card data
            event = ""
            if isinstance(outer, dict):
                # Direct dict
                cards_found = find_cards_recursive(outer)
                if cards_found:
                    log(f"\n[#{count}] DICT: {list(outer.keys())[:5]}")
                    for path, val in cards_found:
                        log(f"  {path} = {json.dumps(val, ensure_ascii=False)}")
            elif isinstance(outer, list) and len(outer) >= 2:
                # Could be [type, payload] or [header, data]
                for item in outer:
                    if isinstance(item, (dict, list)):
                        cards_found = find_cards_recursive(item if isinstance(item, dict) else {"_": item})
                        if cards_found:
                            log(f"\n[#{count}] LIST item:")
                            for path, val in cards_found:
                                log(f"  {path} = {json.dumps(val, ensure_ascii=False)}")
            
            # Also try parsing the inner pomelo-like structure
            # First 2 bytes seem to be msgpack header, then pomelo
            if len(d) > 6 and d[2] == 0x04:  # pomelo type 4 = data
                plen = (d[3]<<16)|(d[4]<<8)|d[5]
                pbody = d[6:6+plen]
                if len(pbody) > 1:
                    flag = pbody[0]
                    mt = (flag>>1)&0x07
                    off = 1
                    if mt in (0,1):
                        while off < len(pbody):
                            b = pbody[off]; off += 1
                            if not (b&0x80): break
                    route = ""
                    if mt in (0,2):
                        if flag & 1:
                            off += 2
                        else:
                            rlen = pbody[off]; off += 1
                            route = pbody[off:off+rlen].decode('ascii','replace')
                            off += rlen
                    try:
                        inner = msgpack.unpackb(pbody[off:], raw=False)
                        cards_found = find_cards_recursive(inner)
                        if cards_found:
                            log(f"\n[#{count}] POMELO route={route}")
                            for path, val in cards_found:
                                log(f"  {path} = {json.dumps(val, ensure_ascii=False)}")
                    except: pass
        except: pass

sc.on('message', on_msg)
sc.load()
log("Capturing traffic...")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
f.close()
sc.unload()
sess.detach()
