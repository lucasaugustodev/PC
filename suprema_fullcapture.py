"""Full traffic capture - logs ALL events to file, highlights card data"""
import frida, json, time, sys, msgpack
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

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
f = open("C:/Users/PC/suprema_fullcapture.log", "w", encoding="utf-8")
count = 0
last_event = ""

def log(s):
    f.write(s + "\n")
    f.flush()

def on_msg(msg, data):
    global count, last_event
    if msg['type'] == 'send':
        if msg['payload'] == 'ready':
            log("READY"); print("READY", flush=True)
            return
        if not data: return
        d = bytes(data)
        if len(d) < 6 or d[0] != 0x82: return
        
        b1 = d[1]
        ws_off = 2
        if (b1 & 0x7F) == 126: ws_off = 4
        elif (b1 & 0x7F) == 127: ws_off = 10
        ws_payload = d[ws_off:]
        
        ptype = ws_payload[0]
        if ptype != 4: return
        plen = (ws_payload[1]<<16)|(ws_payload[2]<<8)|ws_payload[3]
        pbody = ws_payload[4:4+plen]
        if len(pbody) < 2: return
        
        msg_type = pbody[0]
        off = 1
        if msg_type in (4, 6):
            rlen = pbody[off]; off += 1
            route = pbody[off:off+rlen].decode('ascii','replace')
            off += rlen
        elif msg_type in (0, 2):
            rlen = pbody[off]; off += 1
            route = pbody[off:off+rlen].decode('ascii','replace')
            off += rlen
        else:
            route = f"type{msg_type}"
        
        try:
            parsed = msgpack.unpackb(pbody[off:], raw=False)
        except:
            return
        
        if not isinstance(parsed, dict): return
        count += 1
        
        event = parsed.get('event', route)
        
        # Skip repeated gameinfo flood
        if event == last_event == 'gameinfo':
            return
        last_event = event
        
        data_field = parsed.get('data', parsed)
        
        # Log everything
        log(f"\n[#{count}] {event}")
        log(json.dumps(parsed, ensure_ascii=False, default=str)[:5000])
        
        # Print important ones to console
        if event not in ('gameinfo', 'countdown', 'matchesStatusPushNotify',
                          'apiClub.clubHandler.jackpot', 'updategamer'):
            print(f"[#{count}] {event}", flush=True)
            if isinstance(data_field, dict):
                for k in ['cards','handCards','lightcards','publicCards','boardCards',
                           'shared_cards','showCards','bestCards','dealCards','curCards',
                           'gamestage','game_stage','hand_id','handid']:
                    if k in data_field:
                        print(f"  {k} = {data_field[k]}", flush=True)
                # Also check nested
                if 'game_info' in data_field:
                    gi = data_field['game_info']
                    if isinstance(gi, dict):
                        sc_val = gi.get('shared_cards', [])
                        if sc_val:
                            print(f"  shared_cards = {sc_val}", flush=True)

sc.on('message', on_msg)
sc.load()
log("Capturing all events...")
print("Capturing... play hands! Ctrl+C to stop", flush=True)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
f.close()
sc.unload()
sess.detach()
