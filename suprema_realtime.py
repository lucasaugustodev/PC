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
    if cid is None or cid == 0:
        return '??'
    r = (cid - 2) % 16
    s = (cid - 2) // 16
    if 0 <= r < 13 and 0 <= s <= 4:
        return RANKS[r] + SUITS[s]
    return f'?{cid}'

def decode_list(cards):
    if not cards:
        return []
    return [decode(c) for c in cards if c and c != 0]

# Auto-detect PID
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
    print("SupremaPoker.exe not found!")
    sys.exit(1)
print(f"Attaching to PID {pid}...")

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

# Game state
state = {
    'my_cards': [],
    'board': [],
    'opponents': {},
    'last_result': '',
    'event': '',
    'table_id': '',
    'seat': '',
    'pot': '',
    'round': '',
    'msg_count': 0,
}

def render():
    os.system('cls')
    print("=" * 50)
    print("   SUPREMA POKER - REAL-TIME DECODER")
    print("=" * 50)
    print()

    my = ' '.join(state['my_cards']) if state['my_cards'] else '--'
    print(f"  YOUR CARDS:  {my}")
    print()

    bd = ' '.join(state['board']) if state['board'] else '--'
    print(f"  BOARD:       {bd}")
    print()

    if state['opponents']:
        print("  OPPONENTS:")
        for name, cards in state['opponents'].items():
            c = ' '.join(cards) if cards else '??'
            print(f"    {name}: {c}")
        print()

    if state['pot']:
        print(f"  POT: {state['pot']}")
    if state['round']:
        print(f"  ROUND: {state['round']}")
    print()

    if state['last_result']:
        print(f"  LAST RESULT: {state['last_result']}")
        print()

    print(f"  Event: {state['event']}  |  Msgs: {state['msg_count']}")
    print()
    print("  Press Ctrl+C to stop")

def process_event(route, data):
    if not isinstance(data, dict):
        return

    state['msg_count'] += 1
    updated = False

    # Extract event name from onMsg wrapper
    event = data.get('pushRoute', data.get('route', route))
    if event:
        state['event'] = event

    # Inner data (onMsg wraps actual event)
    inner = data.get('msg', data)
    if isinstance(inner, dict):
        ev = inner.get('pushRoute', '')

        # gameinfo - new hand starting
        if 'gameinfo' in str(ev) or 'handCards' in inner:
            hc = inner.get('handCards', [])
            if hc:
                state['my_cards'] = decode_list(hc)
                state['board'] = []
                state['opponents'] = {}
                state['last_result'] = ''
                updated = True

        # prompt - board cards dealt
        if 'prompt' in str(ev) or 'publicCards' in inner:
            pc = inner.get('publicCards', [])
            if pc:
                state['board'] = decode_list(pc)
                updated = True

        # gameover - showdown
        if 'gameover' in str(ev):
            seats = inner.get('seats', [])
            best = inner.get('bestCards', inner.get('lightcards', []))
            pattern = inner.get('pattern', inner.get('cardPattern', ''))

            if best:
                decoded = decode_list(best)
                state['last_result'] = f"{pattern}: {' '.join(decoded)}"
                updated = True

            # Check seats for opponent cards
            if seats:
                for s in seats:
                    if not isinstance(s, dict):
                        continue
                    uid = s.get('uid', s.get('userId', ''))
                    hc = s.get('handCards', s.get('cards', []))
                    if hc:
                        nick = s.get('nickname', str(uid))
                        state['opponents'][nick] = decode_list(hc)
                        updated = True

        # Deal/flop/turn/river via publicCards in any event
        if 'publicCards' in inner:
            pc = inner.get('publicCards', [])
            if pc and any(c != 0 for c in pc):
                state['board'] = decode_list(pc)
                updated = True

        # Cards in nested msg
        msg_inner = inner.get('msg', {})
        if isinstance(msg_inner, dict):
            for key in ['handCards', 'cards', 'publicCards', 'boardCards', 'lightcards']:
                if key in msg_inner:
                    cards = msg_inner[key]
                    if cards and any(c != 0 for c in cards if c):
                        decoded = decode_list(cards)
                        if key in ('handCards', 'cards') and len(decoded) == 2:
                            state['my_cards'] = decoded
                            updated = True
                        elif key in ('publicCards', 'boardCards'):
                            state['board'] = decoded
                            updated = True

            if 'seats' in msg_inner:
                for s in msg_inner['seats']:
                    if not isinstance(s, dict):
                        continue
                    hc = s.get('handCards', s.get('cards', []))
                    if hc and any(c != 0 for c in hc if c):
                        uid = s.get('uid', s.get('userId', ''))
                        nick = s.get('nickname', str(uid))
                        state['opponents'][nick] = decode_list(hc)
                        updated = True

            ev2 = msg_inner.get('pushRoute', '')
            if 'gameover' in str(ev2):
                best = msg_inner.get('bestCards', msg_inner.get('lightcards', []))
                pattern = msg_inner.get('pattern', msg_inner.get('cardPattern', ''))
                if best:
                    state['last_result'] = f"{pattern}: {' '.join(decode_list(best))}"
                    updated = True

        # Pot
        pot = inner.get('pot', inner.get('totalPot', ''))
        if pot:
            state['pot'] = str(pot)

    if updated:
        render()

buf = b''

def on_msg(msg, data):
    global buf
    if msg['type'] == 'send':
        p = msg['payload']
        if p.get('t') == 'ready':
            print("HOOKED - waiting for game events...")
            render()
        elif p.get('t') == 'fatal':
            print(f"FATAL: {p['e']}")
        elif p.get('t') == 'ssl' and data:
            d = bytes(data)
            buf += d
            # Try to parse complete messages
            while len(buf) >= 2:
                if buf[0] != 0x82:
                    # Find next 0x82
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

                # Parse Pomelo
                if len(ws_payload) < 5:
                    continue
                ptype = ws_payload[0]
                if ptype != 4:  # only data messages
                    continue
                plen2 = (ws_payload[1] << 16) | (ws_payload[2] << 8) | ws_payload[3]
                pbody = ws_payload[4:4+plen2]

                if len(pbody) < 3:
                    continue

                # Inner: msg_type + route_len + route + msgpack
                msg_type = pbody[0]
                off = 1
                rlen = pbody[off]
                off += 1
                route = pbody[off:off+rlen].decode('ascii', 'replace')
                off += rlen

                try:
                    parsed = msgpack.unpackb(pbody[off:], raw=False)
                    process_event(route, parsed)
                except:
                    pass

    elif msg['type'] == 'error':
        pass

sc = sess.create_script(js)
sc.on('message', on_msg)
sc.load()

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    pass

print("\nStopping...")
sc.unload()
sess.detach()
