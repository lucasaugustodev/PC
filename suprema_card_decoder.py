"""Auto card decoder - captures screenshots synchronized with card data"""
import frida, struct, subprocess, time, os, json, sys
from datetime import datetime
from PIL import ImageGrab

MY_UID = 588900
WIN_BBOX = (-542, 139, -74, 983)
DECODE_DIR = 'C:/Users/PC/suprema_decode'
os.makedirs(DECODE_DIR, exist_ok=True)

def read_msgpack(data, pos):
    if pos >= len(data): return None, pos
    b = data[pos]
    if b <= 0x7f: return b, pos+1
    if b >= 0xe0: return b-256, pos+1
    if 0xa0 <= b <= 0xbf:
        slen = b - 0xa0
        try: return data[pos+1:pos+1+slen].decode('utf-8','replace'), pos+1+slen
        except: return None, pos+1+slen
    if 0x90 <= b <= 0x9f:
        count = b - 0x90; arr = []; p = pos+1
        for _ in range(count):
            v, p = read_msgpack(data, p); arr.append(v)
        return arr, p
    if 0x80 <= b <= 0x8f:
        count = b - 0x80; d = {}; p = pos+1
        for _ in range(count):
            k, p = read_msgpack(data, p); v, p = read_msgpack(data, p)
            if k is not None: d[str(k)] = v
        return d, p
    if b == 0xc0: return None, pos+1
    if b == 0xc2: return False, pos+1
    if b == 0xc3: return True, pos+1
    if b == 0xcc and pos+1 < len(data): return data[pos+1], pos+2
    if b == 0xcd and pos+2 < len(data): return (data[pos+1]<<8)|data[pos+2], pos+3
    if b == 0xce and pos+4 < len(data):
        return (data[pos+1]<<24)|(data[pos+2]<<16)|(data[pos+3]<<8)|data[pos+4], pos+5
    if b == 0xcf and pos+8 < len(data):
        return int.from_bytes(data[pos+1:pos+9], 'big'), pos+9
    if b == 0xd0 and pos+1 < len(data):
        v = data[pos+1]; return (v-256 if v>=128 else v), pos+2
    if b == 0xd1 and pos+2 < len(data):
        v = (data[pos+1]<<8)|data[pos+2]; return (v-65536 if v>=32768 else v), pos+3
    if b == 0xd2 and pos+4 < len(data):
        v = (data[pos+1]<<24)|(data[pos+2]<<16)|(data[pos+3]<<8)|data[pos+4]
        return (v - 0x100000000 if v >= 0x80000000 else v), pos+5
    if b == 0xd9 and pos+1 < len(data):
        slen = data[pos+1]
        try: return data[pos+2:pos+2+slen].decode('utf-8','replace'), pos+2+slen
        except: return None, pos+2+slen
    if b == 0xda and pos+2 < len(data):
        slen = (data[pos+1]<<8)|data[pos+2]
        try: return data[pos+3:pos+3+slen].decode('utf-8','replace'), pos+3+slen
        except: return None, pos+3+slen
    if b == 0xdc and pos+2 < len(data):
        count = (data[pos+1]<<8)|data[pos+2]; arr = []; p = pos+3
        for _ in range(min(count,500)):
            v, p = read_msgpack(data, p); arr.append(v)
        return arr, p
    if b == 0xde and pos+2 < len(data):
        count = (data[pos+1]<<8)|data[pos+2]; d = {}; p = pos+3
        for _ in range(min(count,500)):
            k, p = read_msgpack(data, p); v, p = read_msgpack(data, p)
            if k is not None: d[str(k)] = v
        return d, p
    if b == 0xcb and pos+8 < len(data):
        return struct.unpack('>d', data[pos+1:pos+9])[0], pos+9
    if b == 0xca and pos+4 < len(data):
        return struct.unpack('>f', data[pos+1:pos+5])[0], pos+5
    return None, pos+1

def find_pid():
    out = subprocess.check_output(
        ['tasklist', '/FI', 'IMAGENAME eq SupremaPoker.exe', '/FO', 'CSV', '/NH'], text=True)
    for line in out.strip().split('\n'):
        if 'SupremaPoker' in line:
            return int(line.strip('"').split('","')[1])
    return None

def screenshot(name):
    try:
        img = ImageGrab.grab(bbox=WIN_BBOX, all_screens=True)
        path = f'{DECODE_DIR}/{name}'
        img.save(path)
        return name
    except Exception as e:
        return f'err:{e}'

pid = find_pid()
if not pid:
    print("No SupremaPoker"); sys.exit(1)

print(f"PID {pid}", flush=True)

FRIDA_JS = """
var mod = Process.findModuleByName("libssl-1_1.dll");
var fn = mod.findExportByName("SSL_read");
Interceptor.attach(fn, {
    onEnter: function(args) { this.buf = args[1]; },
    onLeave: function(retval) {
        var n = retval.toInt32();
        if (n > 0) { send({s: n}, this.buf.readByteArray(n)); }
    }
});
send({ok: 1});
"""

hands = []
cur = {'cards': None, 'board': [], 'seq': 0}

sess = frida.attach(pid)
sc = sess.create_script(FRIDA_JS)

def on_msg(message, data):
    if message['type'] != 'send': return
    p = message['payload']
    if 'ok' in p:
        print('Hooks active - waiting for cards...', flush=True)
        return
    if data is None: return

    raw = bytes(data)
    if len(raw) < 6: return
    b0 = raw[0]; b1 = raw[1]
    opcode = b0 & 0x0f
    plen = b1 & 0x7f; hdr = 2
    if plen == 126 and len(raw) >= 4:
        plen = (raw[2]<<8)|raw[3]; hdr = 4
    elif plen == 127 and len(raw) >= 10:
        plen = int.from_bytes(raw[2:10], 'big'); hdr = 10
    payload = raw[hdr:]
    if opcode not in (1, 2) or len(payload) < 5: return

    pkg_type = payload[0]
    if pkg_type != 4: return
    pkg_len = (payload[1]<<16)|(payload[2]<<8)|payload[3]
    body = payload[4:4+pkg_len]
    if not body: return

    flag = body[0]; mt = (flag>>1)&7; comp = flag&1; bp = 1
    if mt in (0,2):
        while bp < len(body):
            b = body[bp]; bp += 1
            if b < 128: break
    if mt in (0,1,3):
        if comp and bp+1 < len(body): bp += 2
        elif bp < len(body):
            rl = body[bp]; bp += 1; bp += rl
    if bp >= len(body): return

    try:
        decoded, _ = read_msgpack(body, bp)
    except:
        return
    if not isinstance(decoded, dict): return

    d = decoded.get('data', decoded)
    if not isinstance(d, dict): return
    ts = datetime.now().strftime('%H:%M:%S')
    seq = d.get('seqno', decoded.get('seqno', 0))

    # My cards
    gs = d.get('game_seat', {})
    my = gs.get(str(MY_UID), gs.get(MY_UID, {}))
    if isinstance(my, dict):
        cards = my.get('cards')
        pat = my.get('pattern', '')
        if isinstance(cards, list) and any(isinstance(c, int) and c > 0 for c in cards):
            if cards != cur['cards'] or seq != cur['seq']:
                cur['cards'] = cards
                cur['seq'] = seq
                cur['board'] = []
                time.sleep(0.4)
                fn = screenshot(f'h{seq}_deal_{cards[0]}_{cards[1]}.png')
                print(f'[{ts}] DEAL #{seq} cards={cards} pat="{pat}" -> {fn}', flush=True)
                hands.append({'h': seq, 'cards': cards, 'pat': pat, 'board': [], 't': ts})

    # Board changes
    gi = d.get('game_info', {})
    if isinstance(gi, dict):
        sc = gi.get('shared_cards', [])
        if isinstance(sc, list) and len(sc) >= 3 and any(isinstance(c, int) and c > 0 for c in sc):
            if sc != cur['board'] and seq == cur['seq'] and len(sc) != len(cur['board']):
                cur['board'] = sc
                stage = {3:'flop', 4:'turn', 5:'river'}.get(len(sc), 'board')
                time.sleep(0.4)
                fn = screenshot(f'h{seq}_{stage}_{"_".join(str(c) for c in sc)}.png')
                print(f'[{ts}] {stage.upper()} #{seq} board={sc} -> {fn}', flush=True)
                for h in reversed(hands):
                    if h['h'] == seq:
                        h['board'] = sc
                        break

    # Showdown
    gr = d.get('game_result', {})
    if isinstance(gr, dict) and 'seats' in gr:
        seats = gr.get('seats', {})
        board = gr.get('cards', [])
        revealed = {}
        if isinstance(seats, dict):
            for uid, s in seats.items():
                if isinstance(s, dict):
                    c = s.get('cards', [])
                    if isinstance(c, list) and any(isinstance(x, int) and x > 0 for x in c):
                        revealed[uid] = c
        if revealed:
            time.sleep(0.5)
            fn = screenshot(f'h{seq}_showdown.png')
            print(f'[{ts}] SHOWDOWN #{seq} board={board} -> {fn}', flush=True)
            for uid, c in revealed.items():
                me = ' <<ME' if str(uid) == str(MY_UID) else ''
                print(f'  uid={uid} cards={c}{me}', flush=True)

sc.on('message', on_msg)
sc.load()

print(f'\nAuto-capturing to {DECODE_DIR}/', flush=True)
print('Ctrl+C to stop\n', flush=True)

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
finally:
    with open(f'{DECODE_DIR}/hands.json', 'w') as f:
        json.dump(hands, f, indent=2)
    print(f'\nSaved {len(hands)} hands to hands.json', flush=True)
    try:
        sc.unload(); sess.detach()
    except:
        pass
