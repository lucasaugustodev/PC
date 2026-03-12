"""
Constraint solver for Suprema Poker card encoding.
Uses showdown data where we know the hand pattern (Straight, Full house, etc.)
to deduce what each card value maps to.
"""
import sys
from itertools import permutations, combinations
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RANKS = '23456789TJQKA'  # 0-12
SUITS = 'cdhs'  # 0-3

def card_str(rank, suit):
    return RANKS[rank] + SUITS[suit]

# === SHOWDOWN DATA ===
# Hand #65: Straight (winner=588900)
# Player cards: [35, 51]
# Board: [53, 78, 18, 39, 36]
# Best 5 (lightcards): [18, 35, 36, 53, 78]
# Pattern: Straight

# Hand #58: Full house (winner=1482182)
# Winner cards: [60, 76], Loser cards: [73, 42]
# Board: [67, 72, 56, 28, 21]
# Best 5 (lightcards): [28, 56, 60, 72, 76]
# Pattern: Full house

# Hand #62: Two pairs (winner=1204674)
# Me cards: [18, 28] (loser), Winner cards: [42, 30]
# Board: [53, 71, 59, 27, 55]
# Best 5 (lightcards): [27, 30, 55, 59, 71]
# Pattern: Two pairs

# Hand #73: Three of a kind (winner=434061)
# Winner cards: [58, 26], Loser cards: [30, 23]
# Board: [70, 67, 42, 28, 41]
# Best 5 (lightcards): [26, 28, 41, 42, 58]
# Pattern: Three of a kind

def is_straight_ranks(ranks):
    """Check if 5 ranks form a straight"""
    s = sorted(set(ranks))
    if len(s) != 5:
        return False
    # Normal straight
    if s[-1] - s[0] == 4:
        return True
    # Ace-low: A,2,3,4,5 = {0,1,2,3,12}
    if s == [0, 1, 2, 3, 12]:
        return True
    return False

def is_full_house(ranks):
    """Check if 5 ranks form a full house (3+2)"""
    c = Counter(ranks)
    return sorted(c.values()) == [2, 3]

def is_two_pairs(ranks):
    """Check if 5 ranks form two pairs (2+2+1)"""
    c = Counter(ranks)
    return sorted(c.values()) == [1, 2, 2]

def is_three_of_kind(ranks):
    """Check if 5 ranks form three of a kind (3+1+1)"""
    c = Counter(ranks)
    return sorted(c.values()) == [1, 1, 3]

# All possible straights (as rank tuples)
STRAIGHTS = []
for start in range(9):  # 2-high through A-high
    STRAIGHTS.append(tuple(range(start, start+5)))
STRAIGHTS.append((0, 1, 2, 3, 12))  # A-low: A,2,3,4,5

print("=== STEP 1: Enumerate possible rank assignments for Straight ===")
print("Lightcards for Straight: [18, 35, 36, 53, 78]")
print()

straight_cards = [18, 35, 36, 53, 78]
straight_solutions = []

for straight_ranks in STRAIGHTS:
    # Try all permutations: assign each rank in the straight to each card value
    for perm in permutations(straight_ranks):
        rank_map = dict(zip(straight_cards, perm))
        straight_solutions.append(rank_map)

print(f"Total possible Straight rank assignments: {len(straight_solutions)}")
print()

print("=== STEP 2: Filter by Full House constraint ===")
fh_cards = [28, 56, 60, 72, 76]

# For each straight solution, try all possible rank assignments for the full house
# that are consistent (card 28 might already have a rank from another hand)
valid_after_fh = []

for s_sol in straight_solutions:
    # Cards in the straight that overlap with full house
    overlap = set(straight_cards) & set(fh_cards)

    # Card 28 is NOT in straight lightcards, so no overlap constraint from straight
    # But we need the full house to work independently
    # For now, just enumerate possible full house rank assignments

    # Full house: need to pick 2 ranks (one for trips, one for pair)
    # and assign to [28, 56, 60, 72, 76]
    for r1 in range(13):  # trips rank
        for r2 in range(13):  # pair rank
            if r1 == r2:
                continue
            # Assign: 3 cards get r1, 2 cards get r2
            # Which 3 of the 5 get the trips rank?
            for trips_combo in combinations(range(5), 3):
                pair_combo = [i for i in range(5) if i not in trips_combo]
                fh_map = {}
                for i in trips_combo:
                    fh_map[fh_cards[i]] = r1
                for i in pair_combo:
                    fh_map[fh_cards[i]] = r2

                # Check consistency with straight solution
                consistent = True
                for card, rank in fh_map.items():
                    if card in s_sol and s_sol[card] != rank:
                        consistent = False
                        break

                if consistent:
                    # Merge maps
                    merged = {**s_sol, **fh_map}
                    valid_after_fh.append(merged)

print(f"After Straight + Full House: {len(valid_after_fh)} solutions")

# That's probably too many. Let me add the other constraints too.
print()
print("=== STEP 3: Filter by Two Pairs constraint ===")
tp_cards = [27, 30, 55, 59, 71]

valid_after_tp = []
for sol in valid_after_fh:
    # Check overlap with existing solution
    tp_ranks = []
    unknown_tp = []
    for card in tp_cards:
        if card in sol:
            tp_ranks.append(sol[card])
        else:
            unknown_tp.append(card)

    if not unknown_tp:
        # All ranks known, just check
        all_ranks = tp_ranks
        if is_two_pairs(all_ranks):
            valid_after_tp.append(sol)
        continue

    # Need to find ranks for unknown cards such that result is two pairs
    # Two pairs: exactly 2+2+1 rank distribution
    # Try all possible ranks for unknowns
    for combo in combinations(range(13), len(unknown_tp)):
        for perm in permutations(combo):
            test_ranks = tp_ranks + list(perm)
            if is_two_pairs(test_ranks):
                new_sol = {**sol}
                for card, rank in zip(unknown_tp, perm):
                    if card in new_sol and new_sol[card] != rank:
                        break
                    new_sol[card] = rank
                else:
                    valid_after_tp.append(new_sol)

print(f"After adding Two Pairs: {len(valid_after_tp)} solutions")

print()
print("=== STEP 4: Filter by Three of a Kind constraint ===")
tok_cards = [26, 28, 41, 42, 58]

valid_final = []
for sol in valid_after_tp:
    tok_ranks = []
    unknown_tok = []
    for card in tok_cards:
        if card in sol:
            tok_ranks.append(sol[card])
        else:
            unknown_tok.append(card)

    if not unknown_tok:
        if is_three_of_kind(tok_ranks):
            valid_final.append(sol)
        continue

    for combo in combinations(range(13), len(unknown_tok)):
        for perm in permutations(combo):
            test_ranks = tok_ranks + list(perm)
            if is_three_of_kind(test_ranks):
                new_sol = {**sol}
                ok = True
                for card, rank in zip(unknown_tok, perm):
                    if card in new_sol and new_sol[card] != rank:
                        ok = False
                        break
                    new_sol[card] = rank
                if ok:
                    valid_final.append(new_sol)

print(f"After all 4 constraints: {len(valid_final)} solutions")

# Deduplicate
unique = []
seen = set()
for sol in valid_final:
    key = tuple(sorted(sol.items()))
    if key not in seen:
        seen.add(key)
        unique.append(sol)

print(f"Unique solutions: {len(unique)}")

if len(unique) <= 50:
    print()
    print("=== SOLUTIONS ===")
    for i, sol in enumerate(unique[:20]):
        cards_str = {v: RANKS[r] for v, r in sorted(sol.items())}
        print(f"\nSolution {i+1}:")
        # Show the straight
        s_ranks = [sol[c] for c in straight_cards]
        print(f"  Straight: {[RANKS[r] for r in s_ranks]} = {'-'.join(RANKS[r] for r in sorted(s_ranks))}")
        # Show full house
        fh_ranks = [sol[c] for c in fh_cards]
        c = Counter(fh_ranks)
        trips_r = [r for r, cnt in c.items() if cnt == 3][0]
        pair_r = [r for r, cnt in c.items() if cnt == 2][0]
        print(f"  Full house: {RANKS[trips_r]}s full of {RANKS[pair_r]}s")
        # Show two pairs
        tp_ranks_list = [sol[c] for c in tp_cards]
        c2 = Counter(tp_ranks_list)
        pairs = sorted([r for r, cnt in c2.items() if cnt == 2], reverse=True)
        kicker = [r for r, cnt in c2.items() if cnt == 1][0]
        print(f"  Two pairs: {RANKS[pairs[0]]}s and {RANKS[pairs[1]]}s, kicker {RANKS[kicker]}")
        # Show three of a kind
        tok_ranks_list = [sol[c] for c in tok_cards]
        c3 = Counter(tok_ranks_list)
        trip_r = [r for r, cnt in c3.items() if cnt == 3][0]
        kickers = sorted([r for r, cnt in c3.items() if cnt == 1], reverse=True)
        print(f"  Three of a kind: {RANKS[trip_r]}s, kickers {RANKS[kickers[0]]},{RANKS[kickers[1]]}")
        # Show full mapping
        print(f"  Rank map: {cards_str}")
elif len(unique) > 50:
    # Too many - let me count what's constrained
    print("\nToo many solutions. Checking which values have determined ranks...")
    all_values = set()
    for sol in unique:
        all_values.update(sol.keys())

    for val in sorted(all_values):
        ranks_seen = set(sol[val] for sol in unique if val in sol)
        if len(ranks_seen) == 1:
            r = list(ranks_seen)[0]
            print(f"  {val} -> ALWAYS rank {RANKS[r]} ({r})")
        elif len(ranks_seen) <= 3:
            print(f"  {val} -> ranks {{{', '.join(RANKS[r] for r in sorted(ranks_seen))}}}")
