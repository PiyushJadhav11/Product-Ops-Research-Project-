"""Verification loop 1: deterministic consistency rules over research records.

Catches internally-contradictory records before any human looks at them.
Usage: python agent/lint.py data/pass2/pass2.json
"""
import json, sys
from urllib.parse import urlparse

PRIMARY_HINTS = ("docs", "developer", "api", "help", "support", "github.com", "pricing", "learn.microsoft", "dev")


def rules(r):
    for k in ("verdict", "access", "toolkit_auth", "official_mcp"):
        if k not in r:  # e.g. a failed agent run returned {"error": ...}
            return [f"R0 missing required field {k}"]
    f = []
    ev = r.get("evidence", [])
    if len(ev) < 2:
        f.append("R1 <2 evidence urls")
    if r["verdict"] == "ready" and r["access"] in ("paid_plan", "partner_gated", "app_review"):
        f.append("R2 verdict=ready but access is gated")
    if r["verdict"] == "blocked" and r["access"] in ("self_serve_free", "self_serve_trial") and r.get("blocker_type") not in ("not_a_saas_api", "no_public_api"):
        f.append("R3 blocked but self-serve")
    if r["official_mcp"] == "yes" and not r.get("mcp_url"):
        f.append("R4 official MCP without URL")
    if r["toolkit_auth"] not in r.get("auth_methods", []):
        f.append("R5 toolkit_auth not in auth_methods")
    if r["verdict"] != "ready" and r.get("blocker_type") in (None, "none"):
        f.append("R6 non-ready verdict but no blocker")
    if r["verdict"] == "ready" and r.get("blocker_type") not in (None, "none"):
        f.append("R7 ready verdict but blocker set")
    if "unknown" in (r["access"], r["toolkit_auth"], r["official_mcp"]):
        f.append("R8 key field unknown")
    if r.get("evidence_quality") == "secondary":
        f.append("R9 secondary-only evidence")
    if r.get("confidence", 1) < 0.7:
        f.append("R10 confidence<0.7")
    mcp = r.get("mcp_url") or ""
    if r["official_mcp"] == "yes" and mcp.startswith("http"):
        host = urlparse(mcp).netloc
        if any(x in host for x in ("smithery", "glama", "mcp.so", "pulsemcp", "composio", "zapier", "pipedream")):
            f.append("R11 'official' MCP hosted on an aggregator domain")
    return f


if __name__ == "__main__":
    recs = json.load(open(sys.argv[1]))
    out = {r["id"]: rules(r) for r in recs}
    flagged = {k: v for k, v in out.items() if v}
    for r in recs:
        if out[r["id"]]:
            print(f'{r["id"]:>3} {r["app"]:<28} ' + "; ".join(out[r["id"]]))
    print(f"\n{len(flagged)}/{len(recs)} records flagged")
    if len(sys.argv) > 2:
        json.dump(out, open(sys.argv[2], "w"), indent=1)
