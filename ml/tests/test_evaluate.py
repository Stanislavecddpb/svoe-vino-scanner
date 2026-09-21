import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("evaluate", Path(__file__).parents[1] / "scripts" / "evaluate.py")
evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate)


def test_combine_views_blends_full_with_best_label():
    full = np.array([[0.8, 0.6]])
    mid = np.array([[0.2, 0.9]])
    low = np.array([[0.7, 0.1]])
    s = evaluate.combine_views({"full": full, "label_mid": mid, "label_low": low}, 0.5)
    assert np.allclose(s, [[0.75, 0.75]])


def test_combine_views_full_only():
    full = np.array([[0.8, 0.6]])
    assert np.array_equal(evaluate.combine_views({"full": full}, 0.5), full)
