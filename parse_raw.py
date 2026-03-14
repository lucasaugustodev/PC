"""Parse the captured raw binary to extract initinfo and player data."""
import msgpack, json, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

raw = open(os.path.expanduser('~/inject_raw.bin'), 'rb').read()
print(f"Raw bytes: {len(raw)}")

# Find initinfo marker
needle = b'\xa8initinfo'
idx = raw.find(needle)
print(f"initinfo at offset: {idx}")

# The msgpack map should start BEFORE "initinfo"
# Pattern: {... "event": "initinfo", "data": {...} ...}
# In msgpack: a56576656e74 a8696e6974696e666f a4646174618f...
# The map header should be before "code" key

# Search backwards from initinfo for a msgpack map header
# "code" key is a4636f6465 which appears before "event"
code_needle = b'\xa4code'
code_idx = raw.rfind(code_needle, 0, idx)
print(f"'code' key at offset: {code_idx}")

# The map should start 1-2 bytes before "code"
# A fixmap header is 0x80-0x8f (map with 0-15 entries)
# A map16 header is 0xde followed by 2 bytes
for start in range(max(0, code_idx - 5), code_idx + 1):
    b = raw[start]
    if 0x80 <= b <= 0x8f or b == 0xde or b == 0xdf:
        try:
            obj = msgpack.unpackb(raw[start:], raw=False)
            if isinstance(obj, dict) and 'event' in obj:
                print(f"\nDECODED msgpack map at offset {start}!")
                print(f"  code: {obj.get('code')}")
                print(f"  event: {obj.get('event')}")

                data = obj.get('data', {})
                if isinstance(data, dict):
                    room = data.get('room', {})
                    print(f"\n  ROOM: {room.get('name', '?')}")
                    print(f"    id: {room.get('id')}")
                    print(f"    type: {room.get('type')}")
                    opts = room.get('options', {})
                    if isinstance(opts, dict):
                        print(f"    blinds: {opts.get('blinds')}")
                        print(f"    maxPlayer: {opts.get('maxPlayer')}")
                        print(f"    ante: {opts.get('anteFix')}")

                    gs = data.get('game_seat', {})
                    gm = data.get('gamer', {})
                    print(f"\n  PLAYERS ({len(gs)} seats):")
                    for uid_key, seat in gs.items():
                        if not isinstance(seat, dict): continue
                        uid = seat.get('uid', uid_key)
                        g = gm.get(str(uid), {}) if isinstance(gm, dict) else {}
                        if not isinstance(g, dict): g = {}

                        agent_id = seat.get('agentID', 0)
                        is_bot = agent_id != 0

                        print(f"    [{uid_key}] {g.get('displayID', '?')}")
                        print(f"      uid={uid} club={g.get('clubID','?')} union={g.get('unionID','?')}")
                        print(f"      stack={seat.get('coins', 0):.2f} winnings={seat.get('winnings', 0):+.2f}")
                        print(f"      agentID={agent_id} {'** BOT **' if is_bot else 'HUMAN'}")
                        print(f"      seat={seat.get('seat')} status={seat.get('status')}")
                        if seat.get('autorebuy'):
                            print(f"      autorebuy={seat.get('autorebuy')}")
                        if g.get('countryCode'):
                            print(f"      country={g.get('countryCode')}")

                    # Game status
                    game_status = data.get('game_status', {})
                    if isinstance(game_status, dict):
                        print(f"\n  GAME STATUS:")
                        print(f"    max_chip: {game_status.get('max_chip')}")
                        print(f"    last_actType: {game_status.get('last_actType')}")

                    # Room extra info
                    print(f"\n  EXTRA:")
                    print(f"    pot: {data.get('pot')}")
                    print(f"    stage: {data.get('stage')}")
                    print(f"    roomID: {data.get('roomID')}")
                    print(f"    agentPlayer: {data.get('agentPlayer')}")

                # Also dump full JSON for analysis
                out = os.path.expanduser('~/inject_initinfo.json')
                with open(out, 'w', encoding='utf-8') as f:
                    json.dump(obj, f, indent=2, default=str, ensure_ascii=False)
                print(f"\n  Full JSON saved to {out}")
                break
        except Exception as e:
            continue

# Also search for other msgpack objects
print("\n\n=== OTHER MSGPACK OBJECTS ===")

# Find connector.entryHandler.entry response
entry_needle = b'connector.entryHandler.entry'
eidx = raw.find(entry_needle)
if eidx >= 0:
    print(f"\nconnector.entryHandler.entry at offset {eidx}")

# Find "joinGameRoom" event
jg_needle = b'\xacjoinGameRoom'
jgidx = raw.find(jg_needle)
if jgidx >= 0:
    print(f"\njoinGameRoom event at offset {jgidx}")
    for start in range(max(0, jgidx - 20), jgidx):
        try:
            obj = msgpack.unpackb(raw[start:], raw=False)
            if isinstance(obj, dict):
                print(f"  Decoded at {start}: {json.dumps(obj, default=str, ensure_ascii=False)[:500]}")
                break
        except:
            continue

# Find all displayID occurrences
print("\n=== ALL PLAYER NAMES ===")
dname = b'\xa9displayID'
pos = 0
while True:
    idx = raw.find(dname, pos)
    if idx < 0: break
    # Read the string value after displayID key
    val_start = idx + len(dname)
    if val_start < len(raw):
        b = raw[val_start]
        if 0xa0 <= b <= 0xbf:
            slen = b & 0x1f
            name = raw[val_start+1:val_start+1+slen].decode('utf-8', errors='replace')
            print(f"  offset {idx}: displayID = '{name}'")
        elif b == 0xd9:
            slen = raw[val_start+1]
            name = raw[val_start+2:val_start+2+slen].decode('utf-8', errors='replace')
            print(f"  offset {idx}: displayID = '{name}'")
    pos = idx + 1

print("\nDone!")
