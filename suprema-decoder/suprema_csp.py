"""
CSP solver for Suprema Poker card encoding.
Find rank assignment f(card_id) -> rank such that all hand patterns are satisfied.
"""
import sys
from collections import Counter
from itertools import product
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RANKS = '23456789TJQKA'  # 0-12

# All constraints: (card_ids, pattern)
constraints = [
    ([46,45,66,22,52], "High card"),      # C1: prompt on flop
    ([22,29,34,61,66], "Two pairs"),       # C2: gameover main
    ([25,27,29,44,61], "One pair"),         # C3: gameover multi1
    ([45,46,62,74,78], "Three of a kind"), # C4: gameover multi2
    ([18,35,36,53,78], "Straight"),        # C5: old session
    ([28,56,60,72,76], "Full house"),      # C6: old session
    ([27,30,55,59,71], "Two pairs"),       # C7: old session
    ([26,28,41,42,58], "Three of a kind"), # C8: old session
    ([19,45,51,57,61], "Two pairs"),       # C9: new gameover
]

def check_pattern(ranks, pattern):
    c = Counter(ranks)
    vals = sorted(c.values())
    if pattern == "Straight":
        s = sorted(set(ranks))
        if len(s) != 5: return False
        if s[-1] - s[0] == 4: return True
        if s == [0, 1, 2, 3, 12]: return True
        return False
    elif pattern == "Full house":
        return vals == [2, 3]
    elif pattern == "Two pairs":
        return vals == [1, 2, 2]
    elif pattern == "Three of a kind":
        return vals == [1, 1, 3]
    elif pattern == "One pair":
        return vals == [1, 1, 1, 2]
    elif pattern == "High card":
        if len(set(ranks)) != 5: return False
        s = sorted(ranks)
        if s[-1] - s[0] == 4: return False
        if sorted(ranks) == [0, 1, 2, 3, 12]: return False
        return True
    return True

# Get all unique card IDs
all_ids = sorted(set(cid for cards, _ in constraints for cid in cards))
print(f"Unique card IDs: {len(all_ids)}")
print(f"IDs: {all_ids}")

# For each ID, possible ranks (0-12)
# Start with all possible, then eliminate
domains = {cid: set(range(13)) for cid in all_ids}

# Arc consistency: for each constraint, eliminate impossible values
def get_valid_rank_sets(cards, pattern):
    """Return list of valid rank tuples for the 5 cards given the pattern"""
    valid = []
    # For efficiency, enumerate based on pattern structure
    if pattern == "Straight":
        # 5 consecutive ranks
        for start in range(9):  # 2-high through T-high (0-8)
            # All 5! permutations of assignment
            from itertools import permutations
            straight = tuple(range(start, start+5))
            for perm in permutations(straight):
                valid.append(perm)
        # A-low: A,2,3,4,5 = (12,0,1,2,3)
        for perm in permutations((0,1,2,3,12)):
            valid.append(perm)
        return valid

    elif pattern == "Full house":
        # 3+2
        from itertools import combinations, permutations
        result = []
        for r1 in range(13):
            for r2 in range(13):
                if r1 == r2: continue
                # 3 positions get r1, 2 get r2
                for trip_pos in combinations(range(5), 3):
                    ranks = [0]*5
                    for p in trip_pos: ranks[p] = r1
                    for p in range(5):
                        if p not in trip_pos: ranks[p] = r2
                    result.append(tuple(ranks))
        return result

    elif pattern == "Two pairs":
        from itertools import combinations
        result = []
        for r1 in range(13):
            for r2 in range(r1+1, 13):
                for kicker in range(13):
                    if kicker == r1 or kicker == r2: continue
                    # Place pair1 (r1), pair2 (r2), kicker
                    for p1 in combinations(range(5), 2):
                        remaining = [i for i in range(5) if i not in p1]
                        for p2 in combinations(remaining, 2):
                            kp = [i for i in remaining if i not in p2]
                            ranks = [0]*5
                            for p in p1: ranks[p] = r1
                            for p in p2: ranks[p] = r2
                            ranks[kp[0]] = kicker
                            result.append(tuple(ranks))
        return result

    elif pattern == "Three of a kind":
        from itertools import combinations
        result = []
        for r1 in range(13):  # trips rank
            for k1 in range(13):
                if k1 == r1: continue
                for k2 in range(k1+1, 13):
                    if k2 == r1: continue
                    for tp in combinations(range(5), 3):
                        kp = [i for i in range(5) if i not in tp]
                        for ka, kb in [(k1,k2), (k2,k1)]:
                            ranks = [0]*5
                            for p in tp: ranks[p] = r1
                            ranks[kp[0]] = ka
                            ranks[kp[1]] = kb
                            result.append(tuple(ranks))
        return result

    elif pattern == "One pair":
        from itertools import combinations, permutations
        result = []
        for r1 in range(13):  # pair rank
            for kickers in combinations(range(13), 3):
                if r1 in kickers: continue
                for pp in combinations(range(5), 2):
                    kp = [i for i in range(5) if i not in pp]
                    for kperm in permutations(kickers):
                        ranks = [0]*5
                        for p in pp: ranks[p] = r1
                        for i, p in enumerate(kp):
                            ranks[p] = kperm[i]
                        result.append(tuple(ranks))
        return result

    elif pattern == "High card":
        # All distinct, not consecutive (not straight)
        # Too many to enumerate - handle differently
        return None

    return None

# Instead of enumerating all possibilities, use constraint propagation
# Approach: try rank = (id - offset) % N for various N and offset,
# but also check the High card constraint

print("\n=== EXHAUSTIVE FORMULA SEARCH (checking High card too) ===")
for N in range(4, 30):
    for offset in range(0, 80):
        works = True
        for cards, pattern in constraints:
            ranks = [(c - offset) % N for c in cards]
            if any(r >= 13 for r in ranks):
                works = False
                break
            if not check_pattern(ranks, pattern):
                works = False
                break
        if works:
            print(f"\n  *** N={N} offset={offset} WORKS (including High card)! ***")
            for cards, pattern in constraints:
                ranks = [(c - offset) % N for c in cards]
                print(f"    {pattern}: {cards} -> {[RANKS[r] for r in ranks]}")
            # Show full mapping for all known ids
            print(f"  Full mapping:")
            for cid in sorted(all_ids):
                r = (cid - offset) % N
                s = (cid - offset) // N
                print(f"    id={cid:2d} -> rank={RANKS[r]}({r}) suit_group={s}")

# Also try: rank = ((id - offset) // D) % 13
print("\n=== SEARCH: rank = ((id - offset) // D) % 13 ===")
for D in range(2, 10):
    for offset in range(0, 30):
        works = True
        for cards, pattern in constraints:
            ranks = [((c - offset) // D) % 13 for c in cards]
            if not check_pattern(ranks, pattern):
                works = False
                break
        if works:
            print(f"\n  *** D={D} offset={offset} WORKS! ***")
            for cards, pattern in constraints:
                ranks = [((c - offset) // D) % 13 for c in cards]
                print(f"    {pattern}: {cards} -> {[RANKS[r] for r in ranks]}")

# Also try: rank = (id * M + offset) % 13
print("\n=== SEARCH: rank = (id * M + offset) % 13 ===")
for M in range(1, 20):
    for offset in range(0, 13):
        works = True
        for cards, pattern in constraints:
            ranks = [(c * M + offset) % 13 for c in cards]
            if not check_pattern(ranks, pattern):
                works = False
                break
        if works:
            print(f"\n  *** M={M} offset={offset}: rank=(id*{M}+{offset})%13 WORKS! ***")
            for cards, pattern in constraints:
                ranks = [(c * M + offset) % 13 for c in cards]
                print(f"    {pattern}: {cards} -> {[RANKS[r] for r in ranks]}")
