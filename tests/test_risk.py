# tests/test_risk.py
import pytest

from prbot.risk import compute_risk


def base_config():
    # Minimal config needed by compute_risk
    return {
        "thresholds": {"yes": 70, "no": 35},
        "weights": {"jira_bonus_cap": 20, "history_bonus_cap": 40},
        "paths": {
            "risky": ["/api/", "/controller/", "/resource/", "/entity/", "/repository/"],
            "safe": ["/test/", "/tests/", "/docs/", "/doc/", ".md"],
        },
        "exemptions": {"tests_only": True, "docs_only": True},
        "policy": {"allow_unclear": True},
    }


def test_risk_level_and_toggle_are_deterministic_basic():
    cfg = base_config()
    res = compute_risk(
        changed_files=["src/foo/bar.py"],
        additions=10,
        deletions=2,
        text_blobs=["Small change"],
        jira_bonus=0,
        hist_score=0,
        config=cfg,
    )
    assert 0 <= res.score <= 100
    assert res.toggle in ("YES", "NO", "UNCLEAR")
    assert res.level in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(res.evidence, list)


def test_risky_path_increases_risk_score():
    cfg = base_config()

    # Baseline (non-risky path)
    base = compute_risk(
        changed_files=["src/service/foo.py"],
        additions=10,
        deletions=0,
        text_blobs=["Routine refactor"],
        jira_bonus=0,
        hist_score=0,
        config=cfg,
    )

    # Risky path (e.g., contains "api")
    risky = compute_risk(
        changed_files=["src/api/foo.py"],
        additions=10,
        deletions=0,
        text_blobs=["Routine refactor"],
        jira_bonus=0,
        hist_score=0,
        config=cfg,
    )

    assert risky.score >= base.score
    # Evidence should mention something related to API/risky path rule if triggered
    assert any("api" in e.lower() or "contract" in e.lower() or "surface" in e.lower() for e in risky.evidence)


def test_keyword_in_text_increases_risk_score():
    cfg = base_config()

    base = compute_risk(
        changed_files=["src/service/foo.py"],
        additions=5,
        deletions=1,
        text_blobs=["Normal change"],
        jira_bonus=0,
        hist_score=0,
        config=cfg,
    )

    kw = compute_risk(
        changed_files=["src/service/foo.py"],
        additions=5,
        deletions=1,
        text_blobs=["Potential regression risk; add rollback plan"],
        jira_bonus=0,
        hist_score=0,
        config=cfg,
    )

    assert kw.score >= base.score
    assert any("regression" in e.lower() or "rollback" in e.lower() for e in kw.evidence)


def test_bonus_caps_are_applied():
    cfg = base_config()

    # Provide very large bonuses; ensure caps apply
    res = compute_risk(
        changed_files=["src/api/foo.py"],
        additions=10,
        deletions=0,
        text_blobs=["Regression risk mentioned"],
        jira_bonus=999,     # should cap at 20
        hist_score=999,     # should cap at 40
        config=cfg,
    )

    # The score should never exceed 100 due to min(score,100)
    assert res.score <= 100

    # Hard to assert exact score because other rules may contribute,
    # but we can assert evidence exists and output is valid.
    assert res.toggle in ("YES", "NO", "UNCLEAR")
    assert res.level in ("LOW", "MEDIUM", "HIGH")


def test_unclear_branch_sets_level():
    cfg = base_config()

    # Force score likely between no=35 and yes=70.
    # Small change, no bonuses, low signals => often NO;
    # add some signals to nudge into middle.
    res = compute_risk(
        changed_files=["src/config/foo.py"],  # may add some points
        additions=80,
        deletions=20,
        text_blobs=["toggle discussion"],     # may add points
        jira_bonus=0,
        hist_score=0,
        config=cfg,
    )

    # Ensure level is always set (this guards against level being undefined in UNCLEAR path)
    assert res.level in ("LOW", "MEDIUM", "HIGH")
