# PRBot Design Decisions

This document captures the **key architectural and product decisions** made while building PRBot, along with the reasoning behind them.

The goal of this document is to explain *why* PRBot is designed the way it is — not just *how* it works.

---

## 1. Local-First CLI Instead of a Hosted Service

**Decision**  
PRBot is implemented as a local CLI tool, not a hosted SaaS or always-on service.

**Why**
- Enables rapid experimentation without deployment friction
- Avoids security concerns around credentials and source code
- Works in restricted corporate environments
- Makes demos and evaluation reproducible

**Trade-offs**
- No automatic PR scanning
- Requires explicit invocation

**Future Option**
- Safe GitHub Action mode (comment-only, opt-in)

---

## 2. Deterministic Rules as the Decision Authority

**Decision**  
The final recommendation (YES / NO / UNCLEAR) is made by a deterministic rule engine.

**Why**
- Decisions must be explainable and predictable
- Reviewers need to trust recommendations
- Deterministic logic is auditable and debuggable

**Trade-offs**
- Requires manual tuning
- Less flexible than end-to-end ML

**Outcome**
- AI assists reasoning but never overrides rules

---

## 3. AI Used for Reasoning, Not Control

**Decision**  
Large language models are used only to **explain** and **contextualize** decisions.

**Why**
- LLMs are strong at reasoning and communication
- LLMs are weak at making consistent policy decisions
- Prevents hallucinated or unsafe actions

**Implementation**
- Schema-constrained AI output
- AI cannot change scores or decisions
- AI can only reference provided evidence

---

## 4. Explicit Evidence for Every Recommendation

**Decision**  
Every risk score and recommendation must include a list of evidence.

**Why**
- Builds trust with reviewers
- Makes debugging straightforward
- Enables learning from false positives/negatives

**Trade-offs**
- More implementation effort
- Slightly noisier output

**Outcome**
- Users can always answer “why did the bot say this?”

---

## 5. YES / NO / UNCLEAR Instead of Binary Decisions

**Decision**  
PRBot outputs three possible recommendations:
- YES
- NO
- UNCLEAR

**Why**
- Many PRs cannot be confidently classified
- UNCLEAR encourages human judgment
- Prevents forced, low-confidence recommendations

**Trade-offs**
- Metrics slightly more complex
- Requires policy guidance for UNCLEAR cases

**Outcome**
- Reduced false confidence
- Better collaboration with reviewers

---

## 6. Separate Analysis from Outcome Labeling

**Decision**  
PR analysis and outcome labeling are separate commands and data fields.

**Why**
- Outcomes often happen days or weeks later
- Analysis must not depend on outcome availability
- Enables partial and delayed feedback

**Implementation**
- `review` stores predictions
- `outcome` stores ground truth

---

## 7. Feedback Stored Explicitly (Not Inferred)

**Decision**  
Outcomes (regression, toggle added) are explicitly labeled by humans.

**Why**
- Automatic inference is unreliable
- Ground truth must be deliberate
- Supports careful evaluation

**Trade-offs**
- Requires manual effort
- Smaller datasets initially

**Outcome**
- High-quality training and evaluation data

---

## 8. Learning via Policy Tuning, Not Model Retraining

**Decision**  
PRBot “learns” by tuning thresholds and weights, not retraining models.

**Why**
- Safer and more interpretable
- Easier to audit and rollback
- Works well with small datasets

**Implementation**
- Threshold sweep
- Precision/recall optimization
- Config updates via CLI

---

## 9. Configuration as Policy, Not Code

**Decision**  
Behavioral rules live in `config.yaml`, not in Python code.

**Why**
- Faster iteration
- Clear separation of concerns
- Makes decisions explicit and reviewable

**Trade-offs**
- Slightly more complex configuration handling

---

## 10. SQLite for Storage

**Decision**  
PRBot uses SQLite for persistence.

**Why**
- Zero setup
- Portable
- Sufficient for local learning and evaluation

**Trade-offs**
- Not suitable for large-scale concurrent access

**Future Option**
- Pluggable storage backend

---

## 11. Metrics as a First-Class Feature

**Decision**  
Metrics (precision, recall, false positives/negatives) are core features.

**Why**
- Without metrics, improvement is guesswork
- Enables data-driven tuning
- Builds confidence in the system

**Outcome**
- PRBot can answer “is this helping?”

---

## 12. Bot First, Agent Later

**Decision**  
PRBot is explicitly designed as a bot, not an autonomous agent.

**Why**
- Safer adoption
- Clear boundaries
- Easier to trust

**Future Option**
- Gradual evolution to agent behavior
- Guardrails enforced by confidence and policy

---

## 13. No Automatic PR Modification by Default

**Decision**  
PRBot never modifies PRs or code automatically.

**Why**
- Prevents unintended changes
- Maintains human control
- Avoids trust erosion

**Future Option**
- Opt-in, low-risk actions (labels, comments)

---

## 14. Demoability as a Design Constraint

**Decision**  
PRBot is designed to be demoable with a single command.

**Why**
- Demos drive understanding
- Enables stakeholder buy-in
- Encourages clarity of design

**Implementation**
- `demo` command
- Fixture-based offline demo support

---

## Summary

PRBot’s design prioritizes:
- trust over automation
- explanation over prediction
- measurement over intuition
- evolution over perfection

These decisions make PRBot suitable for real-world engineering teams and safe AI experimentation.
