import os, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ['HF_HOME'] = 'D:/poker-ai/hf_cache'
import eval7
from datasets import load_dataset

RANK_VAL = {'A':14,'K':13,'Q':12,'J':11,'T':10,'9':9,'8':8,'7':7,'6':6,'5':5,'4':4,'3':3,'2':2}
RANK_MAP = {'ace':'A','king':'K','queen':'Q','jack':'J','ten':'T','nine':'9','eight':'8',
            'seven':'7','six':'6','five':'5','four':'4','three':'3','two':'2','deuce':'2'}
SUIT_MAP = {'heart':'h','hearts':'h','diamond':'d','diamonds':'d','spade':'s','spades':'s','club':'c','clubs':'c'}

def parse_written_card(text):
    """Parse 'King of Heart' or 'Ten Of Spade' to 'Kh'"""
    text = text.lower().strip()
    for rname, rchar in RANK_MAP.items():
        if text.startswith(rname):
            for sname, schar in SUIT_MAP.items():
                if sname in text:
                    return rchar + schar
    return None

def parse_hand(text):
    """Extract hero cards from '[King of Heart and Three of Heart]'"""
    m = re.search(r'\[(.+?)\]', text)
    if not m:
        return []
    inside = m.group(1)
    parts = re.split(r'\s+and\s+', inside, flags=re.I)
    cards = []
    for p in parts:
        c = parse_written_card(p)
        if c:
            cards.append(c)
    return cards

def parse_board(text):
    """Extract board cards from flop/turn/river descriptions."""
    board = []
    # Flop: "The flop comes Ten Of Heart, Three Of Spade, and Two Of Diamond"
    flop_m = re.search(r'flop comes?\s+(.+?)(?:,\s*then|\.\s)', text, re.I)
    if flop_m:
        flop_text = flop_m.group(1)
        parts = re.split(r',\s*(?:and\s+)?', flop_text, flags=re.I)
        for p in parts:
            p = p.replace(' and ', '').strip()
            c = parse_written_card(p)
            if c:
                board.append(c)

    # Turn: "The turn comes Five Of Diamond"
    turn_m = re.search(r'turn comes?\s+(\w+ Of \w+)', text, re.I)
    if turn_m:
        c = parse_written_card(turn_m.group(1))
        if c:
            board.append(c)

    # River: "The river comes Eight Of Club"
    river_m = re.search(r'river comes?\s+(\w+ Of \w+)', text, re.I)
    if river_m:
        c = parse_written_card(river_m.group(1))
        if c:
            board.append(c)

    return board

def calc_equity(hero_cards, board_cards, num_opponents=1, num_sims=5000):
    try:
        hero = [eval7.Card(c) for c in hero_cards]
        board = [eval7.Card(c) for c in board_cards] if board_cards else []
    except Exception as e:
        return 0.5

    wins = ties = total = 0
    for _ in range(num_sims):
        deck = eval7.Deck()
        for c in hero + board:
            try: deck.cards.remove(c)
            except: pass
        deck.shuffle()

        sim_board = board[:]
        idx = 0
        while len(sim_board) < 5:
            sim_board.append(deck.cards[idx])
            idx += 1

        opp_hands = []
        for _ in range(num_opponents):
            opp_hands.append([deck.cards[idx], deck.cards[idx+1]])
            idx += 2

        hero_score = eval7.evaluate(hero + sim_board)
        best_opp = max(eval7.evaluate(opp + sim_board) for opp in opp_hands)

        if hero_score > best_opp: wins += 1
        elif hero_score == best_opp: ties += 1
        total += 1

    return (wins + ties * 0.5) / total

def hand_tier(cards):
    r1 = RANK_VAL.get(cards[0][0], 0)
    r2 = RANK_VAL.get(cards[1][0], 0)
    hi, lo = max(r1,r2), min(r1,r2)
    suited = cards[0][1] == cards[1][1]
    pair = r1 == r2
    gap = hi - lo
    if pair and hi >= 12: return 1
    if hi == 14 and lo == 13: return 1
    if pair and hi >= 10: return 2
    if hi == 14 and lo >= 11 and suited: return 2
    if hi == 14 and lo == 12: return 2
    if hi == 13 and lo == 12 and suited: return 2
    if pair and hi >= 7: return 3
    if hi == 14 and lo >= 8 and suited: return 3
    if hi == 14 and lo == 10: return 3
    if hi >= 11 and lo >= 10 and suited: return 3
    if hi == 13 and lo == 12: return 3
    if suited and gap == 1 and lo >= 9: return 3
    if pair: return 4
    if hi == 14 and suited: return 4
    if suited and gap <= 2 and lo >= 6: return 4
    if hi >= 11 and lo >= 10: return 4
    return 5

def decide(equity, pot, to_call, can_check, num_opps, hero_cards, board):
    pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0
    is_preflop = len(board) == 0
    tier = hand_tier(hero_cards) if is_preflop else 0
    hu = num_opps == 1

    if is_preflop:
        if can_check and to_call == 0:
            if tier <= 2:
                return ('raise', pot * 0.75, 'premium in position')
            elif tier == 3:
                return ('raise', pot * 0.6, 'good hand, raise')
            return ('check', 0, 'free BB tier %d' % tier)
        if hu:
            if tier <= 2: return ('raise', pot * 0.75, 'premium HU')
            if tier == 3: return ('call', 0, 'playable HU')
            if tier == 4 and pot_odds < 0.30: return ('call', 0, 'speculative HU')
            if tier == 5 and equity > 0.42 and pot_odds < 0.28:
                return ('call', 0, 'wide HU eq %.0f%%' % (equity*100))
            return ('fold', 0, 'trash tier %d' % tier)
        else:
            if tier <= 2: return ('raise', pot * 0.75, 'premium')
            if tier == 3 and pot_odds < 0.25: return ('call', 0, 'playable')
            if tier == 4 and pot_odds < 0.15: return ('call', 0, 'speculative cheap')
            return ('fold', 0, 'not playable multiway tier %d' % tier)

    # Postflop
    if can_check and to_call == 0:
        if equity > 0.70:
            return ('raise', pot * 0.75, 'value bet eq %.0f%%' % (equity*100))
        elif equity > 0.55:
            return ('raise', pot * 0.5, 'semi-value eq %.0f%%' % (equity*100))
        return ('check', 0, 'no value eq %.0f%%' % (equity*100))

    margin = 0.05 if hu else 0.10
    if equity > 0.70:
        return ('raise', pot * 0.75, 'value raise eq %.0f%%' % (equity*100))
    elif equity > pot_odds + margin:
        return ('call', 0, 'eq %.0f%% > needed %.0f%%' % (equity*100, (pot_odds+margin)*100))
    elif can_check:
        return ('check', 0, 'eq %.0f%%' % (equity*100))
    return ('fold', 0, 'eq %.0f%% < needed %.0f%%' % (equity*100, (pot_odds+margin)*100))


# Load PokerBench
print('Loading PokerBench...')
ds = load_dataset('RZ412/PokerBench', cache_dir='D:/poker-ai/hf_cache')
test = ds['test']

correct = 0
total = 0

for i in range(30):
    ex = test[i]
    q = ex['instruction'].strip()
    expected = ex['output'].strip().lower()

    hero = parse_hand(q)
    board = parse_board(q)

    if len(hero) < 2:
        continue

    # Count opponents (6-max, subtract folders)
    folds = q.lower().count('folded') + len(re.findall(r'\b\w+ fold\b', q.lower()))
    num_opps = max(1, 5 - folds)  # 6 players - hero - folders

    # Pot
    pot = 0
    pot_m = re.search(r'pot size is ([\d.]+)', q)
    if pot_m: pot = float(pot_m.group(1))

    # To call
    to_call = 0
    # Last action before hero's turn
    actions = re.findall(r'(\w+)\s+(bet|raise|check|call|fold)\s*([\d.]*)', q.lower())
    if actions:
        last = actions[-1]
        if last[1] in ('bet', 'raise') and last[2]:
            to_call = float(last[2])

    can_check = 'check' in q.lower().split('your turn')[0][-100:] if 'your turn' in q.lower() else to_call == 0

    # If last action before hero was "check", hero can check
    if actions and actions[-1][1] == 'check':
        can_check = True
        to_call = 0

    eq = calc_equity(hero, board, num_opps)
    action, size, reason = decide(eq, pot, to_call, can_check, num_opps, hero, board)

    # Match expected
    exp_action = None
    exp_size = 0
    if 'fold' in expected: exp_action = 'fold'
    elif re.match(r'(bet|raise)\s*(\d+)', expected):
        exp_action = 'raise'
        m = re.search(r'(\d+)', expected)
        if m: exp_size = float(m.group(1))
    elif 'call' in expected: exp_action = 'call'
    elif 'check' in expected: exp_action = 'check'

    match = (action == exp_action)
    if match: correct += 1
    total += 1

    tag = '[OK]' if match else '[X]'

    size_str = ' %.1f chips' % size if size and action == 'raise' else ''
    exp_size_str = ' %d chips' % exp_size if exp_size else ''

    print()
    print('Q%d: %s | Board: %s | Eq: %.0f%% | Opps: %d | Pot: %.0f | Call: %.0f' % (
        i+1, ' '.join(hero), ' '.join(board) if board else '-', eq*100, num_opps, pot, to_call))
    print('  Expected: %s%s' % (expected, exp_size_str))
    print('  eval7:    %s%s | %s  %s' % (action.upper(), size_str, reason, tag))
    print('-'*70)

print()
print('='*70)
print('SCORE: %d/%d (%.0f%%)' % (correct, total, 100*correct/total if total else 0))
print('='*70)
