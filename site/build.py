"""Build site/index.html from data files (all numbers on the page come from here)."""
import json, collections, subprocess, sys
from pathlib import Path
sys.path.insert(0, "agent")
from score import score
root = Path(".")
truth = json.load(open("data/verify/truth.json")); s = json.load(open("data/verify/sample.json"))
files = {"p1": "data/pass1/pass1.json", "p2": "data/pass2/pass2.json", "loops": "data/pass3/patched_norm.json"}
acc, field = {}, {}
for k, f in files.items():
    recs = json.load(open(f))
    acc[k] = {}
    for part, ids in [("A", s["calibration_A"]), ("B", s["holdout_B"]), ("all", s["calibration_A"] + s["holdout_B"])]:
        h, n, m = score(recs, truth, ids); acc[k][part] = round(100 * h / n, 1)
        if part == "all":
            fc = collections.Counter(x[2] for x in m)
            field[k] = {f_: 30 - fc[f_] for f_ in ["toolkit_auth", "access", "official_mcp", "verdict"]}
h, n, misses = score(json.load(open(files["loops"])), truth, s["calibration_A"] + s["holdout_B"])
why = {
 (29, "access"): "Read 'free access to test' as paid; browser check confirmed a self-serve trial",
 (29, "verdict"): "Follows from the access miss",
 (30, "toolkit_auth"): "Chose the Voice-API JWT over key/secret; both valid, definitional",
 (68, "verdict"): "Counted per-project API key setup as per-tenant setup",
 (92, "access"): "REST API is Enterprise-only but the MCP is free; rubric gates on the MCP path",
 (28, "toolkit_auth"): "Used the system-user token; multi-tenant Tech Providers use Embedded Signup (OAuth)",
 (34, "access"): "Fix agent couldn't load marketplace docs; public apps need review",
 (34, "verdict"): "Follows from the access miss",
 (96, "access"): "Pricing table is JS icons that WebFetch can't see; browser check fixed it",
}
sa = set(s["calibration_A"])
M = dict(acc=acc, field=field, final_all=acc["loops"]["all"], final_B=acc["loops"]["B"],
         misses=[[a, f, str(x), str(t), why.get((i, f), ""), "A" if i in sa else "B"] for i, a, f, x, t in misses])
log = json.load(open("data/verify/changes_all.json"))
c = collections.Counter(x["loop"].split("_")[0] for x in log)
M.update(ch_total=len(log), ch_norm=c["normalize"], ch_fix=c["fix"], ch_browser=c["browser"], ch_adj=c["adjudication"])
M["evidence"] = sum(len(r["evidence"]) for r in json.load(open("data/pass2/pass2.json")))
lint = json.load(open("data/verify/lint_pass2.json")); M["lint_p2"] = sum(1 for v in lint.values() if v)
data = open("site/data.slim.json").read()
html = open("site/template.html").read().replace("__DATA__", data.replace("</", "<\\/")).replace("__METRICS__", json.dumps(M))
open("site/index.html", "w").write(html)
print(json.dumps({k: v for k, v in M.items() if k != "misses"}, indent=0)); print(len(M["misses"]), "misses")
