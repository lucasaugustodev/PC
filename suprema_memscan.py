"""Scan Suprema Poker process memory for game-related strings"""
import ctypes
import ctypes.wintypes as wt
import re

kernel32 = ctypes.windll.kernel32
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
pid = 67336

handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
if not handle:
    print("Could not open process")
    exit(1)

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', wt.DWORD),
        ('RegionSize', ctypes.c_size_t),
        ('State', wt.DWORD),
        ('Protect', wt.DWORD),
        ('Type', wt.DWORD),
    ]

mbi = MEMORY_BASIC_INFORMATION()
address = 0

patterns = re.compile(rb'[\x20-\x7e]{8,120}')
poker_keywords = [b'card', b'hand', b'board', b'game', b'seat', b'bet', b'pot',
                   b'fold', b'call', b'raise', b'flop', b'turn', b'river',
                   b'blind', b'dealer', b'player', b'stack', b'action',
                   b'pomelo', b'connector', b'route', b'push', b'request',
                   b'notify', b'lobby', b'table', b'chip', b'round']

noise = [b'cocos2d', b'ERROR', b'framework', b'.cpp', b'.h,', b'@@',
         b'workspace', b'warning', b'lambda', b'std::', b'operator',
         b'Listener', b'Event', b'WEBGL', b'opengl', b'texture']

found = set()

while address < 0x7FFFFFFF:
    result = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address),
                                      ctypes.byref(mbi), ctypes.sizeof(mbi))
    if result == 0:
        break
    if mbi.State == 0x1000 and mbi.Protect in (0x02, 0x04, 0x20, 0x40):
        size = min(mbi.RegionSize, 10 * 1024 * 1024)
        buf = ctypes.create_string_buffer(size)
        bytesRead = ctypes.c_size_t()
        if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(address),
                                       buf, size, ctypes.byref(bytesRead)):
            content = buf.raw[:bytesRead.value]
            for m in patterns.finditer(content):
                s = m.group()
                s_lower = s.lower()
                if any(k in s_lower for k in poker_keywords):
                    if not any(n in s for n in noise):
                        found.add(s)
    address += mbi.RegionSize
    if address <= 0:
        break

kernel32.CloseHandle(handle)

for s in sorted(found):
    print(s.decode('utf-8', errors='replace'))
