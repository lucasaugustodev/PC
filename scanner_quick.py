"""Quick scanner - just collect and print match data."""
import frida, json, time, sys, os, msgpack, subprocess, threading
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

recv_buf = b''
send_buf = b''
lock = threading.Lock()
matches = {}
rooms = {}
LOG = os.path.expanduser('~/suprema_scanner.json')

def parse_ws(buf):
    frames = []; pos = 0
    while pos < len(buf):
        if pos + 1 >= len(buf): break
        b0 = buf[pos]; b1 = buf[pos+1]; op = b0 & 0xF
        if op not in (1,2,8,9,10) and (b0&0x80)==0: pos += 1; continue
        m = (b1&0x80) != 0; pl = b1 & 0x7F; hl = 2
        if pl == 126:
            if pos+3 >= len(buf): break
            pl = (buf[pos+2]<<8) | buf[pos+3]; hl = 4
        elif pl == 127:
            if pos+9 >= len(buf): break
            pl = int.from_bytes(buf[pos+2:pos+10], 'big'); hl = 10
        if m: hl += 4
        t = pos + hl + pl
        if t > len(buf): break
        if m:
            mk = buf[pos+hl-4:pos+hl]; r = bytearray(buf[pos+hl:t])
            for i in range(len(r)): r[i] ^= mk[i%4]
            frames.append(bytes(r))
        else:
            frames.append(buf[pos+hl:t])
        pos = t
    return frames, buf[pos:]

def process(raw, d):
    global recv_buf, send_buf
    with lock:
        if d == 'RECV':
            recv_buf += raw
            frames, recv_buf = parse_ws(recv_buf)
        else:
            send_buf += raw
            frames, send_buf = parse_ws(send_buf)

    for frame in frames:
        if len(frame) < 4 or frame[0] != 4: continue
        plen = (frame[1]<<16) | (frame[2]<<8) | frame[3]
        pb = frame[4:4+plen]

        if d == 'SEND':
            if len(pb) < 3: continue
            rl = pb[2]
            if 3+rl > len(pb): continue
            route = bytes(pb[3:3+rl]).decode('utf-8', errors='replace')
            print(f">>> {route}")
        else:
            if len(pb) < 2: continue
            rl = pb[1]; off = 2+rl
            if off >= len(pb): continue
            try:
                body = msgpack.unpackb(pb[off:], raw=False)
            except:
                continue
            if not isinstance(body, dict): continue
            event = body.get('event', '')

            if 'matchesStatus' in str(event):
                api = body.get('apiData', {})
                ms = api.get('matchesStatus', {}) if isinstance(api, dict) else {}
                ml = ms.get('matches', []) if isinstance(ms, dict) else []
                mc = ms.get('matchesCreate', []) if isinstance(ms, dict) else []
                for m in ml + mc:
                    mid = m.get('matchID', 0)
                    if mid:
                        matches[mid] = m
                if ml:
                    print(f"  MATCHES UPDATE: {len(ml)} matches (total: {len(matches)})")

            elif event == 'initinfo':
                data = body.get('data', {})
                if not isinstance(data, dict): continue
                room = data.get('room', {})
                gs = data.get('game_seat', {})
                gm = data.get('gamer', {})
                rid = room.get('id', '?')
                players = []
                for uid, seat in gs.items():
                    if not isinstance(seat, dict): continue
                    g = gm.get(str(seat.get('uid', uid)), {})
                    if not isinstance(g, dict): g = {}
                    players.append({
                        'uid': seat.get('uid', uid),
                        'name': g.get('displayID', str(uid)),
                        'coins': seat.get('coins', 0),
                        'win': seat.get('winnings', 0),
                        'agentID': seat.get('agentID', 0),
                        'bot': seat.get('agentID', 0) != 0,
                        'club': g.get('clubID', 0),
                    })
                rooms[rid] = {
                    'name': room.get('name', '?'),
                    'players': players,
                    'blinds': room.get('options', {}).get('blinds', '?'),
                    'maxPlayer': room.get('options', {}).get('maxPlayer', '?'),
                }
                print(f"  ROOM: {room.get('name','?')} - {len(players)} players")
                for p in players:
                    b = " [BOT]" if p['bot'] else ""
                    print(f"    {p['name']}: stack={p['coins']:.2f}{b}")

        sys.stdout.flush()

# Hook all PIDs
r = subprocess.check_output(
    'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
    shell=True, text=True
).strip()
pids = [int(l.split(',')[1].strip('"')) for l in r.splitlines() if 'SupremaPoker' in l]
print(f"PIDs: {pids}")

JS = r'''
try {
    var s = Process.findModuleByName("libssl-1_1.dll");
    Interceptor.attach(s.findExportByName("SSL_read"), {
        onEnter: function(a) { this.b = a[1]; },
        onLeave: function(r) { var n = r.toInt32(); if (n > 0) send({t:"d", d:"RECV"}, this.b.readByteArray(n)); }
    });
    Interceptor.attach(s.findExportByName("SSL_write"), {
        onEnter: function(a) { var n = a[2].toInt32(); if (n > 0) send({t:"d", d:"SEND"}, a[1].readByteArray(n)); }
    });
    send({t:"ready"});
} catch(e) { send({t:"fatal", e:e.toString()}); }
'''

ss = []
for pid in pids:
    try:
        se = frida.attach(pid)
        sc = se.create_script(JS)
        def make_cb(p):
            def cb(msg, data):
                if msg['type'] != 'send': return
                payload = msg['payload']
                if payload.get('t') == 'ready':
                    print(f"  PID {p}: HOOK OK")
                    sys.stdout.flush()
                    return
                if payload.get('t') == 'd' and data:
                    process(bytes(data), payload.get('d', 'RECV'))
            return cb
        sc.on('message', make_cb(pid))
        sc.load()
        ss.append((se, sc))
    except Exception as e:
        print(f"  PID {pid}: {e}")

print(f"Hooked {len(ss)} processes. Navega no app!")
print("=" * 50)
sys.stdout.flush()

try:
    while True:
        time.sleep(5)
        if matches:
            # Save
            with open(LOG, 'w', encoding='utf-8') as f:
                json.dump({
                    'matches': {str(k): v for k, v in matches.items()},
                    'rooms': rooms,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                }, f, indent=2, default=str, ensure_ascii=False)
            # Summary
            cash = [m for m in matches.values() if not m.get('prizePool')]
            mtt = [m for m in matches.values() if m.get('prizePool')]
            active_cash = [m for m in cash if m.get('!!', 0) > 0]
            print(f"\n[{time.strftime('%H:%M:%S')}] Total: {len(matches)} matches | "
                  f"Cash: {len(cash)} ({len(active_cash)} active) | MTT: {len(mtt)} | Rooms: {len(rooms)}")
            sys.stdout.flush()
except KeyboardInterrupt:
    pass

# Final save
with open(LOG, 'w', encoding='utf-8') as f:
    json.dump({
        'matches': {str(k): v for k, v in matches.items()},
        'rooms': rooms,
    }, f, indent=2, default=str, ensure_ascii=False)
print(f"\nSaved {len(matches)} matches to {LOG}")
for se, sc in ss:
    try: sc.unload()
    except: pass
    try: se.detach()
    except: pass
