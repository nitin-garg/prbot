# Evaluation & Learning

This document describes how PRBot evaluates its own performance and incorporates feedback.

---

## What Is Being Evaluated

For each PR, PRBot records:

**Prediction**
- risk_score
- toggle_recommendation (YES / NO / UNCLEAR)

**Outcome**
- toggle_added (yes/no)
- regression (yes/no)
- optional regression Jira key

This creates labeled data.

---

## Definitions

**Regression**
- Bug, incident, rollback, or hotfix caused by the change

**False Positive**
- Bot recommended YES
- No regression occurred

**False Negative**
- Bot recommended NO
- Regression occurred

UNCLEAR predictions are tracked separately.

---

## Metrics Computed

- Precision
- Recall
- Confusion matrix
- False positives
- False negatives
- UNCLEAR rate

---

## Example Evaluation Results

Baseline policy:
- YES ≥ 70
- NO ≤ 35

Results (example):
- Precision: 0.42
- Recall: 0.55

After tuning (objective=recall):
- YES ≥ 60
- NO ≤ 30

Results:
- Precision: 0.35
- Recall: 0.75

Trade-off is explicit and configurable.

---

## Learning Approach

PRBot learns by:
1. Storing outcomes
2. Measuring errors
3. Adjusting thresholds via config
4. Re-evaluating

This avoids opaque retraining while remaining data-driven.

---

## Why This Matters

Many AI tools:
- cannot measure correctness
- cannot explain mistakes
- cannot improve safely

PRBot treats **evaluation as a first-class feature**.
