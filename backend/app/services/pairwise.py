from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Pairwise:
    chosen_id: int
    rejected_id: int
    rel: str


def deterministic_rng(seed: str) -> random.Random:
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    n = int.from_bytes(h[:8], "big", signed=False)
    return random.Random(n)


def to_groups(*, ranking: list[int], ranking_groups: list[list[int]] | None) -> list[list[int]]:
    if ranking_groups and len(ranking_groups) > 0:
        return ranking_groups
    return [[rid] for rid in ranking]


def pairwise_from_groups(*, groups: list[list[int]], tie_handling: str, seed: str) -> list[Pairwise]:
    pairs: list[Pairwise] = []

    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            for a in groups[i]:
                for b in groups[j]:
                    pairs.append(Pairwise(chosen_id=a, rejected_id=b, rel="ordered"))

    if tie_handling == "skip":
        return pairs

    if tie_handling != "random":
        return pairs

    rng = deterministic_rng(seed)
    for g in groups:
        if len(g) < 2:
            continue
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                x, y = g[i], g[j]
                if rng.random() < 0.5:
                    pairs.append(Pairwise(chosen_id=x, rejected_id=y, rel="tie"))
                else:
                    pairs.append(Pairwise(chosen_id=y, rejected_id=x, rel="tie"))

    return pairs
