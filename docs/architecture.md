# PRBot Architecture

This document describes the **architecture, data flow, and design decisions** behind **PRBot**.

PRBot is intentionally designed as an **explainable, local-first, feedback-driven system**, not a black-box AI reviewer.

---

## 1. System Overview

PRBot analyzes pull requests and recommends whether a change should be protected by a **feature toggle**.  
It combines deterministic engineering signals with optional AI reasoning and improves over time using real outcomes.

### High-level flow

Pull Request
↓
Signal Extraction
↓
Deterministic Risk Engine
↓
(Optional) AI Reasoning Layer
↓
Outcome Storage
↓
Metrics & Evaluation
↓
Policy / Threshold Tuning


This flow is **intentional and linear**, with learning occurring only after outcomes are observed.

---

## 2. Design Goals

PRBot is built around these core principles:

- **Explainability**  
  Every recommendation must be traceable to concrete signals.

- **Safety by Default**  
  No autonomous code or PR modification.

- **Measurability**  
  Predictions are evaluated against real outcomes.

- **Tunability**  
  Behavior changes via configuration, not code changes.

- **Human-in-the-Loop Learning**  
  Humans provide feedback; the system adapts based on evidence.

---

## 3. Major Components

### 3.1 Command-Line Interface (`cli.py`)

**Role**
- Entry point for all user interactions.

**Responsibilities**
- Parse commands (`review`, `demo`, `outcome`, `metrics`, `eval-repo`, `tune-thresholds`)
- Format and display output
- Orchestrate calls to analysis and persistence layers

**Non-responsibilities**
- No scoring logic
- No learning logic
- No AI logic

The CLI is intentionally thin to keep behavior predictable and debuggable.

---

### 3.2 Analysis Pipeline (`analyze.py`)

**Role**
- Central, reusable analysis pipeline.

**Primary Function**
```python
analyze_pr(token, pr_url, with_ai=False)


This flow is **intentional and linear**, with learning occurring only after outcomes are observed.

---

## 2. Design Goals

PRBot is built around these core principles:

- **Explainability**  
  Every recommendation must be traceable to concrete signals.

- **Safety by Default**  
  No autonomous code or PR modification.

- **Measurability**  
  Predictions are evaluated against real outcomes.

- **Tunability**  
  Behavior changes via configuration, not code changes.

- **Human-in-the-Loop Learning**  
  Humans provide feedback; the system adapts based on evidence.

---

## 3. Major Components

### 3.1 Command-Line Interface (`cli.py`)

**Role**
- Entry point for all user interactions.

**Responsibilities**
- Parse commands (`review`, `demo`, `outcome`, `metrics`, `eval-repo`, `tune-thresholds`)
- Format and display output
- Orchestrate calls to analysis and persistence layers

**Non-responsibilities**
- No scoring logic
- No learning logic
- No AI logic

The CLI is intentionally thin to keep behavior predictable and debuggable.

---

### 3.2 Analysis Pipeline (`analyze.py`)

**Role**
- Central, reusable analysis pipeline.

**Primary Function**
```python
analyze_pr(token, pr_url, with_ai=False)

## 4. Signal Extraction
PRBot uses interpretable, human-readable signals, not embeddings or opaque features.

### 4.1 PR Signals
- Files changed
- Lines added / deleted
- Keywords in PR description and comments

### 4.2 Path-Based Signals
- API boundaries
- Controllers / resources
- Persistence layers (entities, repositories)
- Safe paths (tests, documentation)

### 4.3 Historical Signals
- File churn
- Past hotfixes or rollbacks
- Historical risk in the same area

### 4.4 Issue / Incident Signals (Optional)
- Issue type (defect, incident)
- Priority / severity
- Regression-related keywords
- Each signal contributes to risk in a transparent and explainable way.

## 5. Deterministic Risk Engine (risk.py)
Role 
-Compute a risk score and recommendation.

Inputs
- Extracted signals
- Historical score
- Issue bonus
- Policy configuration

Outputs
- score (0–100)
- level (LOW / MEDIUM / HIGH)
- toggle (YES / NO / UNCLEAR)
- evidence (human-readable reasons)

Key Property
- The risk engine is fully deterministic and explainable.

AI never decides the outcome.

## 6. Policy & Configuration (config.yaml)
Role
- Separate policy decisions from implementation logic.

Configuration Controls
- YES / NO thresholds
- Risk caps
- Risky vs safe paths
- Exemptions (e.g., tests-only changes)
- UNCLEAR behavior

Benefits
- Safe tuning without code changes
- Explicit, auditable policy
- Enables automatic threshold learning

## 7. AI Reasoning Layer (ai_explainer.py)
Role
- Explain implications of detected signals in human language.

Characteristics
- Optional
- Schema-constrained output
- Advisory only

Responsibilities
- Summarize risk context
- Explain why a change may be risky
- Highlight implications (API contracts, nullability, persistence)
- Ask clarifying questions

Non-responsibilities
- Does not change scores
- Does not override decisions
- Does not introduce new facts

AI is used for communication and reasoning, not authority.

## 8. Storage Layer (store.py)

PRBot uses SQLite for simplicity and portability.

### 8.1 file_changes
- Tracks file-level history
- Enables churn and hotspot detection

### 8.2 pr_outcomes
- Stores:
    - analysis results
    - AI summaries (optional)
    - human-labeled outcomes
- Forms the dataset for learning

This storage layer enables offline evaluation and learning.

## 9. Feedback Loop (Learning)
PRBot implements policy learning, not blind model retraining.

Analyze PR
   ↓
Store Prediction
   ↓
Human Labels Outcome
   ↓
Metrics Compare Prediction vs Reality
   ↓
Policy / Threshold Tuning
   ↓
Re-evaluate


Learning updates:
- thresholds
- weights
- exemptions
- Not model parameters.

This keeps learning:
- safe
- explainable
- auditable

## 10. Evaluation & Metrics
PRBot computes:
- Precision
- Recall
- Confusion matrix
- False positives
- False negatives
- UNCLEAR rate

These metrics answer the key question:
“Is the bot actually helping reduce regressions without adding noise?”

## 11. Threshold Auto-Tuning
PRBot can automatically tune decision thresholds using labeled outcomes:
- Sweep candidate YES / NO thresholds
- Evaluate each using precision, recall, or F1
- Select the best policy for a chosen objective
- Optionally write results back to config.yaml

This is real learning from feedback, not heuristics.

## 12. Bot vs Agent
PRBot Today (Bot)
- Reactive
- Advisory
- Single-pass execution
- Human-controlled

Future Agent Evolution
- Persistent memory
- Goal-driven behavior
- Confidence-based actions
- Guardrail-enforced autonomy

The architecture intentionally supports this evolution without redesign.

## 13. Why This Architecture Works
Many AI review tools fail because they:
- hallucinate feedback
- cannot explain decisions
- cannot measure correctness
- cannot improve safely

PRBot avoids these pitfalls by:
- grounding decisions in deterministic signals
- isolating AI to explanation
- storing outcomes explicitly
- tuning behavior via metrics and policy

## 14. Summary
PRBot is not just a PR analysis tool.
It is an example of:
- explainable AI system design
- feedback-driven learning
- safe automation patterns
- policy-first engineering

The architecture prioritizes trust, measurability, and controlled evolution over unchecked automation.