import frida, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import msgpack

sess = frida.attach(100628)

js = r'''
var sslmod = Process.findModuleByName("libssl-1_1.dll");
var ssl_read = sslmod.findExportByName("SSL_read");
var c = 0;
Interceptor.attach(ssl_read, {
    onEnter: function(args) { this.buf = args[1]; },
    onLeave: function(retval) {
        var n = retval.toInt32();
        if (n > 50 && c < 20) {
            c++;
            send({c:c,s:n}, this.buf.readByteArray(n));
        }
    }
});
send("ready");
'''

sc = sess.create_script(js)

def on_msg(msg, data):
    if msg['type'] == 'send':
        if msg['payload'] == 'ready':
            print("READY", flush=True)
            return
        p = msg['payload']
        d = bytes(data)
        print(f"\n=== Packet #{p['c']} ({p['s']}B) ===", flush=True)
        
        # It starts with 0x82 = WS binary frame
        # Parse WS
        b1 = d[1]
        ws_len = b1 & 0x7F
        ws_off = 2
        if ws_len == 126:
            ws_len = (d[2]<<8)|d[3]
            ws_off = 4
        elif ws_len == 127:
            ws_off = 10
        
        ws_payload = d[ws_off:]
        print(f"WS: len_field={ws_len} actual_payload={len(ws_payload)}B", flush=True)
        print(f"WS payload[0:4]: {ws_payload[:4].hex()}", flush=True)
        
        # Pomelo: type=payload[0], length=payload[1:4]
        ptype = ws_payload[0]
        plen = (ws_payload[1]<<16)|(ws_payload[2]<<8)|ws_payload[3]
        pbody = ws_payload[4:4+plen]
        print(f"Pomelo: type={ptype} body_len={plen}", flush=True)
        
        if ptype == 4 and len(pbody) > 1:
            flag = pbody[0]
            mt = (flag>>1) & 0x07
            off = 1
            msg_id = 0
            if mt in (0,1):
                while off < len(pbody):
                    b = pbody[off]; off += 1
                    msg_id = (msg_id<<7)|(b&0x7F)
                    if not (b&0x80): break
            route = ""
            if mt in (0,2):
                if flag & 1:
                    route = f"r#{(pbody[off]<<8)|pbody[off+1]}"
                    off += 2
                else:
                    rlen = pbody[off]; off += 1
                    route = pbody[off:off+rlen].decode('ascii','replace')
                    off += rlen
            
            mp_data = pbody[off:]
            print(f"Route: '{route}' msg_id={msg_id} msgpack_bytes={len(mp_data)}", flush=True)
            
            try:
                parsed = msgpack.unpackb(mp_data, raw=False)
                if isinstance(parsed, dict):
                    print(f"Keys: {list(parsed.keys())}", flush=True)
                    # Print interesting data
                    event = parsed.get('event', '')
                    if event:
                        print(f"Event: {event}", flush=True)
                    data_field = parsed.get('data', {})
                    if isinstance(data_field, dict):
                        for k in data_field:
                            v = data_field[k]
                            if isinstance(v, (int, str, float, bool)):
                                print(f"  data.{k} = {v}", flush=True)
                            elif isinstance(v, list) and len(v) < 20:
                                print(f"  data.{k} = {v}", flush=True)
                            elif isinstance(v, dict):
                                print(f"  data.{k} = dict({list(v.keys())[:10]})", flush=True)
                            else:
                                print(f"  data.{k} = ({type(v).__name__})", flush=True)
                else:
                    print(f"Parsed type: {type(parsed).__name__}", flush=True)
            except Exception as e:
                print(f"MsgPack error: {e}", flush=True)
                print(f"First 30 bytes: {mp_data[:30].hex()}", flush=True)

sc.on('message', on_msg)
sc.load()
for i in range(20):
    time.sleep(1)
sc.unload()
sess.detach()
