"""Catalog "twins": different wines whose reference photos are (nearly) the same image.

No image-based method can tell such wines apart, so they are reported separately
from the main accuracy metric (they stay in the index: a 1-in-N chance beats none).
"""
from __future__ import annotations

import numpy as np

TWIN_THRESHOLD = 0.99


def twin_groups(slugs: list[str], vectors: np.ndarray, threshold: float = TWIN_THRESHOLD) -> list[list[str]]:
    """Connected components of the graph "cosine >= threshold" (only groups of 2+ wines)."""
    n = len(slugs)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    sim = vectors @ vectors.T
    ii, jj = np.where(np.triu(sim, k=1) >= threshold)
    for i, j in zip(ii, jj):
        parent[find(i)] = find(j)

    groups: dict[int, list[str]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(slugs[i])
    return sorted((sorted(g) for g in groups.values() if len(g) > 1), key=lambda g: g[0])
