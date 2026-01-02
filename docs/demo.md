# PRBot Demo Script

This file is a **guided demo script**, not documentation.

Follow it line-by-line during a live demo.

---

## Step 1 — Analyze a PR

```bash
python -m prbot demo https://github.com/org/repo/pull/123 --ai

Explain:
- Risk score and toggle recommendation
- Evidence driving the score
- AI explains implications (schema-constrained)


## Step 2 — Label the Outcome

```bash
python -m prbot outcome https://github.com/org/repo/pull/123 \
  --toggle-added no \
  --regression no \
  --notes "Demo: shipped safely"

Explain:
- This creates ground truth
- Human judgment is explicit


## 3. Batch Evaluation
```bash
python -m prbot eval-repo org/repo --limit 10

Explain:
- Same analysis logic
- No duplication
- Scales across PRs

## 4. Metrics
```bash
python -m prbot metrics --repo org/repo

Explain:
- Precision / recall
- False positives / negatives
- UNCLEAR handling


## 5. Tune Policy
```bash
python -m prbot tune-thresholds --repo org/repo --objective recall --write

Explain:
- Feedback directly updates policy
- No code changes
- Safe learning loop


python -m prbot review https://github.com/UKGEPIC/scheduling-swap-request/pull/38043 --ai
python -m prbot outcome https://github.com/UKGEPIC/scheduling-swap-request/pull/38043 \
  --toggle-added no --regression no --notes "Demo: shipped safely"
python -m prbot eval-repo UKGEPIC/scheduling-swap-request --limit 5
python -m prbot metrics --repo UKGEPIC/scheduling-swap-request
