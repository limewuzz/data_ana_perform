from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class PairwiseLabel:
    a: int
    b: int
    winner: int


def _ordered_pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def labels_from_groups(groups: list[list[int]]) -> list[PairwiseLabel]:
    labels: list[PairwiseLabel] = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            for winner in groups[i]:
                for loser in groups[j]:
                    a, b = _ordered_pair(winner, loser)
                    labels.append(PairwiseLabel(a=a, b=b, winner=winner))
    return labels


def cohen_kappa_binary(labels1: list[PairwiseLabel], labels2: list[PairwiseLabel]) -> float | None:
    if not labels1 or not labels2:
        return None

    m1 = {(l.a, l.b): l.winner for l in labels1}
    m2 = {(l.a, l.b): l.winner for l in labels2}
    common = [k for k in m1.keys() if k in m2]
    if not common:
        return None

    n11 = n10 = n01 = n00 = 0
    for a, b in common:
        w1 = m1[(a, b)]
        w2 = m2[(a, b)]
        p1 = 1 if w1 == a else 0
        p2 = 1 if w2 == a else 0
        if p1 == 1 and p2 == 1:
            n11 += 1
        elif p1 == 1 and p2 == 0:
            n10 += 1
        elif p1 == 0 and p2 == 1:
            n01 += 1
        else:
            n00 += 1

    n = n11 + n10 + n01 + n00
    if n == 0:
        return None

    p_o = (n11 + n00) / n
    p_yes1 = (n11 + n10) / n
    p_yes2 = (n11 + n01) / n
    p_no1 = 1 - p_yes1
    p_no2 = 1 - p_yes2
    p_e = p_yes1 * p_yes2 + p_no1 * p_no2
    if p_e == 1:
        return 1.0
    return (p_o - p_e) / (1 - p_e)


def average_pairwise_kappa(labels_by_annotator: dict[int, list[PairwiseLabel]]) -> float | None:
    annotators = sorted(labels_by_annotator.keys())
    if len(annotators) < 2:
        return None

    kappas: list[float] = []
    for a1, a2 in combinations(annotators, 2):
        k = cohen_kappa_binary(labels_by_annotator[a1], labels_by_annotator[a2])
        if k is not None:
            kappas.append(k)
    if not kappas:
        return None
    return sum(kappas) / len(kappas)


def average_kappa_per_annotator(labels_by_annotator: dict[int, list[PairwiseLabel]]) -> dict[int, float | None]:
    annotators = sorted(labels_by_annotator.keys())
    result: dict[int, float | None] = {a: None for a in annotators}
    if len(annotators) < 2:
        return result

    pairwise: dict[int, list[float]] = defaultdict(list)
    for a1, a2 in combinations(annotators, 2):
        k = cohen_kappa_binary(labels_by_annotator[a1], labels_by_annotator[a2])
        if k is None:
            continue
        pairwise[a1].append(k)
        pairwise[a2].append(k)

    for a, ks in pairwise.items():
        result[a] = sum(ks) / len(ks) if ks else None
    return result

