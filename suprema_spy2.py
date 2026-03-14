"""Suprema Protocol Spy v2 - Raw dump of all SSL traffic with direction."""
import frida, json, time, sys, os, subprocess, threading
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import msgpack
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'msgpack'])
    import msgpack

def find_pid():
    r = subprocess.check_output(
        'tasklist /FI "IMAGENAME eq SupremaPoker.exe" /FO CSV /NH',
        shell=True, text=True
    ).strip()
    for line in r.splitlines():
        if 'SupremaPoker' in line:
            return int(line.split(',')[1].strip('"'))
    return None

pid = find_pid()
if not pid:
    print("SupremaPoker not running!")
    sys.exit(1)

LOG_FILE = os.path.expanduser('~/suprema_spy2.log')
lock = threading.Lock()
msg_counter = 0

def try_decode_pomelo(raw, direction):
    """Try to extract readable info from raw SSL data."""
    results = []

    # Try to find msgpack-encoded dicts in the data
    # Scan for common msgpack patterns
    for i in range(len(raw)):
        if i + 5 > len(raw):
            break

        # Look for msgpack map markers (0x80-0x8f for fixmap, 0xde for map16)
        b = raw[i]
        if b in (0xde, 0xdf) or (0x80 <= b <= 0x8f):
            try:
                obj = msgpack.unpackb(raw[i:], raw=False)
                if isinstance(obj, dict) and len(obj) > 0:
                    results.append(obj)
                    break
            except:
                continue

    return results

def extract_strings(raw):
    """Extract readable ASCII strings from raw data."""
    strings = []
    current = []
    for b in raw:
        if 32 <= b <= 126:
            current.append(chr(b))
        else:
            if len(current) >= 4:
                strings.append(''.join(current))
            current = []
    if len(current) >= 4:
        strings.append(''.join(current))
    return strings

def on_msg(msg, data):
    global msg_counter
    if msg['type'] != 'send':
        return
    p = msg['payload']

    if p.get('t') == 'ready':
        print("\033[92mHOOK OK! Monitoring all SSL traffic...\033[0m")
        return
    if p.get('t') == 'fatal':
        print(f"\033[91mFATAL: {p['e']}\033[0m")
        return
    if not data:
        return

    raw = bytes(data)
    direction = p.get('d', '?')

    with lock:
        msg_counter += 1

        # Extract strings for quick view
        strings = extract_strings(raw)

        # Try msgpack decode
        decoded = try_decode_pomelo(raw, direction)

        # Determine arrow and color
        if direction == 'SEND':
            arrow = '>>>'
            color = '\033[93m'  # Yellow
        else:
            arrow = '<<<'
            color = '\033[96m'  # Cyan

        # Filter: only show interesting stuff
        is_interesting = False
        summary = ''

        # Check strings for keywords
        interesting_keywords = ['room', 'join', 'enter', 'seat', 'match', 'game', 'table',
                                'spectate', 'observe', 'lobby', 'list', 'connect',
                                'Handler', 'apiRoom', 'apiGame', 'apiMatch', 'buyin']

        for s in strings:
            for kw in interesting_keywords:
                if kw.lower() in s.lower():
                    is_interesting = True
                    break

        # Check decoded objects
        for obj in decoded:
            if isinstance(obj, dict):
                is_interesting = True
                # Look for route/event info
                for key in ('route', 'event', 'roomID', 'matchID'):
                    if key in obj:
                        summary += f" {key}={obj[key]}"

        # For SEND, always show (we want to see ALL client requests)
        if direction == 'SEND':
            is_interesting = True

        if not is_interesting:
            return

        timestamp = time.strftime('%H:%M:%S')

        # Build log line
        line = f"[{timestamp}] #{msg_counter} {arrow} {direction} ({len(raw)}b)"
        if summary:
            line += f" {summary}"

        # Strings found
        str_line = ''
        if strings:
            str_line = f"  strings: {strings[:10]}"

        # Decoded objects
        obj_line = ''
        for obj in decoded:
            try:
                js = json.dumps(obj, ensure_ascii=False, default=str)
                if len(js) > 1000:
                    js = js[:1000] + '...'
                obj_line += f"  decoded: {js}\n"
            except:
                pass

        # Hex dump (first 100 bytes)
        hex_line = f"  hex: {raw[:100].hex()}"

        # Print
        print(f"{color}{line}\033[0m")
        if str_line:
            print(str_line)
        if obj_line:
            print(obj_line.rstrip())
        if direction == 'SEND':
            print(hex_line)
        print()

        # Log to file
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{line}\n")
            if str_line:
                f.write(f"{str_line}\n")
            if obj_line:
                f.write(obj_line)
            f.write(f"{hex_line}\n")
            f.write("\n")

# Clear log
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write(f"=== Suprema Protocol Spy v2 - {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")

print(f"Connecting to SupremaPoker (PID {pid})...")
sess = frida.attach(pid)

js = r'''
try {
    var sslmod = Process.findModuleByName("libssl-1_1.dll");

    var ssl_read = sslmod.findExportByName("SSL_read");
    Interceptor.attach(ssl_read, {
        onEnter: function(args) { this.buf = args[1]; },
        onLeave: function(retval) {
            var n = retval.toInt32();
            if (n > 0) send({t:"data", d:"RECV"}, this.buf.readByteArray(n));
        }
    });

    var ssl_write = sslmod.findExportByName("SSL_write");
    Interceptor.attach(ssl_write, {
        onEnter: function(args) {
            var n = args[2].toInt32();
            if (n > 0) send({t:"data", d:"SEND"}, args[1].readByteArray(n));
        }
    });

    send({t:"ready"});
} catch(e) {
    send({t:"fatal", e:e.toString()});
}
'''

sc = sess.create_script(js)
sc.on('message', on_msg)
sc.load()

print("\033[92m")
print("=" * 60)
print("  SUPREMA PROTOCOL SPY v2 - RAW MODE")
print(f"  Logging to: {LOG_FILE}")
print("  ")
print("  >>> AMARELO = Client ENVIA")
print("  <<< AZUL = Server RESPONDE")
print("  ")
print("  SAI da mesa e ENTRA de novo pra capturar o JOIN!")
print("=" * 60)
print("\033[0m")

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    pass

print("\nStopping...")
sc.unload()
sess.detach()
