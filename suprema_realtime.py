"""Real-time card decoder terminal for Suprema Poker."""
import frida, json, time, sys, os, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import msgpack
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'msgpack'])
    import msgpack

RANKS = '23456789TJQKA'
SUITS = ['c','d','h','s','x']

def decode(cid):
    if not cid or cid == 0:
        return '??'
    r = (cid - 2) % 16
    s = (cid - 2) // 16
    if 0 <= r < 13 and 0 <= s <= 4:
        return RANKS[r] + SUITS[s]
    return '?%d' % cid

def decode_list(cards):
    if not cards:
        return []
    return [decode(c) for c in cards if c and c != 0]

def find_pid():
    try:
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq SupremaPoker.exe', '/FO', 'CSV', '/NH'],
                           capture_output=True, text=True)
        for line in r.stdout.strip().split('\n'):
            if 'SupremaPoker' in line:
                parts = line.strip('"').split('","')
                return int(parts[1])
    except:
        pass
    return None

pid = find_pid()
if not pid:
    print("SupremaPoker.exe nao encontrado!")
    sys.exit(1)
print("Attaching to PID %d..." % pid)

sess = frida.attach(pid)

js = r'''
try {
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    var ssl_read = sslmod.findExportByName("SSL_read");
    Interceptor.attach(ssl_read, {
        onEnter: function(args) { this.buf = args[1]; },
        onLeave: function(retval) {
            var n = retval.toInt32();
            if (n > 0) send({t:"ssl"}, this.buf.readByteArray(n));
        }
    });
    send({t:"ready"});
} catch(e) {
    send({t:"fatal",e:e.toString()});
}
'''

state = {
    'my_cards': [],
    'board': [],
    'opponents': {},
    'last_result': '',
    'event': '',
    'pot': '',
    'hand_num': '',
    'msg_count': 0,
}

MY_UID = 588900

def render():
    os.system('cls')
    print("=" * 52)
    print("    SUPREMA POKER - REAL-TIME DECODER")
    print("=" * 52)
    print()
    my = '  '.join(state['my_cards']) if state['my_cards'] else '--'
    print("  YOUR CARDS:  %s" % my)
    print()
    bd = '  '.join(state['board']) if state['board'] else '--'
    print("  BOARD:       %s" % bd)
    print()
    if state['opponents']:
        print("  OPPONENTS:")
        for name, cards in state['opponents'].items():
            c = '  '.join(cards) if cards else '??'
            print("    %s: %s" % (name, c))
        print()
    if state['pot']:
        print("  POT: %s" % state['pot'])
    if state['hand_num']:
        print("  HAND #%s" % state['hand_num'])
    print()
    if state['last_result']:
        print("  LAST RESULT: %s" % state['last_result'])
        print()
    print("  [%s] msgs=%d" % (state['event'], state['msg_count']))
    print()
    print("  Ctrl+C to stop")

def process_game_data(data):
    if not isinstance(data, dict):
        return
    state['msg_count'] += 1
    updated = False

    event = data.get('pushRoute', '')
    inner = data.get('msg', data)
    if not isinstance(inner, dict):
        return

    ev = inner.get('pushRoute', event)
    if ev:
        state['event'] = str(ev)

    # gameinfo - new hand
    gi = inner.get('game_info', {})
    if isinstance(gi, dict):
        sc = gi.get('shared_cards', [])
        if isinstance(sc, list):
            decoded = decode_list(sc)
            if decoded != state['board']:
                state['board'] = decoded
                updated = True
        gc = gi.get('game_counter', '')
        if gc:
            state['hand_num'] = str(gc)
        pot = gi.get('pot', '')
        if pot:
            state['pot'] = str(pot)

    # handCards directly
    hc = inner.get('handCards', [])
    if hc and any(c != 0 for c in hc if c):
        state['my_cards'] = decode_list(hc)
        state['board'] = []
        state['opponents'] = {}
        state['last_result'] = ''
        updated = True

    # prompt with publicCards
    pc = inner.get('publicCards', [])
    if pc and any(c != 0 for c in pc if c):
        state['board'] = decode_list(pc)
        updated = True

    # gameover
    gr = inner.get('game_result', {})
    if isinstance(gr, dict):
        patterns = gr.get('patterns', [])
        lightcards = gr.get('lightcards', [])
        if patterns and lightcards:
            pat = patterns[0] if patterns else ''
            lc = lightcards[0] if lightcards else []
            if pat and lc:
                decoded = decode_list(lc)
                state['last_result'] = "%s: %s" % (pat, '  '.join(decoded))
                updated = True

        seats = gr.get('seats', {})
        if isinstance(seats, dict):
            for uid_str, sdata in seats.items():
                if not isinstance(sdata, dict):
                    continue
                uid = sdata.get('uid', uid_str)
                cards = sdata.get('cards', [])
                if cards and any(c != 0 for c in cards if c):
                    decoded = decode_list(cards)
                    if str(uid) == str(MY_UID):
                        state['my_cards'] = decoded
                    else:
                        state['opponents'][str(uid)] = decoded
                    updated = True

    # gamer_prompt with cards
    gp = inner.get('gamer_prompt', {})
    if isinstance(gp, dict):
        pass

    # shared_cards in game_info
    if 'shared_cards' in inner:
        sc = inner['shared_cards']
        if isinstance(sc, list) and sc:
            decoded = decode_list(sc)
            if decoded and decoded != state['board']:
                state['board'] = decoded
                updated = True

    # Nested msg
    msg2 = inner.get('msg', None)
    if isinstance(msg2, dict):
        for key in ['handCards', 'cards']:
            val = msg2.get(key, [])
            if val and any(c != 0 for c in val if c):
                decoded = decode_list(val)
                if len(decoded) <= 4:
                    state['my_cards'] = decoded
                    state['board'] = []
                    state['opponents'] = {}
                    updated = True
        for key in ['publicCards', 'boardCards', 'shared_cards']:
            val = msg2.get(key, [])
            if val and any(c != 0 for c in val if c):
                state['board'] = decode_list(val)
                updated = True

    if updated:
        render()

buf = b''

def on_msg(msg, data):
    global buf
    if msg['type'] != 'send':
        return
    p = msg['payload']
    if p.get('t') == 'ready':
        print("HOOKED - aguardando eventos do jogo...")
        render()
        return
    if p.get('t') == 'fatal':
        print("FATAL: %s" % p['e'])
        return
    if p.get('t') != 'ssl' or not data:
        return

    d = bytes(data)
    buf += d

    while len(buf) >= 2:
        if buf[0] != 0x82:
            idx = buf.find(b'\x82', 1)
            if idx == -1:
                buf = b''
                break
            buf = buf[idx:]
            continue

        b1 = buf[1]
        plen_raw = b1 & 0x7F
        ws_off = 2
        if plen_raw == 126:
            if len(buf) < 4:
                break
            ws_len = (buf[2] << 8) | buf[3]
            ws_off = 4
        elif plen_raw == 127:
            if len(buf) < 10:
                break
            ws_len = int.from_bytes(buf[2:10], 'big')
            ws_off = 10
        else:
            ws_len = plen_raw

        total = ws_off + ws_len
        if len(buf) < total:
            break

        ws_payload = buf[ws_off:total]
        buf = buf[total:]

        if len(ws_payload) < 5:
            continue
        ptype = ws_payload[0]
        if ptype != 4:
            continue
        plen2 = (ws_payload[1] << 16) | (ws_payload[2] << 8) | ws_payload[3]
        pbody = ws_payload[4:4+plen2]
        if len(pbody) < 3:
            continue

        msg_type = pbody[0]
        off = 1
        rlen = pbody[off]
        off += 1
        route = pbody[off:off+rlen].decode('ascii', 'replace')
        off += rlen

        try:
            parsed = msgpack.unpackb(pbody[off:], raw=False)
            process_game_data(parsed)
        except:
            pass

sc = sess.create_script(js)
sc.on('message', on_msg)
sc.load()

try:
    while True:
        time.sleep(0.3)
except KeyboardInterrupt:
    pass

print("\nParando...")
sc.unload()
sess.detach()
