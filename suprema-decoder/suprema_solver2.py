"""
Constraint-based card encoding solver for Suprema Poker.
Uses showdown data to deduce the mapping card_id -> (rank, suit).
"""
import sys, json
from collections import Counter, defaultdict
from itertools import combinations
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RANKS = '23456789TJQKA'  # indices 0-12

all_showdowns = [
    {"lightcards": [18, 35, 36, 53, 78], "pattern": "Straight"},
    {"lightcards": [28, 56, 60, 72, 76], "pattern": "Full house"},
    {"lightcards": [27, 30, 55, 59, 71], "pattern": "Two pairs"},
    {"lightcards": [26, 28, 41, 42, 58], "pattern": "Three of a kind"},
    {"lightcards": [22, 29, 34, 61, 66], "pattern": "Two pairs"},
    {"lightcards": [25, 27, 29, 44, 61], "pattern": "One pair"},
    {"lightcards": [45, 46, 62, 74, 78], "pattern": "Three of a kind"},
]

all_card_ids = set()
for sd in all_showdowns:
    all_card_ids.update(sd['lightcards'])

print(f"All card_ids seen: {sorted(all_card_ids)}")
print(f"Range: {min(all_card_ids)} - {max(all_card_ids)}, Count: {len(all_card_ids)}")

def rank_check(pattern, ranks):
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
        s = sorted(set(ranks))
        if len(s) != 5: return False
        if s[-1] - s[0] == 4: return False
        if s == [0, 1, 2, 3, 12]: return False
        return True
    return True

print("\n=== FORMULA SEARCH: rank = (id - offset) % N ===")
found = []
for N in range(4, 20):
    for offset in range(0, 80):
        works = True
        for sd in all_showdowns:
            ranks = [(c - offset) % N for c in sd['lightcards']]
            if any(r >= 13 for r in ranks):
                works = False
                break
            if not rank_check(sd['pattern'], ranks):
                works = False
                break
        if works:
            found.append((N, offset))
            print(f"\n  N={N} offset={offset}: rank=(id-{offset})%{N}")
            for sd in all_showdowns:
                ranks = [(c - offset) % N for c in sd['lightcards']]
                print(f"    {sd['pattern']}: {sd['lightcards']} -> {[RANKS[r] for r in ranks]}")

print(f"\nTotal working formulas: {len(found)}")

# Also try: rank = (id // D) % 13
print("\n=== FORMULA SEARCH: rank = (id // D) % 13 ===")
for D in range(1, 10):
    works = True
    for sd in all_showdowns:
        ranks = [(c // D) % 13 for c in sd['lightcards']]
        if not rank_check(sd['pattern'], ranks):
            works = False
            break
    if works:
        print(f"\n  D={D}: rank=(id//{D})%13")
        for sd in all_showdowns:
            ranks = [(c // D) % 13 for c in sd['lightcards']]
            print(f"    {sd['pattern']}: {sd['lightcards']} -> {[RANKS[r] for r in ranks]}")

# Try rank = id % 13 with various suit = id // 13
print("\n=== SIMPLE: rank = id % 13 ===")
works = True
for sd in all_showdowns:
    ranks = [c % 13 for c in sd['lightcards']]
    if not rank_check(sd['pattern'], ranks):
        works = False
        print(f"  FAILS on {sd['pattern']}: {sd['lightcards']} -> {[RANKS[r] for r in ranks]}")
if works:
    print("  WORKS!")

# Try with shuffled rank order
# What if the rank encoding is not 2,3,4,...,A but some other order?
# rank_table[i] = actual rank for i'th position
from itertools import permutations
print("\n=== PERMUTATION SEARCH (rank = id % N, but ranks are permuted) ===")
# This is too many permutations (13! = 6 billion)
# Instead, try to deduce from the Straight constraint
# Straight lightcards: [18, 35, 36, 53, 78]
# These 5 must have 5 consecutive ranks
# If rank = id % N, we need the remainders to be consecutive

for N in [4, 5, 6, 7, 8, 13, 14, 15, 16, 17, 18, 19, 20]:
    remainders = sorted([c % N for c in [18, 35, 36, 53, 78]])
    # Check if consecutive
    if len(set(remainders)) == 5:
        if remainders[-1] - remainders[0] == 4:
            print(f"  N={N}: Straight remainders {remainders} are consecutive!")
        elif set(remainders) == {0, 1, 2, 3, N-1}:
            print(f"  N={N}: Straight remainders {remainders} = A-low straight!")

# Try: rank = id % N for N where straight works, then check all
print("\n=== CHECKING N VALUES WHERE STRAIGHT WORKS ===")
straight_cards = [18, 35, 36, 53, 78]
for N in range(4, 30):
    rems = sorted([c % N for c in straight_cards])
    if len(set(rems)) != 5:
        continue
    is_consec = (rems[-1] - rems[0] == 4)
    is_alow = (set(rems) == {0, 1, 2, 3, N-1} and N-1 < 13)
    if not is_consec and not is_alow:
        continue

    # Now check all other hands with this N
    all_ok = True
    for sd in all_showdowns:
        ranks = [c % N for c in sd['lightcards']]
        if any(r >= 13 for r in ranks):
            all_ok = False
            break
        if not rank_check(sd['pattern'], ranks):
            all_ok = False
            break

    if all_ok:
        print(f"\n  *** N={N} works for ALL hands! ***")
        for sd in all_showdowns:
            ranks = [c % N for c in sd['lightcards']]
            print(f"    {sd['pattern']}: {sd['lightcards']} -> {[RANKS[r] for r in ranks]}")
    else:
        # Show why it fails
        for sd in all_showdowns:
            ranks = [c % N for c in sd['lightcards']]
            if any(r >= 13 for r in ranks) or not rank_check(sd['pattern'], ranks):
                print(f"  N={N}: fails on {sd['pattern']}: ranks={ranks}")
                break
