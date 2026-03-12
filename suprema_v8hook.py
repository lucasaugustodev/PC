"""Search SupremaPoker memory for card decoding logic"""
import frida, json, time, sys, re, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pid = 67336
sess = frida.attach(pid)

js = r'''
function readPrintable(addr, size) {
    var bytes = addr.readByteArray(size);
    if (!bytes) return '';
    var arr = new Uint8Array(bytes);
    var result = '';
    for (var i = 0; i < arr.length; i++) {
        var b = arr[i];
        if (b >= 32 && b < 127) {
            result += String.fromCharCode(b);
        } else {
            result += '.';
        }
    }
    return result;
}

var regions = [
    ['widgetCard_JS', '0x40ac800', 16384],
    ['widgetCard2', '0x40b3d00', 8192],
    ['game_cards', '0x3127f600', 4096],
    ['initCardHolder', '0x3eabe100', 4096],
    ['setCardType', '0x3eabc600', 4096],
    ['setCardList', '0x3eaabb00', 4096],
    ['getCardNode', '0x3eaaab00', 4096],
];

for (var i = 0; i < regions.length; i++) {
    try {
        var data = readPrintable(ptr(regions[i][1]), regions[i][2]);
        send({area: regions[i][0], data: data});
    } catch(e) {
        send({area: regions[i][0], error: e.message});
    }
}
'''

sc = sess.create_script(js)
output_lines = []

def on_msg(msg, data):
    if msg['type'] == 'send':
        p = msg['payload']
        if 'error' in p:
            output_lines.append(f'[{p["area"]}] Error: {p["error"]}')
        else:
            d = p['data']
            segments = re.findall(r'[a-zA-Z0-9_\.\[\]\(\)\{\}\+\-\*/%=<>!&|;:,\'"\\? ]{10,}', d)
            if segments:
                output_lines.append(f'=== {p["area"]} ===')
                for s in segments[:40]:
                    output_lines.append(f'  {s.strip()}')
                output_lines.append('')

sc.on('message', on_msg)
sc.load()
time.sleep(5)
sc.unload()
sess.detach()

with open('suprema_v8_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f'Wrote {len(output_lines)} lines to suprema_v8_output.txt')
for line in output_lines[:100]:
    print(line)
