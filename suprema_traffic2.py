"""Capture ALL pomelo messages with full payload to build card mapping"""
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
        if (n > 0) send({t:"d",s:n}, this.buf.readByteArray(n));
    }
});
send({t:"ready"});
'''

sc = sess.create_script(js)
f = open("C:/Users/PC/suprema_traffic2.log", "w", encoding="utf-8")
msg_count = 0

def log(s):
    print(s, flush=True)
    f.write(s + "\n")
    f.flush()

def on_msg(msg, data):
    global msg_count
    if msg['type'] != 'send': return
    p = msg['payload']
    if p.get('t') == 'ready':
        log("READY - capturing all traffic")
        return
    if not data or len(data) < 5: return
    d = bytes(data)
    if d[0] != 4: return  # only pomelo data packets
    
    try:
        body_len = (d[1]<<16)|(d[2]<<8)|d[3]
        body = d[4:4+body_len]
        if len(body) < 1: return
        flag = body[0]
        mt = (flag>>1) & 0x07
        off = 1
        msg_id = 0
        if mt in (0,1):
            while off < len(body):
                b = body[off]; off += 1
                msg_id = (msg_id<<7)|(b&0x7F)
                if not (b&0x80): break
        route = ""
        if mt in (0,2):
            if flag & 1:
                route = f"r#{(body[off]<<8)|body[off+1]}"
                off += 2
            else:
                rlen = body[off]; off += 1
                route = body[off:off+rlen].decode('ascii','replace')
                off += rlen
        
        payload = msgpack.unpackb(body[off:], raw=False)
        msg_count += 1
        
        if isinstance(payload, dict):
            keys = list(payload.keys())
            # Log everything game-related
            log(f"\n[#{msg_count}] route={route} id={msg_id} keys={keys}")
            for k, v in payload.items():
                if isinstance(v, (list, dict)) or k in ['cards','handCards','lightcards','publicCards',
                    'boardCards','curCards','showCards','gamestage','stage','handid','gameover',
                    'winners','seat','chip','cardtype','handType','bestCards']:
                    log(f"  {k} = {json.dumps(v, ensure_ascii=False)}")
    except:
        pass

sc.on('message', on_msg)
sc.load()
log(f"Capturing... PID=100628")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
f.close()
sc.unload()
sess.detach()
