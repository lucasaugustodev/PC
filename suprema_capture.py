"""Capture SSL traffic with full pomelo parsing + hook setTextureRect"""
import frida, json, time, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sess = frida.attach(100628)

js = r'''
try {
    // Hook SSL to capture traffic with full data
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    var ssl_read = sslmod.findExportByName("SSL_read");
    Interceptor.attach(ssl_read, {
        onEnter: function(args) { this.buf = args[1]; },
        onLeave: function(retval) {
            var n = retval.toInt32();
            if (n > 0) send({t:"ssl",s:n}, this.buf.readByteArray(n));
        }
    });
    
    // Hook setTextureRect to see card atlas coords
    var libcocos = Process.findModuleByName("libcocos2d.dll");
    var exps = libcocos.enumerateExports();
    
    // setTextureRect(Rect, bool, Size) - the 3-arg version
    for (var i = 0; i < exps.length; i++) {
        var n = exps[i].name;
        // ?setTextureRect@Sprite@cocos2d@@UAEXABVRect@2@_NABVSize@2@@Z
        if (n.indexOf('setTextureRect') !== -1 && n.indexOf('Sprite@cocos2d') !== -1 && n.indexOf('_N') !== -1) {
            Interceptor.attach(exps[i].address, {
                onEnter: function(args) {
                    // args[0] = this, args[1] = const Rect& {x,y,w,h as floats}
                    try {
                        var rectPtr = args[1];
                        var x = rectPtr.readFloat();
                        var y = rectPtr.add(4).readFloat();
                        var w = rectPtr.add(8).readFloat();
                        var h = rectPtr.add(12).readFloat();
                        // Only log card-sized rects (typical card = ~80x110 or similar)
                        if (w > 30 && w < 200 && h > 40 && h < 300) {
                            send({t:"rect", x:x, y:y, w:w, h:h});
                        }
                    } catch(e) {}
                }
            });
            send({t:"info", m:"Hooked setTextureRect: " + n});
            break;
        }
    }
    
    send({t:"ready"});
} catch(e) {
    send({t:"fatal",e:e.toString()});
}
'''

sc = sess.create_script(js)
f = open("C:/Users/PC/suprema_capture_out.txt", "w", encoding="utf-8")

def log(s):
    print(s, flush=True)
    f.write(s + "\n")
    f.flush()

def parse_pomelo(d):
    if len(d) < 5 or d[0] != 4:
        return None
    try:
        import msgpack
        body_len = (d[1] << 16) | (d[2] << 8) | d[3]
        body = d[4:4+body_len]
        if len(body) < 1:
            return None
        flag = body[0]
        mt = (flag >> 1) & 0x07
        off = 1
        msg_id = 0
        if mt in (0,1):
            while off < len(body):
                b = body[off]; off += 1
                msg_id = (msg_id << 7) | (b & 0x7F)
                if not (b & 0x80): break
        route = ""
        if mt in (0,2):
            if flag & 1:
                if off+2 <= len(body):
                    route = f"route#{(body[off]<<8)|body[off+1]}"
                    off += 2
            else:
                if off < len(body):
                    rlen = body[off]; off += 1
                    route = body[off:off+rlen].decode('ascii','replace')
                    off += rlen
        payload = msgpack.unpackb(body[off:], raw=False)
        return {"route": route, "id": msg_id, "payload": payload}
    except:
        return None

rect_log = []
seen_rects = set()

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t','')
        if t in ('info','ready','fatal'):
            log(f"[{t}] {p.get('m',p.get('e',''))}")
        elif t == 'rect':
            key = (round(p['x']), round(p['y']), round(p['w']), round(p['h']))
            if key not in seen_rects:
                seen_rects.add(key)
                rect_log.append(key)
                log(f"[RECT] x={p['x']:.0f} y={p['y']:.0f} w={p['w']:.0f} h={p['h']:.0f}")
        elif t == 'ssl':
            if data:
                d = bytes(data)
                parsed = parse_pomelo(d)
                if parsed:
                    pl = parsed['payload']
                    route = parsed['route']
                    if isinstance(pl, dict):
                        interesting = False
                        for key in ['cards','handCards','lightcards','publicCards','boardCards',
                                    'curCards','gamestage','stage','gameover','showCards']:
                            if key in pl:
                                interesting = True
                        if interesting:
                            log(f"[MSG] route={route} keys={list(pl.keys())}")
                            for key in ['cards','handCards','lightcards','publicCards','boardCards',
                                        'curCards','showCards']:
                                if key in pl:
                                    log(f"  {key} = {pl[key]}")
                            for key in ['gamestage','stage']:
                                if key in pl:
                                    log(f"  {key} = {pl[key]}")
    elif msg['type'] == 'error':
        log(f"[ERR] {msg['description']}")

sc.on('message', on_msg)
sc.load()
log("Capturing for 60 seconds...")
try:
    for i in range(60):
        time.sleep(1)
        if i % 15 == 14:
            log(f"  ...{i+1}s, rects={len(rect_log)}")
except KeyboardInterrupt:
    pass

log(f"\nTotal unique rects: {len(rect_log)}")
log(f"Rects: {rect_log}")
f.close()
sc.unload()
sess.detach()
