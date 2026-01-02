from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

@dataclass
class TuneResult:
    yes_threshold: int
    no_threshold: int
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int
    tn: int
    unclear: int

def _predict(score: int, yes_t: int, no_t: int) -> str:
    if score >= yes_t:
        return "YES"
    if score <= no_t:
        return "NO"
    return "UNCLEAR"

def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0

def evaluate_thresholds(rows: List[Dict[str, Any]], yes_t: int, no_t: int) -> TuneResult:
    tp = fp = fn = tn = unclear = 0

    for r in rows:
        score = int(r["risk_score"])
        actual_reg = int(r["regression"]) == 1

        pred = _predict(score, yes_t, no_t)
        if pred == "UNCLEAR":
            unclear += 1
            continue

        predicted_risky = (pred == "YES")

        if predicted_risky and actual_reg:
            tp += 1
        elif predicted_risky and not actual_reg:
            fp += 1
        elif (not predicted_risky) and actual_reg:
            fn += 1
        else:
            tn += 1

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    return TuneResult(
        yes_threshold=yes_t,
        no_threshold=no_t,
        precision=precision,
        recall=recall,
        f1=f1,
        tp=tp, fp=fp, fn=fn, tn=tn,
        unclear=unclear,
    )

def sweep_thresholds(
    rows: List[Dict[str, Any]],
    yes_range: range,
    no_range: range,
    *,
    objective: str = "f1",
    max_unclear_ratio: float = 0.6,
) -> Tuple[TuneResult, List[TuneResult]]:
    """
    objective:
      - "f1": maximize f1
      - "recall": maximize recall (useful if you hate false negatives)
      - "precision": maximize precision (useful if you hate noise)
      - "fn": minimize false negatives
    """
    results: List[TuneResult] = []

    n = len(rows)
    for yes_t in yes_range:
        for no_t in no_range:
            if no_t >= yes_t:
                continue  # must have a gap for UNCLEAR

            res = evaluate_thresholds(rows, yes_t, no_t)

            # guardrail: don't allow tuning that makes everything UNCLEAR
            if n > 0 and (res.unclear / n) > max_unclear_ratio:
                continue

            results.append(res)

    if not results:
        raise RuntimeError("No threshold combinations passed constraints. Relax max_unclear_ratio or ranges.")

    def key_fn(r: TuneResult):
        if objective == "f1":
            return (r.f1, r.recall, r.precision)
        if objective == "recall":
            return (r.recall, r.f1, -r.fn)
        if objective == "precision":
            return (r.precision, r.f1, -r.fp)
        if objective == "fn":
            return (-r.fn, r.f1)
        raise ValueError(f"Unknown objective: {objective}")

    best = max(results, key=key_fn)
    # Sort for display
    results_sorted = sorted(results, key=key_fn, reverse=True)
    return best, results_sorted
