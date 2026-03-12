"""Read card mapping data from known memory address 0x1216a000.
The card class has: COLORS, NUMBERS, CARDS, NUMBER_RANK constants.
Also search nearby memory for arrays that look like card mapping tables."""
import frida, json, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

js = r'''
try {
    // Known address where card-related JS code/data was found
    var baseAddr = ptr("0x1216a000");

    // Read a large chunk around this area to find card data
    // Read 64KB
    var chunk = baseAddr.readByteArray(65536);
    send({t: "chunk", addr: baseAddr.toString()}, chunk);

    // Also search for specific card-related strings in this memory region
    // Look for patterns like card names, suit names
    var searchAddr = ptr("0x12160000");
    var bigChunk = searchAddr.readByteArray(131072);  // 128KB
    send({t: "bigchunk", addr: searchAddr.toString()}, bigChunk);

    // Let's also try to find the V8 heap and look for PokerCards object
    // V8 stores objects on the heap, we can search for known string patterns

    // Search for "COLORS" string near card data
    var searchTerms = ["COLORS", "NUMBERS", "CARDS", "NUMBER_RANK", "SPADE", "HEART", "DIAMOND", "CLUB"];

    // Read more memory around the card area
    for (var offset = 0; offset < 0x100000; offset += 0x10000) {
        try {
            var addr = ptr("0x12100000").add(offset);
            var data = addr.readByteArray(0x10000);
            // Check if it contains card-related strings
            var bytes = new Uint8Array(data);
            var text = "";
            for (var i = 0; i < bytes.length; i++) {
                if (bytes[i] >= 32 && bytes[i] < 127) {
                    text += String.fromCharCode(bytes[i]);
                } else {
                    if (text.length > 3) {
                        for (var j = 0; j < searchTerms.length; j++) {
                            if (text.indexOf(searchTerms[j]) !== -1) {
                                send({t: "found_str", str: text.substring(Math.max(0, text.indexOf(searchTerms[j])-20),
                                    text.indexOf(searchTerms[j]) + searchTerms[j].length + 50),
                                    addr: addr.add(i - text.length).toString(),
                                    term: searchTerms[j]});
                            }
                        }
                    }
                    text = "";
                }
            }
        } catch(e) {}
    }

    send({t: "done"});
} catch(e) {
    send({t: "error", e: e.toString()});
}
'''

sc = sess.create_script(js)
chunks = {}

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        t = p.get('t', '')
        if t in ('chunk', 'bigchunk'):
            if data:
                chunks[p['addr']] = data
                print(f"Got {len(data)} bytes from {p['addr']}")
                # Look for readable strings
                d = bytes(data)
                # Extract ASCII strings > 5 chars
                strings = []
                current = b""
                for b in d:
                    if 32 <= b < 127:
                        current += bytes([b])
                    else:
                        if len(current) > 5:
                            strings.append(current.decode('ascii', 'replace'))
                        current = b""
                if current and len(current) > 5:
                    strings.append(current.decode('ascii', 'replace'))

                # Filter for card-related strings
                card_strings = [s for s in strings if any(kw in s.lower() for kw in
                    ['card', 'suit', 'rank', 'color', 'number', 'spade', 'heart', 'diamond', 'club',
                     'poker', 'joker', 'straight', 'flush', 'full', 'pair'])]
                if card_strings:
                    print(f"  Card-related strings found:")
                    for s in card_strings[:30]:
                        print(f"    {s[:100]}")

                # Also look for arrays of numbers 0-51 or 0-78
                # that could be a lookup table
                for i in range(0, len(d)-4, 4):
                    vals = []
                    for j in range(0, min(52*4, len(d)-i), 4):
                        v = int.from_bytes(d[i+j:i+j+4], 'little')
                        if 0 <= v <= 78:
                            vals.append(v)
                        else:
                            break
                    if len(vals) >= 13 and len(set(vals)) >= 10:
                        # Found a potential card mapping array
                        print(f"  Potential card array at offset +0x{i:x}: {vals[:20]}...")

        elif t == 'found_str':
            print(f"[FOUND] '{p['term']}' near {p['addr']}: {p['str'][:80]}")
        elif t == 'done':
            print("Scan complete")
        elif t == 'error':
            print(f"Error: {p['e']}")
        else:
            print(json.dumps(p))
    elif msg['type'] == 'error':
        print(f"ERR: {msg['description']}")

sc.on('message', on_msg)
sc.load()
time.sleep(5)
sc.unload()
sess.detach()
