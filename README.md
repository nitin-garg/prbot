# PRBot  
**Explainable PR Risk Analysis with Feedback-Driven Learning**

PRBot is a **local-first PR risk analysis assistant** that helps answer one of the most common and subjective questions in software teams:

> **“Should this change be behind a feature toggle?”**

PRBot combines **deterministic engineering signals** (diff size, risky paths, history, incident patterns) with an **optional AI reasoning layer**, and it **learns over time** using real outcomes (regressions, hotfixes, rollbacks).

This project is designed to be:
- explainable
- measurable
- tunable
- safe by default

---

## What PRBot Does

For any pull request, PRBot can:

- Compute a **risk score (0–100)**
- Classify risk as **LOW / MEDIUM / HIGH**
- Recommend **YES / NO / UNCLEAR** for feature toggles
- Explain *why* using concrete evidence
- Optionally generate an **AI reviewer summary** (schema-constrained)
- Store outcomes and compute **precision / recall**
- Automatically **tune thresholds** from feedback

PRBot is **advisory only** — it never modifies code or PRs unless explicitly configured.

---

## Why This Exists

Deciding whether to add a feature toggle is often:
- subjective
- inconsistent across reviewers
- based on memory rather than data

PRBot brings:
- **consistency** (rules + policy)
- **context** (history + incidents)
- **explainability** (evidence + AI reasoning)
- **learning** (outcomes → metrics → tuning)

---

## Core Design Principles

- **Local-first**: Runs as a CLI; no mandatory SaaS or webhooks
- **Explainable**: Every recommendation has evidence
- **Human-in-the-loop**: Humans label outcomes; bot learns from them
- **Config-driven policy**: Tune behavior without code changes
- **AI as reasoning, not authority**: AI explains — rules decide

---

## Demo (5 Minutes)

### 1. Analyze a PR with AI explanation
```bash
python -m prbot demo https://github.com/org/repo/pull/123 --ai


### 2. Record what actually happened
```bash
python -m prbot outcome https://github.com/org/repo/pull/123 \
  --toggle-added no \
  --regression no \
  --notes "Shipped safely"

- This creates ground truth for learning.


### 3. Evaluate recent PRs
```bash
python -m prbot eval-repo org/repo --limit 20

### 4. View metrics
```bash
python -m prbot metrics --repo org/repo


- Outputs:

- confusion matrix

- precision / recall

- false positives

- false negatives


### 5. Auto-tune thresholds from feedback
```bash
python -m prbot tune-thresholds --repo org/repo --objective recall --write

- This updates policy automatically based on real outcomes.

