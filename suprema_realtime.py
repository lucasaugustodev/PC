"""Real-time card decoder + betting tracker + GTO advisor for Suprema Poker."""
import frida, json, time, sys, os, subprocess, threading
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import msgpack
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'msgpack'])
    import msgpack

try:
    import anthropic
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'anthropic'])
    import anthropic

def _load_api_key():
    for p in [os.path.expanduser('~/.anthropic_key'), os.path.join(os.path.dirname(__file__), '.anthropic_key')]:
        if os.path.exists(p):
            return open(p).read().strip()
    return os.environ.get('ANTHROPIC_API_KEY', '')

llm_client = anthropic.Anthropic(api_key=_load_api_key())

RANKS = '23456789TJQKA'
SUITS = ['c','d','h','s','x']
MY_UID = 588900

# Role code -> action name
ROLES = {
    0: '', 2: '', 3: '',           # idle/reset/dealer
    13: 'DEALER', 30: 'CALL', 32: 'CALL',
    33: 'CALL', 40: 'FOLD', 42: 'CHECK',
    43: 'CHECK', 50: 'RAISE', 63: 'BB',
    70: 'BET', 72: 'RAISE', 73: 'RAISE',
    82: 'SB', 93: 'BB', 100: 'FOLD',
}

STREETS = {3: 'PREFLOP', 4: 'FLOP', 5: 'TURN', 6: 'RIVER', 7: 'SHOWDOWN'}

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
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq SupremaPoker.exe', '/FO', 'CSV', '/NH'],
                       capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        if 'SupremaPoker' in line:
            parts = line.strip('"').split('","')
            return int(parts[1])
    return None

pid = find_pid()
if not pid:
    print("SupremaPoker.exe nao encontrado!")
    input("Press Enter...")
    sys.exit(1)

print("PID: %d" % pid, flush=True)

BB_SIZE = 0  # auto-detected from game_info.blinds

def bb(val):
    """Convert internal value to BB count."""
    if BB_SIZE <= 0:
        return val
    return val / BB_SIZE

def fmt_bb(val):
    """Format value as BB string."""
    if BB_SIZE <= 0:
        return str(val)
    b = bb(val)
    if b == int(b):
        return "%dBB" % int(b)
    return "%.1fBB" % b

state = {
    'my_cards': [],
    'board': [],
    'opponents': {},
    'last_result': '',
    'event': '',
    'pot': 0,
    'hand_num': '',
    'street': '',
    'max_bet': 0,
    'last_raise': 0,
    'sidepots': [],
    'players': {},      # uid -> {name, chips, chips_round, role, action, stack}
    'actions': [],       # list of action strings for current hand
    'acting_seat': -1,
    'msg_count': 0,
    'gto_advice': '',
    'dirty': True,
    'blinds_level': 0,
    'next_blinds': 0,
    'avg_stack': 0,
    'player_count': 0,
    'small_blinds': 0,
}

def show():
    os.system('cls')
    print("=" * 56, flush=True)
    print("     SUPREMA POKER - REAL-TIME DECODER", flush=True)
    print("=" * 56, flush=True)
    hand = state['hand_num']
    street = state['street']
    print("  Hand #%-6s  %s" % (hand or '?', street), flush=True)
    print("-" * 56, flush=True)

    my = '  '.join(state['my_cards']) if state['my_cards'] else '--'
    print("  YOUR CARDS:  %s" % my, flush=True)

    bd = '  '.join(state['board']) if state['board'] else '--'
    print("  BOARD:       %s" % bd, flush=True)
    print(flush=True)

    # Pot info
    pot = state['pot']
    print("  POT: %-8s  max_bet: %-8s  last_raise: %s" % (
        fmt_bb(pot), fmt_bb(state['max_bet']), fmt_bb(state['last_raise'])), flush=True)
    if state['sidepots']:
        print("  SIDEPOTS: %s" % [fmt_bb(s) for s in state['sidepots']], flush=True)
    print(flush=True)

    # Players table
    if state['players']:
        print("  %-10s %-8s %-8s %-8s %-8s %s" % (
            'PLAYER', 'STACK', 'BET', 'ROUND', 'ACTION', 'CARDS'), flush=True)
        print("  " + "-" * 54, flush=True)
        for uid, p in sorted(state['players'].items(), key=lambda x: x[1].get('seat', 0)):
            marker = '>> ' if str(uid) == str(MY_UID) else '   '
            name = str(uid)[-6:]
            stack = p.get('stack', 0)
            chips = p.get('chips', 0)
            cr = p.get('chips_round', 0)
            action = p.get('action', '')
            cards = p.get('cards', '')
            print("%s%-10s %-8s %-8s %-8s %-8s %s" % (
                marker, name, fmt_bb(stack), fmt_bb(chips), fmt_bb(cr), action, cards), flush=True)
        print(flush=True)

    # Recent actions
    if state['actions']:
        print("  ACTIONS:", flush=True)
        for a in state['actions'][-8:]:
            print("    %s" % a, flush=True)
        print(flush=True)

    # Opponents cards (showdown)
    if state['opponents']:
        print("  SHOWDOWN:", flush=True)
        for name, cards in state['opponents'].items():
            c = '  '.join(cards) if cards else '??'
            print("    %s: %s" % (name, c), flush=True)
        print(flush=True)

    if state['last_result']:
        print("  RESULT: %s" % state['last_result'], flush=True)
        print(flush=True)

    # GTO recommendation
    if state['gto_advice']:
        print("  >>> GTO: %s <<<" % state['gto_advice'], flush=True)
        print(flush=True)

    print("  [%s] msgs=%d" % (state['event'], state['msg_count']), flush=True)
    print("  Ctrl+C to stop", flush=True)
    state['dirty'] = False

def build_gto_prompt():
    """Build poker situation description for LLM."""
    cards = ' '.join(state['my_cards']) if state['my_cards'] else '??'
    board = ' '.join(state['board']) if state['board'] else 'none'
    street = state['street'] or '?'
    pot = fmt_bb(state['pot'])
    max_bet = fmt_bb(state['max_bet'])

    # Build player info
    num_players = len([p for p in state['players'].values() if p.get('action') not in ('FOLD', '')])
    my_stack = 0
    my_pos = ''
    actions_history = []
    for uid, p in sorted(state['players'].items(), key=lambda x: x[1].get('seat', 0)):
        action = p.get('action', '')
        if action:
            stack_bb = fmt_bb(p.get('stack', 0))
            bet_bb = fmt_bb(p.get('chips', 0))
            if str(uid) == str(MY_UID):
                my_stack = p.get('stack', 0)
            elif action not in ('', 'FOLD'):
                actions_history.append("%s %s" % (action, bet_bb))

    # Build position info
    my_seat_num = 0
    total_seats = len(state['players'])
    for uid, p in state['players'].items():
        if str(uid) == str(MY_UID):
            my_seat_num = p.get('seat', 0)

    prompt = (
        "6max NLH cash. Stacks ~%s. "
        "Hero has [%s]. Board: [%s]. Street: %s. "
        "Pot: %s. To call: %s. "
        "Players in hand: %d. Action so far: %s. "
        "Hero seat %d of %d."
    ) % (fmt_bb(my_stack), cards, board, street, pot,
         fmt_bb(state['max_bet'] - (state['players'].get(str(MY_UID), {}).get('chips_round', 0))),
         num_players, ', '.join(actions_history) if actions_history else 'none',
         my_seat_num, total_seats)
    return prompt

GTO_SYSTEM = """You are a world-class GTO poker solver. Analyze this hand and give the OPTIMAL play.

Rules:
- Consider position, stack depth, pot odds, equity, board texture, and range advantage
- Account for blockers and removal effects
- On the flop/turn/river, consider draws, made hands, and bluff candidates
- Give specific bet sizings (e.g. "33% pot", "75% pot", "overbet 1.5x pot")
- If it's a mixed strategy spot, give the primary action with frequency

Response format (keep it SHORT, max 2 lines):
ACTION: [fold/check/call/bet/raise] SIZE: [amount in BB or % pot] | [1-line reason]"""

def ask_gto():
    """Call Claude Haiku in background thread."""
    try:
        prompt = build_gto_prompt()
        resp = llm_client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=150,
            system=GTO_SYSTEM,
            messages=[{'role': 'user', 'content': prompt}],
        )
        advice = resp.content[0].text.strip()
        state['gto_advice'] = advice
        state['dirty'] = True
    except Exception as e:
        state['gto_advice'] = 'Error: %s' % str(e)[:80]
        state['dirty'] = True

gto_thread = None
gto_last_hand = ''
gto_last_street = ''

def maybe_ask_gto():
    """Trigger GTO advice when it's hero's turn."""
    global gto_thread, gto_last_hand, gto_last_street
    if not state['my_cards']:
        return
    key = "%s_%s" % (state['hand_num'], state['street'])
    if key == gto_last_hand:
        return  # already asked for this spot
    gto_last_hand = key
    state['gto_advice'] = 'thinking...'
    state['dirty'] = True
    gto_thread = threading.Thread(target=ask_gto, daemon=True)
    gto_thread.start()

def process(parsed):
    if not isinstance(parsed, dict):
        return

    state['msg_count'] += 1

    event = parsed.get('event', '')
    d = parsed.get('data', parsed.get('apiData', {}))
    if not isinstance(d, dict):
        return

    if event:
        state['event'] = str(event)

    # game_info
    gi = d.get('game_info', {})
    if isinstance(gi, dict) and gi:
        # Auto-detect BB size from blinds field (works for cash, SNG, MTT)
        blinds_val = gi.get('blinds', 0)
        if blinds_val and float(blinds_val) > 0:
            global BB_SIZE
            BB_SIZE = float(blinds_val)

        sc = gi.get('shared_cards', [])
        if isinstance(sc, list):
            decoded = decode_list(sc)
            if decoded:
                if decoded != state['board']:
                    state['board'] = decoded
                    state['dirty'] = True
            elif state['board']:
                state['board'] = []
                state['opponents'] = {}
                state['last_result'] = ''
                state['dirty'] = True

        gc = gi.get('game_counter', '')
        if gc and str(gc) != state['hand_num']:
            state['hand_num'] = str(gc)
            state['my_cards'] = []
            state['board'] = []
            state['opponents'] = {}
            state['actions'] = []
            state['players'] = {}
            state['last_result'] = ''
            state['gto_advice'] = ''
            state['dirty'] = True

        pot = gi.get('pot', None)
        if pot is not None:
            state['pot'] = float(pot)

        st = gi.get('state', None)
        if st is not None:
            state['street'] = STREETS.get(st, str(st))

    # game_status
    gst = d.get('game_status', {})
    if isinstance(gst, dict) and gst:
        state['max_bet'] = float(gst.get('max_chip', 0))
        state['last_raise'] = float(gst.get('last_raise', 0))
        sp = gst.get('sidepots', [])
        if sp:
            state['sidepots'] = sp

    # game_seat -> player info + cards + actions
    gs = d.get('game_seat', {})
    if isinstance(gs, dict) and gs:
        for uid_str, sd in gs.items():
            if not isinstance(sd, dict):
                continue
            uid = sd.get('uid', uid_str)
            uid_s = str(uid)
            role = sd.get('role', 0)
            chips = sd.get('chips', 0)
            cr = sd.get('chips_round', 0)
            stack = sd.get('coins', 0)
            seat = sd.get('seat', 0)
            action_name = ROLES.get(role, 'r%d' % role)

            # Detect action changes
            prev = state['players'].get(uid_s, {})
            prev_chips = prev.get('chips', 0)
            prev_role = prev.get('role_code', -1)

            if role != prev_role and action_name:
                amount = chips - prev_chips if chips > prev_chips else 0
                if action_name in ('BET', 'RAISE') and amount > 0:
                    action_str = "%s %s %s (total %s)" % (uid_s[-6:], action_name, fmt_bb(amount), fmt_bb(chips))
                elif action_name == 'CALL':
                    action_str = "%s CALL %s" % (uid_s[-6:], fmt_bb(chips))
                elif action_name in ('FOLD', 'CHECK', 'SB', 'BB'):
                    action_str = "%s %s" % (uid_s[-6:], action_name)
                    if action_name in ('SB', 'BB'):
                        action_str += " %s" % fmt_bb(chips)
                else:
                    action_str = ''

                if action_str:
                    state['actions'].append(action_str)
                    state['dirty'] = True

            # Cards
            cards_str = ''
            cards_raw = sd.get('cards', None)
            if cards_raw and isinstance(cards_raw, list) and any(c and c != 0 for c in cards_raw):
                decoded = decode_list(cards_raw)
                cards_str = ' '.join(decoded)
                if uid_s == str(MY_UID) and decoded != state['my_cards']:
                    state['my_cards'] = decoded
                    state['dirty'] = True

            # Pattern (shown in prompt)
            pattern = sd.get('pattern', '')

            state['players'][uid_s] = {
                'seat': seat,
                'stack': stack,
                'chips': chips,
                'chips_round': cr,
                'action': action_name,
                'role_code': role,
                'cards': cards_str,
                'pattern': pattern,
            }
            state['dirty'] = True

    # countdown -> who's acting
    cd = d.get('countdown', {})
    if isinstance(cd, dict):
        state['acting_seat'] = cd.get('seat', -1)

    # gameover
    gr = d.get('game_result', {})
    if isinstance(gr, dict) and gr:
        patterns = gr.get('patterns', [])
        lightcards = gr.get('lightcards', [])
        allpots = gr.get('allpots', [])

        if patterns and lightcards:
            pat = patterns[0] if patterns else ''
            lc = lightcards[0] if lightcards else []
            if pat and lc:
                state['last_result'] = "%s: %s" % (pat, '  '.join(decode_list(lc)))
                state['dirty'] = True

        seats = gr.get('seats', {})
        if isinstance(seats, dict):
            for uid_str, sdata in seats.items():
                if not isinstance(sdata, dict):
                    continue
                uid = sdata.get('uid', uid_str)
                cards = sdata.get('cards', [])
                prize = sdata.get('prize', [])
                diff = sdata.get('chipsDiff', [])
                if cards and any(c != 0 for c in cards if c):
                    decoded = decode_list(cards)
                    if str(uid) == str(MY_UID):
                        state['my_cards'] = decoded
                    else:
                        state['opponents'][str(uid)] = decoded
                    state['dirty'] = True

                # Log result
                if prize and any(p > 0 for p in prize):
                    action_str = "%s WON %s" % (str(uid)[-6:], fmt_bb(sum(prize)))
                    state['actions'].append(action_str)
                elif diff and any(d < 0 for d in diff):
                    action_str = "%s LOST %s" % (str(uid)[-6:], fmt_bb(abs(sum(diff))))
                    state['actions'].append(action_str)

        if allpots:
            state['actions'].append("POTS: %s" % [fmt_bb(p) for p in allpots])
        state['dirty'] = True

    # handCards fallback
    hc = d.get('handCards', [])
    if hc and any(c != 0 for c in hc if c):
        state['my_cards'] = decode_list(hc)
        state['dirty'] = True

    # Trigger GTO advice when it's hero's turn (prompt event or board changes)
    if event == 'prompt' and state['my_cards']:
        maybe_ask_gto()

buf = b''
lock = threading.Lock()

def on_msg(msg, data):
    global buf
    if msg['type'] != 'send':
        return
    p = msg['payload']
    if p.get('t') == 'ready':
        print("HOOK OK!", flush=True)
        state['dirty'] = True
        return
    if p.get('t') == 'fatal':
        print("FATAL: %s" % p['e'], flush=True)
        return
    if p.get('t') != 'ssl' or not data:
        return

    with lock:
        buf += bytes(data)
        parse_buf()

def parse_buf():
    global buf
    while len(buf) >= 2:
        if buf[0] != 0x82:
            idx = buf.find(b'\x82', 1)
            if idx == -1:
                buf = b''
                break
            buf = buf[idx:]
            continue

        b1 = buf[1] & 0x7F
        ws_off = 2
        if b1 == 126:
            if len(buf) < 4: break
            ws_len = (buf[2] << 8) | buf[3]
            ws_off = 4
        elif b1 == 127:
            if len(buf) < 10: break
            ws_len = int.from_bytes(buf[2:10], 'big')
            ws_off = 10
        else:
            ws_len = b1

        total = ws_off + ws_len
        if len(buf) < total:
            break

        ws_payload = buf[ws_off:total]
        buf = buf[total:]

        if len(ws_payload) < 5:
            continue
        if ws_payload[0] != 4:
            continue
        plen2 = (ws_payload[1] << 16) | (ws_payload[2] << 8) | ws_payload[3]
        pbody = ws_payload[4:4+plen2]
        if len(pbody) < 3:
            continue

        rlen = pbody[1]
        off = 2 + rlen

        try:
            parsed = msgpack.unpackb(pbody[off:], raw=False)
            process(parsed)
        except:
            pass

# Connect
print("Connecting to SupremaPoker (PID %d)..." % pid, flush=True)
sess = frida.attach(pid)

js = r'''
try {
    var sslmod = Process.findModuleByName("libssl-1_1.dll");
    var ssl_read = sslmod.findExportByName("SSL_read");
    Interceptor.attach(ssl_read, {
        onEnter: function(args) { this.buf = args[1]; },
        onLeave: function(retval) {
            var n = retval.toInt32();
            if (n > 0) send({t:"ssl",s:n}, this.buf.readByteArray(n));
        }
    });
    send({t:"ready"});
} catch(e) {
    send({t:"fatal",e:e.toString()});
}
'''

sc = sess.create_script(js)
sc.on('message', on_msg)
sc.load()

print("Monitoring... play a hand!", flush=True)
show()

try:
    while True:
        time.sleep(0.5)
        if state['dirty']:
            show()
except KeyboardInterrupt:
    pass

print("\nStopping...")
sc.unload()
sess.detach()
