import numpy as np

from wine_ml.twins import twin_groups


def unit(v):
    v = np.asarray(v, np.float32)
    return v / np.linalg.norm(v)


def test_groups_are_transitive_and_skip_singletons():
    a = unit([1, 0, 0])
    a2 = unit([1, 0.01, 0])      # twin of a
    a3 = unit([1, 0.02, 0.0])    # twin of a2 -> same group
    b = unit([0, 1, 0])          # alone
    c = unit([0, 0, 1])
    c2 = unit([0, 0.01, 1])
    slugs = ["a", "a2", "a3", "b", "c", "c2"]
    groups = twin_groups(slugs, np.stack([a, a2, a3, b, c, c2]), threshold=0.99)
    assert groups == [["a", "a2", "a3"], ["c", "c2"]]


def test_no_twins():
    assert twin_groups(["x", "y"], np.stack([unit([1, 0]), unit([0, 1])])) == []
