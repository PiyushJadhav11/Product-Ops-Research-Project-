"""Verification loop 2: deterministic rubric normalization (rubric v2.1).

Calibration sample A showed ~40% of pass-2 misses were not research errors but
inconsistent application of the verdict rubric (e.g. self-serve trial + 'ready_with_friction').
This re-derives verdict / blocker_type from the researched facts so every record obeys one rule.
Usage: python agent/normalize.py in.json out.json
"""
import json, sys


def normalize(r):
    r = dict(r)
    changes = []
    if r.get("verdict_locked"):  # human/adjudicator decision wins; only keep blocker_type consistent with it
        bt = r.get("blocker_type", "none")
        if r["verdict"] == "ready":
            nb = "none"
        elif bt in (None, "none"):
            nb = {"app_review": "app_review", "paid_plan": "paid_plan", "partner_gated": "partner_gate"}.get(r["access"], "other")
        else:
            nb = bt
        if nb != bt:
            changes.append(("blocker_type", bt, nb))
            r["blocker_type"] = nb
            if nb == "other" and r.get("blocker") in (None, "", "none"):
                r["blocker"] = "Human reviewer judged this ready_with_friction (see data/verify/human_spotcheck.csv)"
        return r, changes
    acc, bt = r["access"], r.get("blocker_type", "none")
    has_api = r.get("api_breadth") not in ("none", None) and r.get("api_type") not in ([], ["none"], None)
    mcp = r.get("official_mcp") == "yes"

    if bt == "not_a_saas_api":
        v = "blocked"
    elif acc == "partner_gated":
        v, bt = "blocked", "partner_gate"
    elif not has_api and not mcp:
        v, bt = "blocked", "no_public_api"
    elif not has_api and mcp:
        v, bt = "ready_with_friction", "no_public_api"        # MCP-only surface
    elif acc == "app_review":
        v, bt = "ready_with_friction", "app_review"
    elif acc == "paid_plan":
        v, bt = "ready_with_friction", "paid_plan"
    elif bt in ("per_tenant_setup",):
        v = "ready_with_friction"
    elif acc in ("self_serve_free", "self_serve_trial"):
        v, bt = "ready", "none"
    else:  # unknown access: leave verdict, mark for human
        v = r["verdict"]
        r["needs_human"] = True
    if v != r["verdict"]:
        changes.append(("verdict", r["verdict"], v))
    if bt != r.get("blocker_type"):
        changes.append(("blocker_type", r.get("blocker_type"), bt))
    r["verdict"], r["blocker_type"] = v, bt
    if v == "ready":
        r["blocker"] = "none"
    return r, changes


if __name__ == "__main__":
    recs = json.load(open(sys.argv[1]))
    out, log = [], []
    for r in recs:
        n, c = normalize(r)
        out.append(n)
        for f, a, b in c:
            log.append({"id": r["id"], "app": r["app"], "field": f, "from": a, "to": b, "loop": "normalize"})
    json.dump(out, open(sys.argv[2], "w"), indent=1)
    print(f"{len(log)} field changes across {len({x['id'] for x in log})} records")
    if len(sys.argv) > 3:
        json.dump(log, open(sys.argv[3], "w"), indent=1)
