"""Score a research file against adjudicated ground truth on a sample.
Usage: python agent/score.py data/pass2/pass2.json [A|B|all]"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["toolkit_auth", "access", "official_mcp", "verdict"]
KEYLIKE = {"api_key", "bearer_token"}  # a toolkit handles these identically (static secret in a header)

def norm(f, v):
    if f == "toolkit_auth" and v in KEYLIKE:
        return "api_key|bearer_token"
    return v

def score(recs, truth, ids):
    recs = {r["id"]: r for r in recs}
    hits, misses = 0, []
    for i in ids:
        t = truth[str(i)]["labels"]
        for f in FIELDS:
            if norm(f, recs[i].get(f)) == norm(f, t[f]):
                hits += 1
            else:
                misses.append((i, recs[i]["app"], f, recs[i].get(f), t[f]))
    return hits, len(ids) * len(FIELDS), misses

if __name__ == "__main__":
    recs = json.load(open(sys.argv[1]))
    tf = ROOT / "data/verify/truth_final.json"  # truth + human corrections, if any
    truth = json.load(open(tf if tf.exists() else ROOT / "data/verify/truth.json"))
    s = json.load(open(ROOT / "data/verify/sample.json"))
    which = sys.argv[2] if len(sys.argv) > 2 else "all"
    ids = {"A": s["calibration_A"], "B": s["holdout_B"], "all": s["calibration_A"] + s["holdout_B"]}[which]
    h, n, m = score(recs, truth, ids)
    print(f"{which}: {h}/{n} = {h/n:.1%}")
    for x in m:
        print("  MISS", x)
