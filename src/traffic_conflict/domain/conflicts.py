"""Table conservative explicite des 12 mouvements du carrefour à droite.

Même approche : la dynamique de suivi SUMO impose l'espacement. Approches
opposées tout droit : compatibles. Deux tournants à droite : compatibles.
Les autres paires inter-approches sont traitées comme incompatibles, y compris
certains mouvements physiquement compatibles : hypothèse conservative V0.
"""
from itertools import product

APPROACHES = ("N", "E", "S", "W")
MOVEMENTS = ("STRAIGHT", "LEFT", "RIGHT")
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
COMPATIBILITY = {}
for first, second in product(product(APPROACHES, MOVEMENTS), repeat=2):
    a, am = first
    b, bm = second
    COMPATIBILITY[first, second] = (a == b or (am == bm == "RIGHT") or
                                         (OPPOSITE[a] == b and am == bm == "STRAIGHT"))


def incompatible(first, second):
    return not COMPATIBILITY[(first.approach, first.movement), (second.approach, second.movement)]
