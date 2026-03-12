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
f = open("C:/Users/PC/suprema_traffic4.log", "w", encoding="utf-8")
count = 0

def log(s):
    f.write(s + "\n")
    f.flush()
    print(s, flush=True)

def on_msg(msg, data):
    global count
    if msg['type'] == 'send':
        if msg['payload'] == 'ready':
            log("READY")
            return
        if not data: return
        d = bytes(data)
        count += 1
        
        # WebSocket frame: byte0=opcode, byte1=length info
        # 0x82 = final frame, binary opcode (2)
        if d[0] != 0x82:
            return
        
        # Parse WS length
        b1 = d[1]
        mask = b1 & 0x80  # masking bit
        length = b1 & 0x7F
        off = 2
        if length == 126:
            length = (d[2]<<8)|d[3]
            off = 4
        elif length == 127:
            length = int.from_bytes(d[2:10], 'big')
            off = 10
        
        # If masked, read 4-byte mask key
        if mask:
            mask_key = d[off:off+4]
            off += 4
            # Unmask data
            payload = bytearray(d[off:off+length])
            for i in range(len(payload)):
                payload[i] ^= mask_key[i % 4]
        else:
            payload = d[off:off+length]
        
        if len(payload) < 4:
            return
        
        # Now this should be Pomelo protocol
        ptype = payload[0]
        if ptype != 4:  # data packet
            if ptype == 3:  # heartbeat
                return
            return
        
        plen = (payload[1]<<16)|(payload[2]<<8)|payload[3]
        body = bytes(payload[4:4+plen])
        
        if len(body) < 2:
            return
        
        flag = body[0]
        mt = (flag>>1) & 0x07
        off2 = 1
        msg_id = 0
        if mt in (0,1):  # request/response
            while off2 < len(body):
                b = body[off2]; off2 += 1
                msg_id = (msg_id<<7)|(b&0x7F)
                if not (b & 0x80): break
        route = ""
        if mt in (0,2):  # request/notify
            if flag & 1:  # compressed route
                if off2+2 <= len(body):
                    route = f"route#{(body[off2]<<8)|body[off2+1]}"
                    off2 += 2
            else:
                rlen = body[off2]; off2 += 1
                route = body[off2:off2+rlen].decode('ascii','replace')
                off2 += rlen
        
        try:
            pl = msgpack.unpackb(body[off2:], raw=False)
        except:
            return
        
        if not isinstance(pl, dict):
            return
        
        # Log ALL messages for analysis
        event = pl.get('event', route)
        data_field = pl.get('data', pl)
        
        # Check for card-related content recursively
        s = json.dumps(pl, ensure_ascii=False, default=str)
        if any(k in s for k in ['cards','handCards','lightcards','gamestage','game_stage',
                                  'gameover','game_over','handid','hand_id','showCards',
                                  'cardtype','handType','bestCards','dealCards']):
            log(f"\n=== [{count}] event={event} route={route} ===")
            log(json.dumps(pl, indent=2, ensure_ascii=False, default=str)[:2000])

sc.on('message', on_msg)
sc.load()
log("Capturing (WS+Pomelo+MsgPack)...")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
f.close()
sc.unload()
sess.detach()
