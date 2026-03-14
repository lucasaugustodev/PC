"""
Test: simulate RAG lookup on PokerBench 500k postflop spots
Pick real hands from our logs, find most similar spot in dataset, use that answer
"""
import os, sys, re, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ['HF_HOME'] = 'D:/poker-ai/hf_cache'
from datasets import load_dataset

print('Loading PokerBench...')
t0 = time.time()
ds = load_dataset('RZ412/PokerBench', cache_dir='D:/poker-ai/hf_cache')
train = ds['train']
test = ds['test']
print('Loaded %d train + %d test in %.1fs' % (len(train), len(test), time.time()-t0))

# Show dataset structure
print('\nSample train[0]:')
print('Keys:', list(train[0].keys()))
print('Instruction[:200]:', train[0]['instruction'][:200])
print('Output:', train[0]['output'][:100])

print('\nSample train[1000]:')
print('Instruction[:200]:', train[1000]['instruction'][:200])
print('Output:', train[1000]['output'][:100])

print('\nSample train[50000]:')
print('Instruction[:200]:', train[50000]['instruction'][:200])
print('Output:', train[50000]['output'][:100])

# Count action distribution
print('\n--- Action distribution (first 5000) ---')
actions = {}
for i in range(min(5000, len(train))):
    out = train[i]['output'].strip().lower()
    act = out.split()[0] if out else '?'
    actions[act] = actions.get(act, 0) + 1
for a, c in sorted(actions.items(), key=lambda x: -x[1]):
    print('  %s: %d (%.0f%%)' % (a, c, 100*c/5000))

# Now test: extract key features from a scenario for matching
RANK_MAP = {'ace':'A','king':'K','queen':'Q','jack':'J','ten':'T','nine':'9','eight':'8',
            'seven':'7','six':'6','five':'5','four':'4','three':'3','two':'2'}
SUIT_MAP = {'heart':'h','diamond':'d','spade':'s','club':'c'}

def extract_features(text):
    """Extract searchable features from PokerBench instruction."""
    text_lower = text.lower()

    # Position
    pos = None
    pos_m = re.search(r'your position is (\w+)', text_lower)
    if pos_m: pos = pos_m.group(1).upper()

    # Hero cards
    hero = []
    hand_m = re.search(r'\[(.+?)\]', text)
    if hand_m:
        parts = re.split(r'\s+and\s+', hand_m.group(1), flags=re.I)
        for p in parts:
            p = p.lower().strip()
            for rname, rchar in RANK_MAP.items():
                if p.startswith(rname):
                    for sname, schar in SUIT_MAP.items():
                        if sname in p:
                            hero.append(rchar + schar)

    # Street
    street = 'preflop'
    if 'river' in text_lower: street = 'river'
    elif 'turn' in text_lower: street = 'turn'
    elif 'flop' in text_lower: street = 'flop'

    # Board
    board = []
    for card_m in re.finditer(r'(ace|king|queen|jack|ten|nine|eight|seven|six|five|four|three|two)\s+of\s+(heart|diamond|spade|club)', text_lower):
        c = RANK_MAP[card_m.group(1)] + SUIT_MAP[card_m.group(2)]
        if c not in hero:
            board.append(c)
    # Remove duplicates, keep order
    seen = set()
    board_unique = []
    for c in board:
        if c not in seen:
            seen.add(c)
            board_unique.append(c)
    board = board_unique[:5]

    # Pot
    pot = 0
    pot_m = re.search(r'pot size is ([\d.]+)', text_lower)
    if pot_m: pot = float(pot_m.group(1))

    # Facing bet/raise amount
    to_call = 0
    # Look for last bet/raise before "your turn"
    before_turn = text_lower.split('your turn')[0] if 'your turn' in text_lower else text_lower
    bets = re.findall(r'(?:bet|raise)\s+([\d.]+)', before_turn)
    if bets: to_call = float(bets[-1])

    return {
        'pos': pos,
        'hero': hero,
        'street': street,
        'board': board,
        'pot': pot,
        'to_call': to_call,
        'hero_sorted': tuple(sorted(hero)),
    }

def similarity(f1, f2):
    """Score similarity between two feature dicts. Higher = more similar."""
    score = 0

    # Same street is critical
    if f1['street'] == f2['street']: score += 50
    else: return 0  # must match street

    # Same hero cards (rank only, ignore suit for wider matching)
    h1_ranks = tuple(sorted(c[0] for c in f1['hero']))
    h2_ranks = tuple(sorted(c[0] for c in f2['hero']))
    if h1_ranks == h2_ranks:
        score += 30
        # Suited match bonus
        if len(f1['hero']) == 2 and len(f2['hero']) == 2:
            s1 = f1['hero'][0][1] == f1['hero'][1][1]
            s2 = f2['hero'][0][1] == f2['hero'][1][1]
            if s1 == s2: score += 5
    elif len(h1_ranks) == 2 and len(h2_ranks) == 2:
        # Partial rank match
        if h1_ranks[0] == h2_ranks[0] or h1_ranks[1] == h2_ranks[1]:
            score += 10

    # Board texture similarity
    if f1['board'] and f2['board']:
        b1_ranks = set(c[0] for c in f1['board'])
        b2_ranks = set(c[0] for c in f2['board'])
        overlap = len(b1_ranks & b2_ranks)
        score += overlap * 5

        # High card similarity
        b1_high = max((RANK_MAP_REV.get(c[0], 0) for c in f1['board']), default=0)
        b2_high = max((RANK_MAP_REV.get(c[0], 0) for c in f2['board']), default=0)
        if abs(b1_high - b2_high) <= 1: score += 3

    # Position match
    if f1['pos'] == f2['pos']: score += 10

    # Pot size similarity (relative)
    if f1['pot'] > 0 and f2['pot'] > 0:
        ratio = min(f1['pot'], f2['pot']) / max(f1['pot'], f2['pot'])
        score += int(ratio * 10)

    # Facing bet similarity
    if (f1['to_call'] > 0) == (f2['to_call'] > 0): score += 5

    return score

RANK_MAP_REV = {'A':14,'K':13,'Q':12,'J':11,'T':10,'9':9,'8':8,'7':7,'6':6,'5':5,'4':4,'3':3,'2':2}

# ===============================================================
# TEST: Find best match for real hands from our logs
# ===============================================================

test_scenarios = [
    {
        'name': '97o preflop HU (the bad raise 4x hand)',
        'street': 'preflop', 'hero': ['9c','7h'], 'board': [],
        'pos': 'BB', 'pot': 2.6, 'to_call': 1.1,
    },
    {
        'name': 'Kh As preflop HU ITM',
        'street': 'preflop', 'hero': ['Kh','As'], 'board': [],
        'pos': 'SB', 'pot': 1.9, 'to_call': 1.1,
    },
    {
        'name': '5h Jh flush draw flop',
        'street': 'flop', 'hero': ['5h','Jh'], 'board': ['8h','Qc','Ac'],
        'pos': 'BTN', 'pot': 7.5, 'to_call': 3.1,
    },
    {
        'name': '9c 7h gutshot flop check avail',
        'street': 'flop', 'hero': ['9c','7h'], 'board': ['2d','8s','Jd'],
        'pos': 'BB', 'pot': 10.6, 'to_call': 0,
    },
    {
        'name': 'T4o pair of 4s turn',
        'street': 'turn', 'hero': ['Ts','4d'], 'board': ['8s','7s','4c','3d'],
        'pos': 'BB', 'pot': 0.14, 'to_call': 0,
    },
]

# Pre-extract features from dataset (sample for speed)
print('\nExtracting features from dataset...')
t0 = time.time()
SAMPLE_SIZE = 20000
dataset_features = []
for i in range(min(SAMPLE_SIZE, len(train))):
    f = extract_features(train[i]['instruction'])
    f['idx'] = i
    f['answer'] = train[i]['output'].strip()
    dataset_features.append(f)
print('Extracted %d features in %.1fs' % (len(dataset_features), time.time()-t0))

# Search
print('\n' + '='*70)
print('RAG SIMULATION: Finding best matches for real hands')
print('='*70)

for scenario in test_scenarios:
    query = {
        'street': scenario['street'],
        'hero': scenario['hero'],
        'board': scenario['board'],
        'pos': scenario['pos'],
        'pot': scenario['pot'],
        'to_call': scenario['to_call'],
        'hero_sorted': tuple(sorted(scenario['hero'])),
    }

    # Score all
    scored = []
    for df in dataset_features:
        s = similarity(query, df)
        if s > 0:
            scored.append((s, df))

    scored.sort(key=lambda x: -x[0])

    print('\n--- %s ---' % scenario['name'])
    print('Query: %s on %s | Pot: %.1f | Call: %.1f' % (
        ' '.join(scenario['hero']), ' '.join(scenario['board']) if scenario['board'] else 'preflop',
        scenario['pot'], scenario['to_call']))

    if scored:
        print('Top 5 matches:')
        for j, (score, df) in enumerate(scored[:5]):
            print('  #%d (score=%d): %s on %s | pos=%s | pot=%.0f | call=%.0f -> %s' % (
                j+1, score, ' '.join(df['hero']), ' '.join(df['board']) if df['board'] else 'preflop',
                df['pos'], df['pot'], df['to_call'], df['answer'][:50]))

        # Consensus from top matches
        top_actions = {}
        for score, df in scored[:10]:
            act = df['answer'].split()[0].lower()
            top_actions[act] = top_actions.get(act, 0) + 1
        print('  Consensus (top 10): %s' % dict(top_actions))
    else:
        print('  No matches found!')
