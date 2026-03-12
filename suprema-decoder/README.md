# Suprema Poker - Real-Time Card Decoder

Real-time card decoder for Suprema Poker. Intercepts network traffic via Frida, parses the WebSocket/Pomelo/msgpack protocol stack, and decodes card IDs into human-readable cards.

## How It Works

Suprema Poker uses a layered protocol:

```
SSL/TLS -> WebSocket (binary frames) -> Pomelo (type 4 = data) -> msgpack payload
```

Card IDs are encoded with 4 suit groups of 13 cards each, with 3-ID gaps between groups:

```
rank = (card_id - 2) % 16    # 0-12 -> 2,3,4,5,6,7,8,9,T,J,Q,K,A
suit = (card_id - 2) // 16   # 0-3 -> clubs, diamonds, hearts, spades
```

| Suit | Card IDs | Range |
|------|----------|-------|
| Suit 0 | 2-14 | 2c - Ac |
| Suit 1 | 18-30 | 2d - Ad |
| Suit 2 | 34-46 | 2h - Ah |
| Suit 3 | 50-62 | 2s - As |
| Suit 4 | 66-78 | 2x - Ax |

IDs 15-17, 31-33, 47-49, 63-65 are gaps (unused).

## Scripts

### `suprema_realtime.py` - Real-Time Decoder (Main)

Opens a terminal window showing decoded cards live during gameplay:
- Your hole cards
- Board cards (flop/turn/river)
- Opponent cards (at showdown)
- Last hand result

```bash
python suprema_realtime.py
```

Auto-detects the SupremaPoker process. Hooks `SSL_read` via Frida to capture traffic.

### `suprema_fullcapture.py` - Full Traffic Logger

Captures and logs all game events to a file for analysis.

```bash
python suprema_fullcapture.py
```

Output goes to `suprema_fullcapture.log`.

### `suprema_solver2.py` - Card Encoding Solver

Constraint-based solver that deduces the card encoding formula from showdown data. Used during reverse engineering to discover the `(id - 2) % 16` formula.

### `suprema_csp.py` - CSP Solver

Exhaustive formula search across multiple encoding strategies. Tests `(id - offset) % N`, `((id - offset) // D) % 13`, and `(id * M + offset) % 13`.

### `suprema_livehook.py` - Sprite + SSL Hook

Combined hook for sprite frame monitoring and SSL traffic capture. Used during initial reverse engineering.

## Requirements

- Python 3.10+
- [Frida](https://frida.re/) (`pip install frida frida-tools`)
- [msgpack](https://pypi.org/project/msgpack/) (`pip install msgpack`)
- Windows (Suprema Poker is a Windows desktop app)

```bash
pip install frida frida-tools msgpack
```

## Protocol Details

### WebSocket Frame
```
0x82 [length] [payload]
```
- `0x82` = binary final frame
- Length: 1 byte (<126), or `0x7E` + 2 bytes, or `0x7F` + 8 bytes

### Pomelo Header
```
[type: 1 byte] [length: 3 bytes] [body]
```
- Type 4 = data message

### Inner Message
```
[msg_type: 1 byte] [route_len: 1 byte] [route: N bytes] [msgpack payload]
```
- msg_type 6 = notify with route (typically "onMsg")

### Game Events
| Event | Description |
|-------|-------------|
| `gameinfo` | Table state, shared cards, pot |
| `moveturn` | Player action, contains hole cards in `game_seat` |
| `prompt` | Your turn to act |
| `countdown` | Action timer |
| `gameover` | Showdown results, all player cards revealed |

### Card Data Locations
- **Your cards**: `data.game_seat[UID].cards` in `moveturn` events
- **Board**: `data.game_info.shared_cards` in any event
- **All cards at showdown**: `data.game_result.seats[UID].cards` in `gameover`
- **Best hand**: `data.game_result.lightcards` + `data.game_result.patterns`

## Architecture

```
SupremaPoker.exe (Cocos2d-x + V8 JS engine)
    |
    |-- libssl-1_1.dll (SSL_read hooked via Frida)
    |
    v
suprema_realtime.py
    |-- Frida attach to process
    |-- SSL_read interceptor
    |-- WebSocket frame parser
    |-- Pomelo protocol parser
    |-- msgpack deserializer
    |-- Card ID decoder
    |-- Terminal display (cls + print)
```

## Disclaimer

This project is for educational and research purposes only. Use responsibly.
