# prbot/cli.py
import argparse
import os
import time
from rich.console import Console
from dotenv import load_dotenv

from prbot.github_client import (
    fetch_pr_context,
    upsert_bot_comment,
    list_merged_prs,
    parse_pr_url,
)
from prbot.extractors import extract_jira_keys
from prbot.store import (
    init_db,
    upsert_file_change,
    upsert_pr_outcome,
    list_outcomes,
)
from prbot.analyze import analyze_pr

load_dotenv()
console = Console()


def _require_github_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Missing GITHUB_TOKEN env var")
    return token


def _print_ai(ai: dict) -> None:
    # ai might be {"error": "..."} or the structured schema dict
    if not ai:
        return
    if "error" in ai:
        console.print(f"[yellow]AI summary unavailable: {ai['error']}[/yellow]")
        return

    console.print("\n[bold]AI reviewer summary[/bold]")
    console.print(f"- Decision: {ai['decision']} (confidence {ai['confidence']})")
    console.print(f"- Summary: {ai['summary']}")

    console.print("\n[bold]Key risks[/bold]")
    for r in ai.get("key_risks", []):
        console.print(f"- {r}")

    console.print("\n[bold]Mitigations[/bold]")
    for m in ai.get("mitigations", []):
        console.print(f"- {m}")

    t = ai.get("suggested_toggle")
    if t:
        console.print("\n[bold]Suggested toggle[/bold]")
        console.print(f"- recommended: {t['recommended']}")
        console.print(f"- scope: {t['scope']}, default: {t['default_state']}")
        for s in t.get("rollout_steps", []):
            console.print(f"  - {s}")

    if ai.get("questions_for_author"):
        console.print("\n[bold]Questions for author[/bold]")
        for q in ai["questions_for_author"]:
            console.print(f"- {q}")


def _upsert_analysis_row(analysis: dict) -> None:
    ctx = analysis["ctx"]
    result = analysis["result"]
    ai = analysis.get("ai")

    row = {
        "repo": ctx["repo_full"],
        "pr_number": ctx["pr_number"],
        "pr_url": ctx["url"],
        "analyzed_at": analysis["analyzed_at"],
        "risk_score": int(result.score),
        "risk_level": result.level,
        "toggle_recommendation": result.toggle,
    }

    if ai and isinstance(ai, dict) and "error" not in ai:
        row.update(
            {
                "ai_decision": ai.get("decision"),
                "ai_confidence": float(ai.get("confidence", 0.0)),
                "ai_summary": (ai.get("summary") or "")[:500],
            }
        )

    upsert_pr_outcome(row)


def main():
    parser = argparse.ArgumentParser(prog="prbot")
    sub = parser.add_subparsers(dest="cmd", required=True)

    review = sub.add_parser("review", help="Review a GitHub PR and recommend toggle.")
    review.add_argument("pr", help="PR URL like https://github.com/ORG/REPO/pull/123")
    review.add_argument("--comment", action="store_true", help="Post/update a PR comment with the result")
    review.add_argument("--ai", action="store_true", help="Add AI reviewer summary")

    index = sub.add_parser("index-pr", help="Index a merged PR into local file history DB.")
    index.add_argument("pr", help="PR URL")

    idxrepo = sub.add_parser("index-repo", help="Index last N merged PRs from a repo into DB.")
    idxrepo.add_argument("repo", help="ORG/REPO")
    idxrepo.add_argument("--limit", type=int, default=200)

    out = sub.add_parser("outcome", help="Update PR outcome labels (toggle/regression).")
    out.add_argument("pr", help="PR URL")
    out.add_argument("--toggle-added", choices=["yes", "no"])
    out.add_argument("--regression", choices=["yes", "no"])
    out.add_argument("--regression-jira")
    out.add_argument("--notes")

    ev = sub.add_parser("eval-repo", help="Run review on last N merged PRs and store analysis rows.")
    ev.add_argument("repo", help="ORG/REPO")
    ev.add_argument("--limit", type=int, default=30)
    ev.add_argument("--ai", action="store_true")

    m = sub.add_parser("metrics", help="Show basic evaluation metrics from pr_outcomes.")
    m.add_argument("--repo")


    demo = sub.add_parser("demo", help="Run a guided demo flow on one PR + show metrics.")
    demo.add_argument("pr", help="PR URL to demo")
    demo.add_argument("--repo", help="Repo for metrics/eval (defaults from PR)")
    demo.add_argument("--label", choices=["safe", "regression"], default="safe")
    demo.add_argument("--toggle", choices=["yes", "no"], default="no")
    demo.add_argument("--notes", default="Demo label")
    demo.add_argument("--eval-limit", type=int, default=10)
    demo.add_argument("--ai", action="store_true")


    tt = sub.add_parser("tune-thresholds", help="Auto-tune YES/NO thresholds from labeled outcomes.")
    tt.add_argument("--repo")
    tt.add_argument("--objective", choices=["f1", "recall", "precision", "fn"], default="f1")
    tt.add_argument("--write", action="store_true", help="Write best thresholds back to config.yaml")
    tt.add_argument("--max-unclear", type=float, default=0.6, help="Max fraction of rows allowed to be UNCLEAR")


    args = parser.parse_args()
    token = _require_github_token()

    if args.cmd == "tune-thresholds":
        init_db()
        from prbot.store import list_labeled_outcomes
        from prbot.tuning import sweep_thresholds
        from prbot.settings import load_settings, save_settings  # adjust to your loader module name

        rows = list_labeled_outcomes(args.repo)
        if len(rows) < 10:
            console.print(f"[yellow]Only {len(rows)} labeled rows. Results may be noisy.[/yellow]")

        # Reasonable ranges to try
        yes_range = range(50, 91, 5)   # 50..90
        no_range  = range(10, 51, 5)   # 10..50

        best, ranked = sweep_thresholds(
            rows,
            yes_range=yes_range,
            no_range=no_range,
            objective=args.objective,
            max_unclear_ratio=args.max_unclear,
        )

        console.print(f"[bold]Repo filter:[/bold] {args.repo or 'ALL'}")
        console.print(f"[bold]Objective:[/bold] {args.objective}")
        console.print(f"[bold]Best thresholds:[/bold] yes={best.yes_threshold}  no={best.no_threshold}")
        console.print(f"- Precision: {best.precision:.2f}")
        console.print(f"- Recall:    {best.recall:.2f}")
        console.print(f"- F1:        {best.f1:.2f}")
        console.print(f"- TP={best.tp} FP={best.fp} FN={best.fn} TN={best.tn} UNCLEAR={best.unclear}")

        console.print("\n[bold]Top 5 candidates[/bold]")
        for r in ranked[:5]:
            console.print(
                f"- yes={r.yes_threshold:>2} no={r.no_threshold:>2} "
                f"F1={r.f1:.2f} P={r.precision:.2f} R={r.recall:.2f} "
                f"FN={r.fn} FP={r.fp} UNCLEAR={r.unclear}"
            )

        if args.write:
            cfg = load_settings()
            cfg.setdefault("threshold", {})
            print(cfg["threshold"]["foryes"])
            cfg["threshold"]["foryes"] = int(best.yes_threshold)
            cfg["threshold"]["forno"] = int(best.no_threshold)
            save_settings(cfg)
            print(cfg["threshold"]["foryes"])
            console.print(f"\n[green]Wrote thresholds to config.yaml: yes={best.yes_threshold}, no={best.no_threshold}[/green]")
        else:
            console.print("\n[yellow]Dry-run only. Re-run with --write to update config.yaml[/yellow]")

        return


    if args.cmd == "demo":
        init_db()

        console.print("[bold]1) Analyze PR[/bold]")
        analysis = analyze_pr(token, args.pr, with_ai=args.ai)
        _upsert_analysis_row(analysis)

        ctx = analysis["ctx"]
        repo = args.repo or ctx["repo_full"]
        console.print(f"- Repo: {repo}")
        console.print(f"- PR:   {ctx['url']}")
        console.print(f"- Risk: {analysis['result'].score}/100 ({analysis['result'].level})")
        console.print(f"- Toggle recommendation: {analysis['result'].toggle}")

        if args.ai:
            _print_ai(analysis.get("ai"))

        console.print("\n[bold]2) Label outcome (simulate reality)[/bold]")
        repo_full, pr_number = parse_pr_url(args.pr)

        row = {
            "repo": repo_full,
            "pr_number": pr_number,
            "pr_url": args.pr,
            "toggle_added": 1 if args.toggle == "yes" else 0,
            "regression": 1 if args.label == "regression" else 0,
            "notes": args.notes,
        }
        upsert_pr_outcome(row)
        console.print(f"- toggle_added={args.toggle}, regression={args.label}")

        console.print("\n[bold]3) Evaluate small batch + show metrics[/bold]")
        merged_prs = list_merged_prs(token, repo, limit=args.eval_limit)
        for pr in merged_prs:
            a = analyze_pr(token, pr.html_url, with_ai=False)
            _upsert_analysis_row(a)
            time.sleep(0.2)

        # call your existing metrics logic inline or refactor metrics into a helper function
        console.print("\n[bold]4) Metrics[/bold]")
        # simplest: just tell the user to run:
        console.print(f"Run: python -m prbot metrics --repo {repo}")
        return


    # ---- Commands dispatch (single path) ----
    if args.cmd == "outcome":
        init_db()
        repo_full, pr_number = parse_pr_url(args.pr)

        row = {
            "repo": repo_full,
            "pr_number": pr_number,
            "pr_url": args.pr,
        }
        if args.toggle_added:
            row["toggle_added"] = 1 if args.toggle_added == "yes" else 0
        if args.regression:
            row["regression"] = 1 if args.regression == "yes" else 0
        if args.regression_jira:
            row["regression_jira"] = args.regression_jira
        if args.notes:
            row["notes"] = args.notes

        upsert_pr_outcome(row)
        console.print("[green]Outcome updated.[/green]")
        return

    if args.cmd == "metrics":
        init_db()
        rows = list_outcomes(args.repo)
        labeled = [r for r in rows if r["regression"] is not None]

        console.print(f"[bold]Repo filter:[/bold] {args.repo or 'ALL'}")
        console.print(f"[bold]Total analyses:[/bold] {len(rows)}")
        console.print(f"[bold]Labeled regressions:[/bold] {len(labeled)}")

        tp = fp = fn = tn = unclear = 0

        for r in labeled:
            pred = (r["toggle_recommendation"] or "").upper()
            actual_reg = int(r["regression"]) == 1

            if pred == "UNCLEAR":
                unclear += 1
                continue

            predicted_risky = pred == "YES"

            if predicted_risky and actual_reg:
                tp += 1
            elif predicted_risky and not actual_reg:
                fp += 1
            elif (not predicted_risky) and actual_reg:
                fn += 1
            else:
                tn += 1

        def safe_div(a, b):
            return a / b if b else 0.0

        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)

        console.print("\n[bold]Confusion matrix (excluding UNCLEAR)[/bold]")
        console.print(f"- TP: {tp}  FP: {fp}")
        console.print(f"- FN: {fn}  TN: {tn}")
        console.print(f"- UNCLEAR: {unclear}")

        console.print("\n[bold]Metrics[/bold]")
        console.print(f"- Precision: {precision:.2f}")
        console.print(f"- Recall:    {recall:.2f}")

        fns = [r for r in labeled if (r["toggle_recommendation"] or "").upper() == "NO" and int(r["regression"]) == 1]
        fps = [r for r in labeled if (r["toggle_recommendation"] or "").upper() == "YES" and int(r["regression"]) == 0]

        if fns:
            console.print("\n[bold]False negatives (missed regressions)[/bold]")
            for r in fns[:5]:
                console.print(f"- {r['repo']} #{r['pr_number']}  score={r['risk_score']}  {r['pr_url']}")
        if fps:
            console.print("\n[bold]False positives (over-flagged)[/bold]")
            for r in fps[:5]:
                console.print(f"- {r['repo']} #{r['pr_number']}  score={r['risk_score']}  {r['pr_url']}")

        return

    if args.cmd == "eval-repo":
        init_db()
        merged_prs = list_merged_prs(token, args.repo, limit=args.limit)
        console.print(f"[bold]Evaluating {len(merged_prs)} merged PRs[/bold]")

        for pr in merged_prs:
            pr_url = pr.html_url
            console.print(f"- {pr_url}")
            analysis = analyze_pr(token, pr_url, with_ai=args.ai)
            _upsert_analysis_row(analysis)
            time.sleep(0.2)

        console.print("[green]Eval batch complete.[/green]")
        return

    if args.cmd == "index-repo":
        init_db()
        console.print(f"[bold]Indexing merged PRs from {args.repo} (limit={args.limit})[/bold]")
        merged_prs = list_merged_prs(token, args.repo, limit=args.limit)
        console.print(f"Found {len(merged_prs)} merged PRs")

        indexed = 0
        for pr in merged_prs:
            ctx = fetch_pr_context(token, pr.html_url)
            if not ctx.get("merged"):
                continue

            title_body = (ctx["title"] + "\n" + ctx["body"]).lower()
            markers = [kw for kw in ["revert", "rollback", "hotfix", "incident", "sev"] if kw in title_body]

            jira_keys = extract_jira_keys([ctx["title"], ctx["body"]] + ctx.get("commit_messages", []))

            for fp in ctx["files"]:
                upsert_file_change(
                    repo=args.repo,
                    file_path=fp,
                    pr_number=ctx["pr_number"],
                    merged_at=ctx["merged_at_epoch"],
                    jira_keys=jira_keys,
                    markers=markers,
                    pr_url=ctx["url"],
                )

            indexed += 1
            console.print(f"  indexed PR #{ctx['pr_number']} ({len(ctx['files'])} files)")
            time.sleep(0.2)

        console.print(f"[green]Index complete: {indexed} PRs indexed[/green]")
        return

    if args.cmd == "index-pr":
        ctx = fetch_pr_context(token, args.pr)
        if not ctx.get("merged"):
            raise SystemExit("PR is not merged; only merged PRs should be indexed.")

        init_db()

        title_body = (ctx["title"] + "\n" + ctx["body"]).lower()
        markers = [kw for kw in ["revert", "rollback", "hotfix", "sev", "incident"] if kw in title_body]

        jira_keys = extract_jira_keys([ctx["title"], ctx["body"]] + ctx.get("commit_messages", []))

        merged_at = ctx["merged_at_epoch"]
        for fp in ctx["files"]:
            upsert_file_change(
                repo=ctx["repo_full"],
                file_path=fp,
                pr_number=ctx["pr_number"],
                merged_at=merged_at,
                jira_keys=jira_keys,
                markers=markers,
                pr_url=ctx["url"],
            )

        console.print(f"[green]Indexed PR #{ctx['pr_number']} ({len(ctx['files'])} files)[/green]")
        return

    if args.cmd == "review":
        analysis = analyze_pr(token, args.pr, with_ai=args.ai)
        ctx = analysis["ctx"]
        result = analysis["result"]
        hist = analysis["history"]
        jira_keys = analysis["jira_keys"]
        jira_details = analysis["jira_details"]
        ai = analysis.get("ai")

        # Print enrichment
        console.print("\n[bold]Jira enrichment[/bold]")
        if not jira_details:
            console.print("No Jira enrichment (no keys or Jira not configured).")
        else:
            for key, sig in jira_details:
                console.print(f"- {key}: {sig['issuetype']} | {sig['priority']} | {sig['status']} | risk {sig['risk_score']}/100")
                for r in sig["reasons"][:3]:
                    console.print(f"   - {r}")

        if args.ai:
            _print_ai(ai)

        console.print("\n[bold]History enrichment[/bold]")
        console.print(f"- Historical touches (last 180d): {hist['total_touches']}")
        console.print(f"- Hotfix/revert-like PRs: {hist['hotfix_like']}")
        console.print(f"- Max historical Jira risk: {hist['max_hist_jira_risk']}/100")
        if hist.get("historical_jira_keys"):
            console.print(f"- Sample historical Jira keys: {', '.join(hist['historical_jira_keys'][:10])}")

        # Print summary
        console.print(f"\n[bold]Repo:[/bold] {ctx['repo_full']}")
        console.print(f"[bold]PR:[/bold] #{ctx['pr_number']}  {ctx['url']}\n")
        console.print(f"[bold]Risk:[/bold] {result.score}/100  ([bold]{result.level}[/bold])")
        console.print(f"[bold]Toggle recommendation:[/bold] {result.toggle}\n")

        console.print("[bold]Stats[/bold]")
        console.print(f"- Files changed: {len(ctx['files'])}")
        console.print(f"- Lines: +{ctx['additions']} / -{ctx['deletions']} (total {ctx['additions']+ctx['deletions']})\n")

        console.print("[bold]Jira keys found[/bold]")
        console.print(", ".join(jira_keys) if jira_keys else "None\n")

        console.print("[bold]Evidence[/bold]")
        if result.evidence:
            for e in result.evidence:
                console.print(f"- {e}")
        else:
            console.print("- No strong risk signals detected.")

        if args.comment:
            upsert_bot_comment(token, ctx, result, jira_keys)
            console.print("\n[green]Posted/updated PR comment.[/green]")

        _upsert_analysis_row(analysis)
        return

    raise SystemExit(f"Unknown command: {args.cmd}")
