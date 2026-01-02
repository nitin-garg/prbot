# tests/test_tuning.py
import pytest

from prbot.tuning import evaluate_thresholds, sweep_thresholds


def make_rows(scores, regressions):
    """
    Build minimal pr_outcomes-like rows with risk_score + regression.
    """
    assert len(scores) == len(regressions)
    rows = []
    for s, r in zip(scores, regressions):
        rows.append({"risk_score": int(s), "regression": int(r)})
    return rows


def test_evaluate_thresholds_counts_make_sense():
    # Scores: 90, 80, 60, 40, 20
    # Regressions: 1, 1, 0, 0, 0
    rows = make_rows([90, 80, 60, 40, 20], [1, 1, 0, 0, 0])

    # yes>=70, no<=35 => predictions:
    # 90 YES (reg=1) -> TP
    # 80 YES (reg=1) -> TP
    # 60 UNCLEAR -> ignored in confusion matrix
    # 40 UNCLEAR (since >35 and <70) -> ignored
    # 20 NO (reg=0) -> TN
    res = evaluate_thresholds(rows, yes_t=70, no_t=35)

    assert res.tp == 2
    assert res.fp == 0
    assert res.fn == 0
    assert res.tn == 1
    assert res.unclear == 2

    # Precision and recall should be perfect here
    assert res.precision == pytest.approx(1.0)
    assert res.recall == pytest.approx(1.0)
    assert res.f1 == pytest.approx(1.0)


def test_sweep_thresholds_finds_valid_best():
    # Create a dataset where regressions tend to have high scores.
    rows = make_rows(
        scores=[95, 90, 85, 70, 65, 55, 45, 35, 25, 15],
        regressions=[1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
    )

    best, ranked = sweep_thresholds(
        rows,
        yes_range=range(50, 91, 10),  # 50,60,70,80,90
        no_range=range(10, 51, 10),   # 10,20,30,40,50
        objective="f1",
        max_unclear_ratio=0.9,        # allow plenty of unclear for this test
    )

    assert best.yes_threshold in range(50, 91, 10)
    assert best.no_threshold in range(10, 51, 10)
    assert best.no_threshold < best.yes_threshold

    # Ranked list should be non-empty and sorted by objective
    assert len(ranked) > 0
    assert ranked[0].f1 >= ranked[-1].f1


def test_sweep_thresholds_recall_objective_prefers_lower_yes_threshold():
    # In this dataset, some regressions have mid scores.
    rows = make_rows(
        scores=[90, 75, 65, 60, 55, 40, 30, 20],
        regressions=[1, 1, 1, 1, 0, 0, 0, 0],
    )

    best_recall, _ = sweep_thresholds(
        rows,
        yes_range=range(50, 91, 10),  # 50,60,70,80,90
        no_range=range(10, 41, 10),   # 10,20,30,40
        objective="recall",
        max_unclear_ratio=0.9,
    )

    # For recall, lower YES threshold often catches more regressions.
    assert best_recall.yes_threshold in (50, 60, 70)


def test_sweep_thresholds_respects_unclear_guardrail():
    rows = make_rows(
        scores=[60, 59, 58, 57, 56, 55, 54, 53],
        regressions=[1, 0, 1, 0, 1, 0, 1, 0],
    )

    # Very strict unclear guardrail might eliminate all options.
    with pytest.raises(RuntimeError):
        sweep_thresholds(
            rows,
            yes_range=range(70, 91, 10),
            no_range=range(10, 31, 10),
            objective="f1",
            max_unclear_ratio=0.0,  # no UNCLEAR allowed
        )
