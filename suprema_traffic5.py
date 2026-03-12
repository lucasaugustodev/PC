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
        if (n > 10) send({s:n}, this.buf.readByteArray(n));
    }
});
send("ready");
'''

sc = sess.create_script(js)
f = open("C:/Users/PC/suprema_traffic5.log", "w", encoding="utf-8")
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
        if d[0] != 0x82: return  # WS binary frame
        
        # Parse WS length
        b1 = d[1]
        ws_len = b1 & 0x7F
        ws_off = 2
        if ws_len == 126:
            ws_len = (d[2]<<8)|d[3]
            ws_off = 4
        
        ws_payload = d[ws_off:]
        
        # Pomelo: type(1) + length(3)
        ptype = ws_payload[0]
        if ptype != 4: return
        plen = (ws_payload[1]<<16)|(ws_payload[2]<<8)|ws_payload[3]
        pbody = ws_payload[4:4+plen]
        
        # The body is PURE msgpack - no pomelo flag/route header
        try:
            parsed = msgpack.unpackb(pbody, raw=False)
            count += 1
        except:
            return
        
        if not isinstance(parsed, dict):
            return
        
        event = parsed.get('event', '')
        data_field = parsed.get('data', {})
        
        # Log all messages with their event type
        s = json.dumps(parsed, ensure_ascii=False, default=str)
        
        # Always log event type
        if event:
            # Check if card-related
            if any(k in s for k in ['cards','Cards','handCards','lightcards','dealcard',
                                      'gamestage','game_stage','gameover','game_over',
                                      'showCards','cardtype','bestCards','dealCards',
                                      'handType','hand_id','handid']):
                log(f"\n=== [{count}] EVENT: {event} ===")
                log(json.dumps(parsed, indent=2, ensure_ascii=False, default=str)[:3000])
            else:
                log(f"[{count}] event={event}")
        else:
            # Response or other
            keys = list(parsed.keys())
            if any(k in s for k in ['cards','Cards']):
                log(f"\n=== [{count}] RESPONSE keys={keys} ===")
                log(json.dumps(parsed, indent=2, ensure_ascii=False, default=str)[:3000])

sc.on('message', on_msg)
sc.load()
log("Capturing (pure msgpack body)...")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
f.close()
sc.unload()
sess.detach()
