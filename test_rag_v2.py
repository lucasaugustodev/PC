import os, sys, re, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ['HF_HOME'] = 'D:/poker-ai/hf_cache'
from datasets import load_dataset

ds = load_dataset('RZ412/PokerBench', cache_dir='D:/poker-ai/hf_cache')
train = ds['train']

RANK_MAP = {'ace':'A','king':'K','queen':'Q','jack':'J','ten':'T','nine':'9','eight':'8',
            'seven':'7','six':'6','five':'5','four':'4','three':'3','two':'2'}
SUIT_MAP = {'heart':'h','diamond':'d','spade':'s','club':'c'}
RANK_VAL = {'A':14,'K':13,'Q':12,'J':11,'T':10,'9':9,'8':8,'7':7,'6':6,'5':5,'4':4,'3':3,'2':2}

def parse_cards(text):
    cards = []
    for m in re.finditer(r'(ace|king|queen|jack|ten|nine|eight|seven|six|five|four|three|two)\s+of\s+(heart|diamond|spade|club)', text.lower()):
        cards.append(RANK_MAP[m.group(1)] + SUIT_MAP[m.group(2)])
    return cards

def extract(text):
    text_lower = text.lower()
    pos_m = re.search(r'your position is (\w+)', text_lower)
    pos = pos_m.group(1).upper() if pos_m else None

    hand_m = re.search(r'\[(.+?)\]', text)
    hero = []
    if hand_m:
        parts = re.split(r'\s+and\s+', hand_m.group(1), flags=re.I)
        for p in parts:
            c = parse_cards(p)
            hero.extend(c)

    all_cards = parse_cards(text)
    board = [c for c in all_cards if c not in hero][:5]

    street = 'preflop'
    if 'the river' in text_lower: street = 'river'
    elif 'the turn' in text_lower: street = 'turn'
    elif 'the flop' in text_lower: street = 'flop'

    pot = 0
    pot_m = re.search(r'pot size is ([\d.]+)', text_lower)
    if pot_m: pot = float(pot_m.group(1))

    to_call = 0
    before = text_lower.split('your turn')[0] if 'your turn' in text_lower else text_lower
    bets = re.findall(r'(?:bet|raise)\s+([\d.]+)', before)
    if bets: to_call = float(bets[-1])

    return {'pos':pos, 'hero':hero, 'board':board, 'street':street, 'pot':pot, 'to_call':to_call}

print('Indexing 50000 entries...')
t0 = time.time()
index = []
for i in range(50000):
    f = extract(train[i]['instruction'])
    f['answer'] = train[i]['output'].strip()
    f['idx'] = i
    index.append(f)
print('Done %d in %.1fs' % (len(index), time.time()-t0))

def hero_ranks(hero):
    return tuple(sorted(c[0] for c in hero))

def is_suited(hero):
    return len(hero)==2 and hero[0][1]==hero[1][1]

def find_similar(query, top_n=10):
    results = []
    q_ranks = hero_ranks(query['hero'])
    q_suited = is_suited(query['hero'])
    q_board_ranks = set(c[0] for c in query['board'])

    for f in index:
        if f['street'] != query['street']: continue

        score = 50
        f_ranks = hero_ranks(f['hero'])
        if q_ranks == f_ranks:
            score += 30
            if is_suited(f['hero']) == q_suited: score += 5
        elif len(q_ranks)==2 and len(f_ranks)==2:
            if q_ranks[0]==f_ranks[0] or q_ranks[1]==f_ranks[1]: score += 10
            diff = abs(RANK_VAL.get(q_ranks[0],0)-RANK_VAL.get(f_ranks[0],0)) + abs(RANK_VAL.get(q_ranks[1],0)-RANK_VAL.get(f_ranks[1],0))
            if diff <= 2: score += 8

        f_board_ranks = set(c[0] for c in f['board'])
        overlap = len(q_board_ranks & f_board_ranks)
        score += overlap * 8

        if query['board'] and f['board']:
            q_hi = max(RANK_VAL.get(c[0],0) for c in query['board'])
            f_hi = max(RANK_VAL.get(c[0],0) for c in f['board'])
            if abs(q_hi - f_hi) <= 1: score += 5

        if query['pos'] == f['pos']: score += 10
        if (query['to_call']>0) == (f['to_call']>0): score += 8

        if query['pot']>0 and f['pot']>0:
            ratio = min(query['pot'],f['pot'])/max(query['pot'],f['pot'])
            score += int(ratio * 5)

        if score > 60:
            results.append((score, f))

    results.sort(key=lambda x:-x[0])
    return results[:top_n]

# Test scenarios from PokerBench test set + our real hands
scenarios = [
    {'name': 'T4o pair of 4s turn (check avail)',
     'hero':['Ts','4d'], 'board':['8s','7s','4c','3d'], 'street':'turn', 'pos':'BB', 'pot':14, 'to_call':0},
    {'name': 'AQd turn Td6h4hKh facing 20 bet (expected: fold)',
     'hero':['As','Qd'], 'board':['Td','6h','4h','Kh'], 'street':'turn', 'pos':'SB', 'pot':36, 'to_call':20},
    {'name': 'KQ two pair turn QcAdKh3d (expected: check)',
     'hero':['Ks','Qh'], 'board':['Qc','Ad','Kh','3d'], 'street':'turn', 'pos':'BTN', 'pot':36, 'to_call':0},
    {'name': 'AhJc top pair river 4s4h3hJh8c (expected: bet 10)',
     'hero':['Ah','Jc'], 'board':['4s','4h','3h','Jh','8c'], 'street':'river', 'pos':'BTN', 'pot':13, 'to_call':0},
    {'name': '88 set river Th4c5dKd8c facing 72 (expected: call)',
     'hero':['8s','8h'], 'board':['Th','4c','5d','Kd','8c'], 'street':'river', 'pos':'CO', 'pot':165, 'to_call':72},
    {'name': 'QcTc straight turn Js8d3c9d (expected: bet 3)',
     'hero':['Qc','Tc'], 'board':['Js','8d','3c','9d'], 'street':'turn', 'pos':'BTN', 'pot':4, 'to_call':0},
    {'name': '75s straight river Td6h4hKh8c (expected: call)',
     'hero':['7s','5s'], 'board':['Td','6h','4h','Kh','8c'], 'street':'river', 'pos':'BB', 'pot':39, 'to_call':17},
    {'name': 'A5s gutshot+bdfd flop 4s4h3h facing raise (expected: call)',
     'hero':['As','5s'], 'board':['4s','4h','3h'], 'street':'turn', 'pos':'CO', 'pot':27, 'to_call':10},
    {'name': 'TT overpair turn 9s7s4c6s facing 29 (expected: raise)',
     'hero':['Ts','Tc'], 'board':['9s','7s','4c','6s'], 'street':'turn', 'pos':'BTN', 'pot':67, 'to_call':29},
    {'name': 'Kd9d flush river Js Ks 5d Jd 4d facing 80 (expected: call)',
     'hero':['Kd','9d'], 'board':['Js','Ks','5d','Jd','4d'], 'street':'river', 'pos':'BTN', 'pot':148, 'to_call':80},
]

print()
print('='*70)
print('RAG SIMULATION: PokerBench lookup for real poker spots')
print('='*70)

for s in scenarios:
    t0 = time.time()
    matches = find_similar(s)
    elapsed = time.time() - t0

    print()
    print('--- %s ---' % s['name'])
    print('Hero: %s | Board: %s | Pot: %.0f | Call: %.0f | Search: %.0fms' % (
        ' '.join(s['hero']), ' '.join(s['board']), s['pot'], s['to_call'], elapsed*1000))

    if matches:
        for j,(score,f) in enumerate(matches[:5]):
            print('  #%d (s=%d) %s on %s pos=%s pot=%.0f call=%.0f -> %s' % (
                j+1, score, ' '.join(f['hero']), ' '.join(f['board']),
                f['pos'], f['pot'], f['to_call'], f['answer']))

        acts = {}
        for _,f in matches[:10]:
            a = f['answer'].split()[0].lower()
            acts[a] = acts.get(a,0)+1
        print('  >>> CONSENSUS: %s' % dict(acts))
    else:
        print('  No matches!')
    print('-'*70)
