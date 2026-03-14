import eval7

def calc_equity(hero_cards, board_cards, num_opponents=1, num_sims=10000):
    hero = [eval7.Card(c) for c in hero_cards]
    board = [eval7.Card(c) for c in board_cards] if board_cards else []

    wins = 0
    ties = 0
    total = 0

    for _ in range(num_sims):
        deck = eval7.Deck()
        for c in hero + board:
            deck.cards.remove(c)
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

        if hero_score > best_opp:
            wins += 1
        elif hero_score == best_opp:
            ties += 1
        total += 1

    return (wins + ties * 0.5) / total

# Preflop hand strength tier (1=premium, 5=trash)
RANK_VAL = {'A':14,'K':13,'Q':12,'J':11,'T':10,'9':9,'8':8,'7':7,'6':6,'5':5,'4':4,'3':3,'2':2}

def hand_tier(cards):
    """Rate preflop hand 1-5. 1=premium, 5=trash."""
    r1 = RANK_VAL.get(cards[0][0], 0)
    r2 = RANK_VAL.get(cards[1][0], 0)
    hi, lo = max(r1,r2), min(r1,r2)
    suited = cards[0][1] == cards[1][1]
    pair = r1 == r2
    gap = hi - lo

    # Tier 1: AA KK QQ AKs AKo
    if pair and hi >= 12: return 1
    if hi == 14 and lo == 13: return 1

    # Tier 2: JJ TT AQs AQo AJs KQs
    if pair and hi >= 10: return 2
    if hi == 14 and lo >= 11 and suited: return 2
    if hi == 14 and lo == 12: return 2
    if hi == 13 and lo == 12 and suited: return 2

    # Tier 3: 99-77, ATs-A8s, KJs, QJs, ATo, KQo, suited connectors T9s+
    if pair and hi >= 7: return 3
    if hi == 14 and lo >= 8 and suited: return 3
    if hi == 14 and lo == 10: return 3
    if hi >= 11 and lo >= 10 and suited: return 3
    if hi == 13 and lo == 12: return 3
    if suited and gap == 1 and lo >= 9: return 3

    # Tier 4: 66-22, suited Ax, suited connectors, broadways
    if pair: return 4
    if hi == 14 and suited: return 4
    if suited and gap <= 2 and lo >= 6: return 4
    if hi >= 11 and lo >= 10: return 4

    # Tier 5: trash
    return 5

def decide(equity, pot, to_call, can_check, can_raise, num_opps, hero_cards, board, is_preflop):
    pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0
    tier = hand_tier(hero_cards) if is_preflop else 0
    facing_bet = to_call > 0
    hu = num_opps == 1

    # === PREFLOP LOGIC ===
    if is_preflop:
        if can_check and not facing_bet:
            # In BB, no raise faced
            if tier <= 2:
                return 'RAISE (premium hand, tier %d)' % tier
            elif tier == 3 and hu:
                return 'RAISE (good hand HU, tier %d)' % tier
            else:
                return 'CHECK (free BB, tier %d)' % tier

        if facing_bet:
            # HU adjustments - much wider ranges
            if hu:
                if tier == 1:
                    return 'RAISE (premium HU, tier 1)'
                elif tier == 2:
                    return 'RAISE (strong HU, tier 2)'
                elif tier == 3:
                    return 'CALL (playable HU, tier 3)'
                elif tier == 4:
                    if pot_odds < 0.35:
                        return 'CALL (speculative HU, tier 4)'
                    else:
                        return 'FOLD (bad odds HU, tier 4)'
                else:  # tier 5
                    # HU: even trash can call if pot odds are good and has some equity
                    if equity > 0.40 and pot_odds < 0.30:
                        return 'CALL (HU wide call, equity %.0f%%, tier 5)' % (equity*100)
                    elif max(RANK_VAL.get(hero_cards[0][0],0), RANK_VAL.get(hero_cards[1][0],0)) >= 10:
                        return 'CALL (HU has high card, tier 5)'
                    else:
                        return 'FOLD (trash HU, tier 5)'
            else:
                # Multiway - tighter
                if tier == 1:
                    return 'RAISE (premium, tier 1)'
                elif tier == 2:
                    return 'CALL (strong multiway, tier 2)'
                elif tier == 3:
                    if pot_odds < 0.25:
                        return 'CALL (playable, good odds, tier 3)'
                    else:
                        return 'FOLD (marginal multiway, tier 3)'
                elif tier == 4:
                    if pot_odds < 0.15:
                        return 'CALL (speculative, cheap, tier 4)'
                    else:
                        return 'FOLD (speculative, bad odds, tier 4)'
                else:
                    return 'FOLD (trash multiway, tier 5)'

    # === POSTFLOP LOGIC ===
    if can_check and not facing_bet:
        if equity > 0.70:
            return 'RAISE (bet for value, equity %.0f%%)' % (equity*100)
        elif equity > 0.55:
            return 'RAISE (semi-value bet, equity %.0f%%)' % (equity*100)
        else:
            return 'CHECK (equity %.0f%%)' % (equity*100)

    if facing_bet:
        # Need equity > pot odds + margin
        margin = 0.05 if hu else 0.10
        if equity > 0.65:
            if can_raise:
                return 'RAISE (strong, equity %.0f%%)' % (equity*100)
            return 'CALL (strong, equity %.0f%%)' % (equity*100)
        elif equity > pot_odds + margin:
            return 'CALL (equity %.0f%% > needed %.0f%%)' % (equity*100, (pot_odds+margin)*100)
        elif can_check:
            return 'CHECK'
        else:
            return 'FOLD (equity %.0f%% < needed %.0f%%)' % (equity*100, (pot_odds+margin)*100)

    return 'CHECK' if can_check else 'FOLD'

hands = [
    {'hero': ['Ts', '4d'], 'board': ['8s', '7s', '4c', '3d'], 'opps': 1, 'pot': 0.14, 'to_call': 0, 'can_check': True, 'can_raise': True, 'desc': 'Ts 4d | Board: 8s 7s 4c 3d (TURN) | cash'},
    {'hero': ['7s', 'Jd'], 'board': [], 'opps': 3, 'pot': 0.14, 'to_call': 0.02, 'can_check': False, 'can_raise': True, 'desc': '7s Jd | Preflop | 4 players | cash'},
    {'hero': ['5h', '8s'], 'board': [], 'opps': 1, 'pot': 1.5, 'to_call': 0.5, 'can_check': False, 'can_raise': True, 'desc': '5h 8s | Preflop HU | SNG bubble'},
    {'hero': ['Td', '8s'], 'board': [], 'opps': 1, 'pot': 2.6, 'to_call': 1.1, 'can_check': False, 'can_raise': True, 'desc': 'Td 8s | Preflop HU | MTT 9 players'},
    {'hero': ['5h', 'Jh'], 'board': [], 'opps': 1, 'pot': 2.5, 'to_call': 1.1, 'can_check': False, 'can_raise': True, 'desc': '5h Jh | Preflop HU | MTT'},
    {'hero': ['5h', 'Jh'], 'board': ['8h', 'Qc', 'Ac'], 'opps': 1, 'pot': 7.5, 'to_call': 3.1, 'can_check': False, 'can_raise': True, 'desc': '5h Jh | Board: 8h Qc Ac (FLOP) | MTT flush draw'},
    {'hero': ['2d', '9c'], 'board': [], 'opps': 3, 'pot': 62.1, 'to_call': 0, 'can_check': True, 'can_raise': True, 'desc': '2d 9c | Preflop | CHECK available | MTT'},
    {'hero': ['9c', '7h'], 'board': [], 'opps': 1, 'pot': 2.6, 'to_call': 1.1, 'can_check': False, 'can_raise': True, 'desc': '9c 7h | Preflop HU | MTT 561 left'},
    {'hero': ['9c', '7h'], 'board': ['2d', '8s', 'Jd'], 'opps': 1, 'pot': 10.6, 'to_call': 0, 'can_check': True, 'can_raise': True, 'desc': '9c 7h | Board: 2d 8s Jd (FLOP) | gutshot'},
    {'hero': ['Kh', 'As'], 'board': [], 'opps': 1, 'pot': 1.9, 'to_call': 1.1, 'can_check': False, 'can_raise': True, 'desc': 'Kh As | Preflop HU | ITM 3 left'},
    {'hero': ['7c', 'Ah'], 'board': [], 'opps': 1, 'pot': 2.8, 'to_call': 0.2, 'can_check': True, 'can_raise': True, 'desc': '7c Ah | Preflop BB | check avail | 5 left'},
    {'hero': ['3h', 'Qc'], 'board': [], 'opps': 1, 'pot': 1.8, 'to_call': 0.6, 'can_check': False, 'can_raise': False, 'desc': '3h Qc | Preflop HU | only fold/allin'},
]

print('='*70)
print('EVAL7 v2: EQUITY + HAND TIERS + POSITION')
print('='*70)

for h in hands:
    is_pf = len(h['board']) == 0
    eq = calc_equity(h['hero'], h['board'], h['opps'])
    tier = hand_tier(h['hero']) if is_pf else '-'
    decision = decide(eq, h['pot'], h['to_call'], h['can_check'], h['can_raise'], h['opps'], h['hero'], h['board'], is_pf)
    pot_odds = (h['to_call']/(h['pot']+h['to_call'])*100) if h['pot']+h['to_call'] > 0 else 0
    print()
    print('Hand: %s' % h['desc'])
    print('Equity: %.1f%% | Pot odds: %.1f%% | Tier: %s' % (eq*100, pot_odds, tier))
    print('>>> %s' % decision)
    print('-'*70)
