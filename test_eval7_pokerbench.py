import os, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ['HF_HOME'] = 'D:/poker-ai/hf_cache'
import eval7
from datasets import load_dataset

RANK_VAL = {'A':14,'K':13,'Q':12,'J':11,'T':10,'9':9,'8':8,'7':7,'6':6,'5':5,'4':4,'3':3,'2':2}
SUIT_MAP = {'s':'s','h':'h','d':'d','c':'c','spades':'s','hearts':'h','diamonds':'d','clubs':'c'}

def parse_card(s):
    """Parse card like 'Ah', 'Kd', '10s', 'ace of spades' etc."""
    s = s.strip().replace('10','T')
    if len(s) == 2 and s[0] in RANK_VAL and s[1] in 'shdc':
        return s
    return None

def parse_cards_from_text(text):
    """Extract cards from poker scenario text."""
    cards = re.findall(r'\b([AKQJT2-9][shdc])\b', text)
    # Also try "10" format
    tens = re.findall(r'\b(10[shdc])\b', text)
    for t in tens:
        cards.append('T' + t[2])
    return cards

def calc_equity(hero_cards, board_cards, num_opponents=1, num_sims=5000):
    try:
        hero = [eval7.Card(c) for c in hero_cards]
        board = [eval7.Card(c) for c in board_cards] if board_cards else []
    except:
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

def decide_with_size(equity, pot, to_call, can_check, num_opps, hero_cards, board):
    """Returns (action, size_in_bb_or_pot_fraction, reason)"""
    pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0
    is_preflop = len(board) == 0
    tier = hand_tier(hero_cards) if is_preflop else 0
    hu = num_opps == 1

    # === PREFLOP ===
    if is_preflop:
        if can_check and to_call == 0:
            if tier <= 2:
                return ('raise', '3x', 'premium in BB, raise for value (tier %d)' % tier)
            elif tier == 3 and hu:
                return ('raise', '2.5x', 'good hand HU in BB (tier %d)' % tier)
            elif tier <= 4 and hu and equity > 0.52:
                return ('raise', '2.5x', 'HU aggression in BB (tier %d)' % tier)
            else:
                return ('check', None, 'free BB (tier %d)' % tier)

        if hu:
            if tier == 1:
                return ('raise', '3x', 'premium HU (tier 1)')
            elif tier == 2:
                return ('raise', '2.5x', 'strong HU (tier 2)')
            elif tier == 3:
                return ('call', None, 'playable HU (tier 3)')
            elif tier == 4:
                if pot_odds < 0.30:
                    return ('call', None, 'speculative HU, ok odds (tier 4)')
                return ('fold', None, 'speculative HU, bad odds (tier 4)')
            else:
                if equity > 0.42 and pot_odds < 0.28:
                    return ('call', None, 'HU wide call, eq %.0f%% (tier 5)' % (equity*100))
                hi = max(RANK_VAL.get(hero_cards[0][0],0), RANK_VAL.get(hero_cards[1][0],0))
                if hi >= 10 and pot_odds < 0.30:
                    return ('call', None, 'HU high card (tier 5)')
                return ('fold', None, 'trash HU (tier 5)')
        else:
            if tier == 1:
                return ('raise', '3x', 'premium multiway (tier 1)')
            elif tier == 2:
                return ('raise', '2.5x', 'strong multiway (tier 2)')
            elif tier == 3:
                if pot_odds < 0.25:
                    return ('call', None, 'playable, good odds (tier 3)')
                return ('fold', None, 'marginal multiway (tier 3)')
            elif tier == 4:
                if pot_odds < 0.15:
                    return ('call', None, 'speculative, cheap (tier 4)')
                return ('fold', None, 'speculative, expensive (tier 4)')
            return ('fold', None, 'trash multiway (tier 5)')

    # === POSTFLOP ===
    if can_check and to_call == 0:
        if equity > 0.70:
            size = '3/4 pot'
            return ('raise', size, 'strong value bet, eq %.0f%%' % (equity*100))
        elif equity > 0.55:
            size = '1/2 pot'
            return ('raise', size, 'semi-value bet, eq %.0f%%' % (equity*100))
        else:
            return ('check', None, 'no value to bet, eq %.0f%%' % (equity*100))

    margin = 0.05 if hu else 0.10
    if equity > 0.70:
        return ('raise', '3/4 pot', 'value raise, eq %.0f%%' % (equity*100))
    elif equity > pot_odds + margin:
        return ('call', None, 'eq %.0f%% > needed %.0f%%' % (equity*100, (pot_odds+margin)*100))
    elif can_check:
        return ('check', None, 'eq %.0f%%' % (equity*100))
    else:
        return ('fold', None, 'eq %.0f%% < needed %.0f%%' % (equity*100, (pot_odds+margin)*100))


# Load PokerBench
print('Loading PokerBench...')
ds = load_dataset('RZ412/PokerBench', cache_dir='D:/poker-ai/hf_cache')
test = ds['test']

correct = 0
total = 0
results = []

for i in range(30):
    ex = test[i]
    q = ex['instruction'].strip()
    expected = ex['output'].strip().lower()

    # Parse hero cards (first 2 cards mentioned are usually hero's)
    all_cards = parse_cards_from_text(q)
    if len(all_cards) < 2:
        continue

    hero = all_cards[:2]

    # Detect board cards
    board = []
    # Check for "board" or "community" or "flop/turn/river" keywords
    board_match = re.search(r'(?:board|community|flop|turn|river)[:\s]+', q, re.I)
    if board_match:
        after = q[board_match.end():]
        board_cards = parse_cards_from_text(after)
        board = board_cards[:5]  # max 5 board cards
    elif len(all_cards) > 2:
        # If more than 2 cards and context suggests board
        if 'flop' in q.lower() or 'turn' in q.lower() or 'river' in q.lower():
            board = all_cards[2:7]

    # Detect opponents
    num_opps = 1
    opp_match = re.search(r'(\d+)\s*(?:player|opponent|villain)', q, re.I)
    if opp_match:
        n = int(opp_match.group(1))
        if n > 1:
            num_opps = n - 1  # total players minus hero

    # Detect pot and to_call
    pot = 0
    pot_match = re.search(r'pot\s*(?:is|of|:)?\s*\$?(\d+\.?\d*)', q, re.I)
    if pot_match:
        pot = float(pot_match.group(1))

    to_call = 0
    call_match = re.search(r'(?:call|bet[s]?|raise[s]?)\s*(?:of|is|to)?\s*\$?(\d+\.?\d*)', q, re.I)
    if call_match:
        to_call = float(call_match.group(1))

    can_check = 'check' in q.lower() or to_call == 0

    # Calculate
    eq = calc_equity(hero, board, num_opps)
    action, size, reason = decide_with_size(eq, pot, to_call, can_check, num_opps, hero, board)

    # Check if our action matches expected
    exp_action = None
    if 'fold' in expected: exp_action = 'fold'
    elif 'raise' in expected or 'bet' in expected: exp_action = 'raise'
    elif 'call' in expected: exp_action = 'call'
    elif 'check' in expected: exp_action = 'check'
    elif 'all-in' in expected or 'all in' in expected: exp_action = 'raise'

    match = (action == exp_action) if exp_action else False
    if match: correct += 1
    total += 1

    tag = '[OK]' if match else '[X]'

    print()
    print('Q%d: %s' % (i+1, q[:150]))
    print('  Hero: %s | Board: %s | Equity: %.0f%% | Opps: %d' % (' '.join(hero), ' '.join(board) if board else '-', eq*100, num_opps))
    print('  Expected: %s' % expected[:80])
    size_str = ' SIZE: %s' % size if size else ''
    print('  eval7:    %s%s | %s  %s' % (action.upper(), size_str, reason, tag))
    print('-'*70)

print()
print('='*70)
print('Score: %d/%d (%.0f%%)' % (correct, total, 100*correct/total if total else 0))
print('='*70)
