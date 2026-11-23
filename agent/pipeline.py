"""Rebuild data/final.json from the committed agent outputs, deterministically.

    pass2.json
      -> normalize (loop 2)                         data/pass3/normalized.json
      -> apply fix-loop patches (loop 3)            data/pass3/patched.json
      -> normalize                                  data/pass3/patched_norm.json   (scored as "after loops")
      -> apply browser checks (loop 4)              data/verify/browser_checks.json
      -> apply adjudicated truth on the 30 sampled apps   data/verify/truth.json
      -> apply documented overrides                 data/verify/overrides.json
      -> normalize (locked verdicts kept)           data/final.json + data/final.csv
Every field change goes to data/verify/changes_all.json with the loop that made it.

Usage (from anywhere):  python agent/pipeline.py
"""
import csv, glob, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
from normalize import normalize  # noqa: E402

KEY_FIELDS = ["toolkit_auth", "access", "official_mcp", "verdict", "blocker_type"]
CSV_COLS = ["id", "app", "category", "one_liner", "toolkit_auth", "auth_methods", "access", "gate_evidence",
            "api_type", "api_breadth", "webhooks", "official_mcp", "mcp_url", "verdict", "blocker_type", "blocker",
            "toolkit_shape", "docs_url", "confidence", "verified_sample", "evidence_urls"]


def P(rel):
    return ROOT / rel


def load(rel):
    return json.load(open(P(rel), encoding="utf-8"))


def dump(obj, rel):
    json.dump(obj, open(P(rel), "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def norm_all(recs, log, tag):
    out = []
    for r in recs:
        n, ch = normalize(r)
        out.append(n)
        log += [{"id": r["id"], "app": r["app"], "field": f, "from": a, "to": b, "loop": tag} for f, a, b in ch]
    return out


def main():
    log = []
    recs = norm_all(load("data/pass2/pass2.json"), log, "normalize")
    dump(recs, "data/pass3/normalized.json")

    # loop 3: fix-loop patches (each has a vendor URL + quote)
    by = {r["id"]: r for r in recs}
    for f in sorted(glob.glob(str(P("data/pass3/patches_*.json")))):
        for p in json.load(open(f, encoding="utf-8"))["patches"]:
            r = by[int(p["id"])]
            r[p["field"]] = p["to"]
            r.setdefault("evidence", []).append(
                {"claim": f"[fix-loop {p['check']}] {p['field']}: {(p.get('quote') or '')[:160]}", "url": p.get("url", "")})
            log.append({"id": r["id"], "app": r["app"], "field": p["field"], "from": p["from"], "to": p["to"],
                        "loop": "fix_" + p["check"], "url": p.get("url"), "quote": p.get("quote")})
    recs = sorted(by.values(), key=lambda r: r["id"])
    dump(recs, "data/pass3/patched.json")
    recs = norm_all(recs, log, "normalize")
    dump(recs, "data/pass3/patched_norm.json")

    # loop 4: browser checks
    by = {r["id"]: r for r in recs}
    for b in load("data/verify/browser_checks.json"):
        r = by[b["id"]]
        log.append({"id": b["id"], "app": r["app"], "field": b["field"], "from": r[b["field"]], "to": b["to"],
                    "loop": "browser", "url": b["url"], "quote": b["quote"]})
        r[b["field"]] = b["to"]
        r["evidence"].append({"claim": "[browser check] " + b["quote"], "url": b["url"]})

    # adjudicated ground truth for the 30 sampled apps
    truth, sample = load("data/verify/truth.json"), load("data/verify/sample.json")
    for k, t in truth.items():
        r = by[int(k)]
        for f in KEY_FIELDS:
            tv = t["labels"][f]
            if r.get(f) != tv and not ({r.get(f), tv} <= {"api_key", "bearer_token"}):
                p = t["proof"].get(f, {})
                log.append({"id": r["id"], "app": r["app"], "field": f, "from": r.get(f), "to": tv,
                            "loop": "adjudication", "url": p.get("url"), "quote": p.get("quote")})
                r[f] = tv
        if t["labels"].get("mcp_url") and r["official_mcp"] == "yes" and not r.get("mcp_url"):
            r["mcp_url"] = t["labels"]["mcp_url"]
        r["verified_sample"] = "A" if int(k) in sample["calibration_A"] else "B"

    # documented overrides (policy calls by the orchestrator agent; each has a reason)
    for o in load("data/verify/overrides.json"):
        r = by[o["id"]]
        for f, v in o["set"].items():
            if f in KEY_FIELDS and r.get(f) != v:
                log.append({"id": r["id"], "app": r["app"], "field": f, "from": r.get(f), "to": v,
                            "loop": "override", "quote": o["reason"]})
            r[f] = v

    final = sorted(by.values(), key=lambda r: r["id"])
    final = [normalize(r)[0] for r in final]          # locked records are left alone
    dump(final, "data/final.json")
    dump(log, "data/verify/changes_all.json")

    with open(P("data/final.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLS)
        for r in final:
            row = []
            for c in CSV_COLS:
                v = r.get(c, "")
                if c == "evidence_urls":
                    v = " | ".join(dict.fromkeys(e["url"] for e in r["evidence"] if e.get("url")))
                if isinstance(v, list):
                    v = ";".join(v)
                row.append(v)
            w.writerow(row)

    with open(P("data/verify/human_review.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "app", "sample", "field", "final_value", "proof_url", "proof_quote", "adjudication_note",
                    "human_ok (y/n)", "human_note"])
        for k, t in sorted(truth.items(), key=lambda x: int(x[0])):
            for f in ["toolkit_auth", "access", "official_mcp", "verdict"]:
                p = t["proof"].get(f, {})
                w.writerow([k, t["app"], by[int(k)]["verified_sample"], f, t["labels"][f], p.get("url", ""),
                            p.get("quote", ""), " ".join(n for n in t.get("adjudication", []) if n.startswith(f)), "", ""])
    print(f"final.json: {len(final)} apps; {len(log)} logged field changes")


if __name__ == "__main__":
    main()
