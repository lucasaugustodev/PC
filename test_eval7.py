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

def decide(equity, pot, to_call, can_check=False, can_raise=False):
    pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0

    if can_check and to_call == 0:
        if equity > 0.60:
            return 'RAISE (strong hand, bet for value)'
        else:
            return 'CHECK (free card)'

    if equity > 0.65:
        if can_raise:
            return 'RAISE (strong equity %.0f%%)' % (equity*100)
        else:
            return 'CALL (strong equity %.0f%%)' % (equity*100)
    elif equity > pot_odds and equity > 0.35:
        return 'CALL (equity %.0f%% > pot odds %.0f%%)' % (equity*100, pot_odds*100)
    elif can_check:
        return 'CHECK'
    else:
        return 'FOLD (equity %.0f%% < pot odds %.0f%%)' % (equity*100, pot_odds*100)

hands = [
    {'hero': ['Ts', '4d'], 'board': ['8s', '7s', '4c', '3d'], 'opps': 1, 'pot': 0.14, 'to_call': 0, 'can_check': True, 'can_raise': True, 'desc': 'Ts 4d | Board: 8s 7s 4c 3d (TURN) | cash'},
    {'hero': ['7s', 'Jd'], 'board': [], 'opps': 3, 'pot': 0.14, 'to_call': 0.02, 'can_check': False, 'can_raise': True, 'desc': '7s Jd | Preflop | 4 players | cash'},
    {'hero': ['5h', '8s'], 'board': [], 'opps': 1, 'pot': 1.5, 'to_call': 0.5, 'can_check': False, 'can_raise': True, 'desc': '5h 8s | Preflop HU | SNG bubble'},
    {'hero': ['Td', '8s'], 'board': [], 'opps': 1, 'pot': 2.6, 'to_call': 1.1, 'can_check': False, 'can_raise': True, 'desc': 'Td 8s | Preflop | MTT 9 players'},
    {'hero': ['5h', 'Jh'], 'board': [], 'opps': 1, 'pot': 2.5, 'to_call': 1.1, 'can_check': False, 'can_raise': True, 'desc': '5h Jh | Preflop HU | MTT'},
    {'hero': ['5h', 'Jh'], 'board': ['8h', 'Qc', 'Ac'], 'opps': 1, 'pot': 7.5, 'to_call': 3.1, 'can_check': False, 'can_raise': True, 'desc': '5h Jh | Board: 8h Qc Ac (FLOP) | MTT'},
    {'hero': ['2d', '9c'], 'board': [], 'opps': 3, 'pot': 62.1, 'to_call': 0, 'can_check': True, 'can_raise': True, 'desc': '2d 9c | Preflop | CHECK available | MTT'},
    {'hero': ['9c', '7h'], 'board': [], 'opps': 1, 'pot': 2.6, 'to_call': 1.1, 'can_check': False, 'can_raise': True, 'desc': '9c 7h | Preflop | MTT 561 left'},
    {'hero': ['9c', '7h'], 'board': ['2d', '8s', 'Jd'], 'opps': 1, 'pot': 10.6, 'to_call': 0, 'can_check': True, 'can_raise': True, 'desc': '9c 7h | Board: 2d 8s Jd (FLOP) | MTT check avail'},
    {'hero': ['Kh', 'As'], 'board': [], 'opps': 1, 'pot': 1.9, 'to_call': 1.1, 'can_check': False, 'can_raise': True, 'desc': 'Kh As | Preflop HU | ITM 3 left'},
    {'hero': ['7c', 'Ah'], 'board': [], 'opps': 1, 'pot': 2.8, 'to_call': 0.2, 'can_check': True, 'can_raise': True, 'desc': '7c Ah | Preflop | check avail | 5 left'},
]

print('='*70)
print('EVAL7 EQUITY-BASED DECISIONS vs LOGGED HANDS')
print('='*70)

for h in hands:
    eq = calc_equity(h['hero'], h['board'], h['opps'])
    decision = decide(eq, h['pot'], h['to_call'], h['can_check'], h['can_raise'])
    print()
    print('Hand: %s' % h['desc'])
    pot_odds = (h['to_call']/(h['pot']+h['to_call'])*100) if h['pot']+h['to_call'] > 0 else 0
    print('Equity: %.1f%% | Pot odds: %.1f%%' % (eq*100, pot_odds))
    print('>>> Decision: %s' % decision)
    print('-'*70)
