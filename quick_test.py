"""Quick test - inject and save raw bytes for analysis."""
import frida, json, time, sys, os, msgpack, subprocess, threading, random
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

lock = threading.Lock()
raw_recv = []

r = subprocess.check_output(
    'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
    shell=True, text=True).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]

JS = r'''
try {
    var s = Process.findModuleByName("libssl-1_1.dll");
    var wfn = new NativeFunction(s.findExportByName("SSL_write"), 'int', ['pointer', 'pointer', 'int']);
    var g = null;
    Interceptor.attach(s.findExportByName("SSL_read"), {
        onEnter: function(a) { this.ssl=a[0]; this.buf=a[1]; },
        onLeave: function(r) {
            var n=r.toInt32(); if(n>0) {
                var b0 = this.buf.readU8();
                if(b0===0x82||b0===3||b0===4||b0===2||b0===1) g=this.ssl;
                send({d:"R"}, this.buf.readByteArray(n));
            }
        }
    });
    Interceptor.attach(s.findExportByName("SSL_write"), {
        onEnter: function(a) {
            this.ssl=a[0]; var n=a[2].toInt32(); if(n>0) {
                var b0=a[1].readU8();
                if(b0===0x82||b0===3||b0===4) g=this.ssl;
                send({d:"S"}, a[1].readByteArray(n));
            }
        }
    });
    rpc.exports = {
        inject: function(hex) {
            if(!g) return "NO_SSL";
            var d=[]; for(var i=0;i<hex.length;i+=2) d.push(parseInt(hex.substr(i,2),16));
            var b=Memory.alloc(d.length); b.writeByteArray(d);
            return "OK:"+wfn(g,b,d.length);
        }
    };
    send({t:"ready"});
} catch(e) { send({t:"fatal", e:e.toString()}); }
'''

sessions = []
active_sc = None
for pid in pids:
    try:
        sess = frida.attach(pid)
        sc = sess.create_script(JS)
        def make_cb(p):
            def cb(msg, data):
                if msg['type'] != 'send': return
                if msg['payload'].get('t') == 'ready': return
                if data and msg['payload'].get('d') == 'R':
                    with lock:
                        raw_recv.append((time.time(), bytes(data)))
            return cb
        sc.on('message', make_cb(pid))
        sc.load()
        sessions.append((sess, sc, pid))
    except:
        pass

time.sleep(2)
for s, sc, p in sessions:
    try:
        if sc.exports_sync.inject("03").startswith("OK"):
            active_sc = sc
            print(f"Active: PID {p}")
            break
    except:
        pass

# Clear and inject
with lock:
    raw_recv.clear()
ts = time.time()

body = json.dumps({
    "clubID": "14625", "unionID": 113, "myClubID": 41157, "myUnionID": 128,
    "roomID": "14625_43107012#113@41157%128",
    "privatecode": None, "ver": 7288, "lan": "pt", "verPackage": "5"
}).encode()
route = b'apiPlayer.playerHandler.joinGameRoom'
reqid = 500
inner = bytes([(reqid >> 8) & 0xFF, reqid & 0xFF, len(route)]) + route + body
plen = len(inner)
pomelo = bytes([4, (plen >> 16) & 0xFF, (plen >> 8) & 0xFF, plen & 0xFF]) + inner

f = bytearray([0x82])
pl = len(pomelo)
if pl < 126:
    f.append(0x80 | pl)
elif pl < 65536:
    f.append(0x80 | 126)
    f.extend(pl.to_bytes(2, 'big'))
m = bytes([random.randint(0, 255) for _ in range(4)])
f.extend(m)
mp = bytearray(pomelo)
for i in range(len(mp)):
    mp[i] ^= m[i % 4]
f.extend(mp)

r = active_sc.exports_sync.inject(bytes(f).hex())
print(f"Inject: {r}")
time.sleep(10)

with lock:
    chunks = [(t, d) for t, d in raw_recv if t > ts]
all_bytes = b''.join([d for t, d in chunks])
print(f"Chunks: {len(chunks)}, Total bytes: {len(all_bytes)}")

# Save
with open(os.path.expanduser('~/inject_raw2.bin'), 'wb') as fw:
    fw.write(all_bytes)

# Analysis
print(f"\ninitinfo at: {all_bytes.find(b'initinfo')}")
print(f"game_seat at: {all_bytes.find(b'game_seat')}")
print(f"displayID at: {all_bytes.find(b'displayID')}")
print(f"HTTP 101? {b'101 Switching' in all_bytes}")
crlf2 = b'\r\n\r\n'
print(f"HTTP end: {all_bytes.find(crlf2)}")

# Show first 200 bytes
print(f"\nFirst 100 bytes: {all_bytes[:100].hex()}")

# Try ASCII decode of first part
try:
    ascii_part = all_bytes[:500].decode('ascii', errors='replace')
    print(f"ASCII start: {ascii_part[:200]}")
except:
    pass

for s, sc, p in sessions:
    try: sc.unload()
    except: pass
    try: s.detach()
    except: pass
print("\nDone")
