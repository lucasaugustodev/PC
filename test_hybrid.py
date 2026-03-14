"""
Hybrid GTO Engine: eval7 equity + RAG (PokerBench) + hand tiers + LLM (Ollama poker-gto)
Test on 10 PokerBench spots with known correct answers.
"""
import os, sys, re, time, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ['HF_HOME'] = 'D:/poker-ai/hf_cache'
import eval7
from datasets import load_dataset

RANK_MAP = {'ace':'A','king':'K','queen':'Q','jack':'J','ten':'T','nine':'9','eight':'8',
            'seven':'7','six':'6','five':'5','four':'4','three':'3','two':'2'}
SUIT_MAP = {'heart':'h','diamond':'d','spade':'s','club':'c'}
RANK_VAL = {'A':14,'K':13,'Q':12,'J':11,'T':10,'9':9,'8':8,'7':7,'6':6,'5':5,'4':4,'3':3,'2':2}

# ===== EVAL7 EQUITY =====
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
            sim_board.append(deck.cards[idx]); idx += 1
        opp_hands = []
        for _ in range(num_opponents):
            opp_hands.append([deck.cards[idx], deck.cards[idx+1]]); idx += 2
        hero_score = eval7.evaluate(hero + sim_board)
        best_opp = max(eval7.evaluate(opp + sim_board) for opp in opp_hands)
        if hero_score > best_opp: wins += 1
        elif hero_score == best_opp: ties += 1
        total += 1
    return (wins + ties * 0.5) / total

# ===== HAND TIER (preflop) =====
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

# ===== EVAL7 DECISION =====
def eval7_decide(equity, pot, to_call, can_check, num_opps, hero, board):
    pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0
    is_pf = len(board) == 0
    hu = num_opps == 1
    if is_pf:
        tier = hand_tier(hero)
        if can_check and to_call == 0:
            if tier <= 2: return 'raise'
            if tier == 3 and hu: return 'raise'
            return 'check'
        if hu:
            if tier <= 2: return 'raise'
            if tier <= 4: return 'call'
            if equity > 0.42 and pot_odds < 0.28: return 'call'
            return 'fold'
        else:
            if tier <= 2: return 'raise'
            if tier == 3 and pot_odds < 0.25: return 'call'
            return 'fold'
    # Postflop
    if can_check and to_call == 0:
        if equity > 0.70: return 'raise'
        if equity > 0.55: return 'raise'
        return 'check'
    margin = 0.05 if hu else 0.10
    if equity > 0.70: return 'raise'
    if equity > pot_odds + margin: return 'call'
    if can_check: return 'check'
    return 'fold'

# ===== RAG (PokerBench lookup) =====
print('Loading PokerBench for RAG...')
ds = load_dataset('RZ412/PokerBench', cache_dir='D:/poker-ai/hf_cache')
train_data = ds['train']

def parse_cards_text(text):
    cards = []
    for m in re.finditer(r'(ace|king|queen|jack|ten|nine|eight|seven|six|five|four|three|two)\s+of\s+(heart|diamond|spade|club)', text.lower()):
        cards.append(RANK_MAP[m.group(1)] + SUIT_MAP[m.group(2)])
    return cards

def extract_features(text):
    text_lower = text.lower()
    pos_m = re.search(r'your position is (\w+)', text_lower)
    pos = pos_m.group(1).upper() if pos_m else None
    hand_m = re.search(r'\[(.+?)\]', text)
    hero = []
    if hand_m:
        for p in re.split(r'\s+and\s+', hand_m.group(1), flags=re.I):
            hero.extend(parse_cards_text(p))
    all_cards = parse_cards_text(text)
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
    return {'pos':pos,'hero':hero,'board':board,'street':street,'pot':pot,'to_call':to_call}

print('Indexing 50000 RAG entries...')
rag_index = []
for i in range(50000):
    f = extract_features(train_data[i]['instruction'])
    f['answer'] = train_data[i]['output'].strip()
    rag_index.append(f)
print('RAG ready.')

def rag_lookup(query, top_n=10):
    q_ranks = tuple(sorted(c[0] for c in query['hero']))
    q_suited = len(query['hero'])==2 and query['hero'][0][1]==query['hero'][1][1]
    q_board_ranks = set(c[0] for c in query['board'])
    results = []
    for f in rag_index:
        if f['street'] != query['street']: continue
        score = 50
        f_ranks = tuple(sorted(c[0] for c in f['hero']))
        if q_ranks == f_ranks:
            score += 30
            f_suited = len(f['hero'])==2 and f['hero'][0][1]==f['hero'][1][1]
            if q_suited == f_suited: score += 5
        elif len(q_ranks)==2 and len(f_ranks)==2:
            if q_ranks[0]==f_ranks[0] or q_ranks[1]==f_ranks[1]: score += 10
            diff = abs(RANK_VAL.get(q_ranks[0],0)-RANK_VAL.get(f_ranks[0],0)) + abs(RANK_VAL.get(q_ranks[1],0)-RANK_VAL.get(f_ranks[1],0))
            if diff <= 2: score += 8
        f_board_ranks = set(c[0] for c in f['board'])
        score += len(q_board_ranks & f_board_ranks) * 8
        if query['board'] and f['board']:
            q_hi = max((RANK_VAL.get(c[0],0) for c in query['board']), default=0)
            f_hi = max((RANK_VAL.get(c[0],0) for c in f['board']), default=0)
            if abs(q_hi - f_hi) <= 1: score += 5
        if query['pos'] == f['pos']: score += 10
        if (query['to_call']>0) == (f['to_call']>0): score += 8
        if score > 60:
            results.append((score, f))
    results.sort(key=lambda x:-x[0])
    # Return consensus action
    if not results:
        return None, {}
    acts = {}
    for _, f in results[:top_n]:
        a = f['answer'].split()[0].lower()
        # Normalize bet -> raise
        if a == 'bet': a = 'raise'
        acts[a] = acts.get(a, 0) + 1
    best = max(acts, key=acts.get)
    return best, acts

# ===== LLM (Ollama poker-gto) =====
def llm_decide(hero, board, pot, to_call, can_check, pos='BTN'):
    board_str = ' '.join(board) if board else 'none'
    street = 'PREFLOP' if not board else ('FLOP' if len(board)==3 else ('TURN' if len(board)==4 else 'RIVER'))
    prompt = 'Hero has [%s]. Board: [%s]. Street: %s. Pot: %.0f. To call: %.0f. Position: %s.' % (
        ' '.join(hero), board_str, street, pot, to_call, pos)
    if can_check:
        prompt += ' Check is available.'
    try:
        resp = requests.post('http://localhost:11434/api/generate', json={
            'model': 'poker-gto',
            'prompt': prompt,
            'system': 'You are a GTO poker advisor. Give the optimal action: fold, check, call, bet, or raise.',
            'stream': False,
            'options': {'temperature': 0.1, 'num_predict': 30},
        }, timeout=15)
        raw = resp.json().get('response', '').strip().lower()
        if 'fold' in raw[:30]: return 'fold'
        if 'raise' in raw[:30] or 'bet' in raw[:30]: return 'raise'
        if 'call' in raw[:30]: return 'call'
        if 'check' in raw[:30]: return 'check'
        return raw.split()[0] if raw else 'unknown'
    except:
        return 'error'

# ===== HYBRID DECISION =====
def hybrid_decide(hero, board, pot, to_call, can_check, num_opps, pos):
    votes = {}

    # 1. Eval7 equity
    equity = calc_equity(hero, board, num_opps)
    ev_action = eval7_decide(equity, pot, to_call, can_check, num_opps, hero, board)
    votes['eval7'] = ev_action

    # 2. RAG lookup
    street = 'preflop' if not board else ('flop' if len(board)==3 else ('turn' if len(board)==4 else 'river'))
    rag_action, rag_dist = rag_lookup({
        'hero': hero, 'board': board, 'street': street,
        'pos': pos, 'pot': pot, 'to_call': to_call
    })
    votes['rag'] = rag_action

    # 3. LLM (disabled - performs worse than eval7 and adds latency)
    # llm_action = llm_decide(hero, board, pot, to_call, can_check, pos)
    # votes['llm'] = llm_action

    # 4. Rules override
    rules_action = None
    pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0
    is_postflop = len(board) > 0
    facing_bet = to_call > 0

    # Rule: never fold when can check
    if can_check and to_call == 0:
        for k in votes:
            if votes[k] == 'fold':
                votes[k] = 'check'

    # Rule: equity < 15% and facing big bet, fold (clear trash)
    bet_ratio = to_call / pot if pot > 0 else 0
    if equity < 0.15 and pot_odds > 0.35 and not can_check:
        rules_action = 'fold'

    # Rule: nuts (>95%) facing big bet in big pot -> call (trap only with near-nuts)
    if is_postflop and equity > 0.95 and facing_bet and bet_ratio > 0.50 and pot > 50:
        rules_action = 'call'

    # Combine votes
    if rules_action:
        final = rules_action
        method = 'RULES'
    else:
        # Weighted voting: rag=3, eval7=2 (RAG outperforms eval7 50% vs 24%)
        tally = {}
        weights = {'eval7': 2, 'rag': 3}
        for src, act in votes.items():
            if act and act != 'error' and act != 'unknown':
                tally[act] = tally.get(act, 0) + weights.get(src, 1)
        if tally:
            final = max(tally, key=tally.get)
            method = 'VOTE(%s)' % '+'.join('%s=%s' % (s,a) for s,a in votes.items())
        else:
            final = ev_action
            method = 'FALLBACK(eval7)'

    return final, equity, votes, rag_dist, method

# ===== TEST ON 10 POKERBENCH SPOTS =====
test_ds = ds['test']

# Pick 10 diverse spots from test set
test_indices = list(range(100))

print()
print('='*70)
print('HYBRID ENGINE TEST: eval7 + RAG + LLM + Rules')
print('='*70)

correct = {'hybrid':0, 'eval7':0, 'rag':0, 'llm':0}
total = 0

for idx in test_indices:
    ex = test_ds[idx]
    q = ex['instruction']
    expected_raw = ex['output'].strip().lower()

    # Parse expected
    if 'fold' in expected_raw: expected = 'fold'
    elif 'raise' in expected_raw or 'bet' in expected_raw: expected = 'raise'
    elif 'call' in expected_raw: expected = 'call'
    elif 'check' in expected_raw: expected = 'check'
    else: continue

    # Parse hand
    feat = extract_features(q)
    if len(feat['hero']) < 2: continue

    # Detect can_check
    can_check = feat['to_call'] == 0

    final, equity, votes, rag_dist, method = hybrid_decide(
        feat['hero'], feat['board'], feat['pot'], feat['to_call'],
        can_check, 1, feat['pos'] or 'BTN')

    total += 1
    if final == expected: correct['hybrid'] += 1
    if votes.get('eval7') == expected: correct['eval7'] += 1
    if votes.get('rag') == expected: correct['rag'] += 1
    # llm disabled
    # llm disabled

    tag = '[OK]' if final == expected else '[X]'

    print()
    print('Q%d: %s on %s | eq=%.0f%% | pot=%.0f call=%.0f' % (
        idx+1, ' '.join(feat['hero']), ' '.join(feat['board']) if feat['board'] else 'preflop',
        equity*100, feat['pot'], feat['to_call']))
    print('  Expected: %-8s | eval7: %-8s | RAG: %-8s' % (
        expected, votes.get('eval7','?'), votes.get('rag','?') or 'n/a'))
    if rag_dist:
        print('  RAG dist: %s' % rag_dist)
    print('  >>> HYBRID: %-8s %s  %s' % (final.upper(), method, tag))
    print('-'*70)

print()
print('='*70)
print('FINAL SCORES (%d spots):' % total)
print('  Hybrid (combined): %d/%d (%.0f%%)' % (correct['hybrid'], total, 100*correct['hybrid']/total if total else 0))
print('  eval7 alone:       %d/%d (%.0f%%)' % (correct['eval7'], total, 100*correct['eval7']/total if total else 0))
print('  RAG alone:         %d/%d (%.0f%%)' % (correct['rag'], total, 100*correct['rag']/total if total else 0))
print('  LLM alone:         %d/%d (%.0f%%)' % (correct['llm'], total, 100*correct['llm']/total if total else 0))
print('='*70)
