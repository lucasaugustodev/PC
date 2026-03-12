"""Find XXTEA key by analyzing the SupremaPoker.exe binary"""
import sys, re, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('C:/Program Files (x86)/SupremaPoker/SupremaPoker.exe', 'rb') as f:
    exe = f.read()

pe_off = struct.unpack_from('<I', exe, 0x3C)[0]
num_sections = struct.unpack_from('<H', exe, pe_off + 6)[0]
opt_hdr_size = struct.unpack_from('<H', exe, pe_off + 20)[0]
image_base = struct.unpack_from('<I', exe, pe_off + 52)[0]
sections_off = pe_off + 24 + opt_hdr_size

sects = {}
for i in range(num_sections):
    s_off = sections_off + i * 40
    name = exe[s_off:s_off+8].rstrip(b'\x00').decode('ascii','replace')
    sects[name] = {
        'vaddr': struct.unpack_from('<I', exe, s_off+12)[0],
        'vsize': struct.unpack_from('<I', exe, s_off+8)[0],
        'rawptr': struct.unpack_from('<I', exe, s_off+16)[0],
        'rawsize': struct.unpack_from('<I', exe, s_off+20)[0],
    }

rdata = sects['.rdata']
text = sects['.text']
rdata_data = exe[rdata['rawptr']:rdata['rawptr']+rdata['rawsize']]
text_data = exe[text['rawptr']:text['rawptr']+text['rawsize']]

print(f'Image base: 0x{image_base:08x}')

# Find project.jsc2 string
project_pos = rdata_data.find(b'project.jsc2')
if project_pos < 0:
    project_pos = rdata_data.find(b'project.jsc')

if project_pos >= 0:
    s = rdata_data[project_pos:project_pos+30]
    print(f'"project.jsc" found in .rdata at offset +0x{project_pos:x}')
    print(f'  Content: {s}')

    str_va = image_base + rdata['vaddr'] + project_pos
    print(f'  VA: 0x{str_va:08x}')

    # Find references to this VA in .text
    va_bytes = struct.pack('<I', str_va)
    refs = [(m.start(), image_base + text['vaddr'] + m.start())
            for m in re.finditer(re.escape(va_bytes), text_data)]
    print(f'  Code references: {len(refs)}')

    if refs:
        # For each reference, look at surrounding strings
        for raw_off, code_va in refs[:3]:
            print(f'\n  === Code reference at 0x{code_va:08x} ===')
            # Look at all PUSH instructions (0x68) in the surrounding 200 bytes
            # that reference .rdata strings
            start = max(0, raw_off - 300)
            end = min(len(text_data), raw_off + 100)

            for i in range(start, end):
                if text_data[i] == 0x68:  # PUSH imm32
                    if i + 5 <= len(text_data):
                        pushed_va = struct.unpack_from('<I', text_data, i+1)[0]
                        # Check if this VA points into .rdata
                        rdata_start = image_base + rdata['vaddr']
                        rdata_end = rdata_start + rdata['vsize']
                        if rdata_start <= pushed_va < rdata_end:
                            rdata_off = pushed_va - rdata_start
                            # Read the string at that offset
                            str_end = rdata_data.find(b'\x00', rdata_off)
                            if str_end > rdata_off and str_end - rdata_off < 200:
                                sval = rdata_data[rdata_off:str_end].decode('ascii', 'replace')
                                dist = i - raw_off
                                print(f'    PUSH 0x{pushed_va:08x} (dist={dist:+d}): "{sval}"')
else:
    print('project.jsc not found in .rdata')

# Also search for src/project.jsc
src_pos = rdata_data.find(b'src/project')
if src_pos >= 0:
    s = rdata_data[src_pos:src_pos+30]
    print(f'\n"src/project" found in .rdata: {s}')
    str_va2 = image_base + rdata['vaddr'] + src_pos
    va_bytes2 = struct.pack('<I', str_va2)
    refs2 = [(m.start(), image_base + text['vaddr'] + m.start())
             for m in re.finditer(re.escape(va_bytes2), text_data)]
    print(f'  Code refs: {len(refs2)}')

    if refs2:
        for raw_off, code_va in refs2[:3]:
            print(f'\n  === Code ref at 0x{code_va:08x} ===')
            start = max(0, raw_off - 300)
            end = min(len(text_data), raw_off + 100)
            for i in range(start, end):
                if text_data[i] == 0x68:
                    if i + 5 <= len(text_data):
                        pushed_va = struct.unpack_from('<I', text_data, i+1)[0]
                        rdata_start = image_base + rdata['vaddr']
                        rdata_end = rdata_start + rdata['vsize']
                        if rdata_start <= pushed_va < rdata_end:
                            rdata_off = pushed_va - rdata_start
                            str_end = rdata_data.find(b'\x00', rdata_off)
                            if str_end > rdata_off and str_end - rdata_off < 200:
                                sval = rdata_data[rdata_off:str_end].decode('ascii', 'replace')
                                dist = i - raw_off
                                print(f'    PUSH 0x{pushed_va:08x} (dist={dist:+d}): "{sval}"')
