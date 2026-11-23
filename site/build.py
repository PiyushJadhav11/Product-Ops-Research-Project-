"""Build the case-study page from the data files. Every number on the page is computed here.

    python site/build.py      ->  site/index.html (+ data.json, final.csv)  and the same files in docs/ for GitHub Pages
Run agent/pipeline.py first if you changed any data.
"""
import collections, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
from score import score  # noqa: E402

load = lambda rel: json.load(open(ROOT / rel, encoding="utf-8"))
KEY = ["toolkit_auth", "access", "official_mcp", "verdict"]

# 1. accuracy by stage, against adjudicated truth on the 30-app sample
truth, s = load("data/verify/truth.json"), load("data/verify/sample.json")
ALL = s["calibration_A"] + s["holdout_B"]
files = {"p1": "data/pass1/pass1.json", "p2": "data/pass2/pass2.json", "loops": "data/pass3/patched_norm.json"}
acc, field = {}, {}
for k, f in files.items():
    recs = load(f)
    acc[k] = {}
    for part, ids in [("A", s["calibration_A"]), ("B", s["holdout_B"]), ("all", ALL)]:
        h, n, m = score(recs, truth, ids)
        acc[k][part] = round(100 * h / n, 1)
        if part == "all":
            fc = collections.Counter(x[2] for x in m)
            field[k] = {f_: len(ALL) - fc[f_] for f_ in KEY}

# 2. misses still standing after the loops (explanations written after reading each case)
_, _, misses = score(load(files["loops"]), truth, ALL)
WHY = {
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
M = dict(acc=acc, field=field, n_sample=len(ALL), final_all=acc["loops"]["all"], final_B=acc["loops"]["B"],
         misses=[[a, f, str(x), str(t), WHY.get((i, f), "(not yet explained)"), "A" if i in sa else "B"]
                 for i, a, f, x, t in misses])
log = load("data/verify/changes_all.json")
c = collections.Counter(x["loop"].split("_")[0] for x in log)
M.update(ch_total=len(log), ch_norm=c["normalize"], ch_fix=c["fix"], ch_browser=c["browser"], ch_adj=c["adjudication"])
M["evidence"] = sum(len(r["evidence"]) for r in load("data/pass2/pass2.json"))
M["lint_p2"] = sum(1 for v in load("data/verify/lint_pass2.json").values() if v)

# 3. slim per-app records for the table
ch = collections.defaultdict(list)
for x in log:
    if x["field"] in ("toolkit_auth", "access", "official_mcp", "verdict", "blocker_type", "auth_methods", "mcp_url"):
        ch[x["id"]].append([x["loop"], x["field"], str(x["from"]), str(x["to"])])


def t(v, n):
    v = (v or "").strip()
    return v if len(v) <= n else v[: n - 1] + "…"


final = load("data/final.json")
slim = []
for r in final:
    ev, seen = [], set()
    for e in r["evidence"]:
        u = e.get("url") or ""
        if u in seen or not u.startswith("http"):
            continue
        seen.add(u)
        ev.append([t(e.get("claim"), 140), u])
    slim.append(dict(id=r["id"], app=r["app"], cat=r["category"], what=t(r.get("one_liner"), 120),
                     auth=r.get("auth_methods", []), tk=r["toolkit_auth"], access=r["access"], gate=t(r.get("gate_evidence"), 220),
                     api=r.get("api_type", []), breadth=r.get("api_breadth"), hooks=r.get("webhooks"), mcp=r["official_mcp"],
                     mcp_url=r.get("mcp_url") or "", verdict=r["verdict"], bt=r["blocker_type"], blocker=t(r.get("blocker"), 180),
                     shape=r.get("toolkit_shape"), docs=r.get("docs_url", ""), ev=ev[:5], conf=r.get("confidence"),
                     sample=r.get("verified_sample", ""), changes=ch.get(r["id"], [])))

# 4. render + copy
data = json.dumps(slim, separators=(",", ":"), ensure_ascii=False)
html = (ROOT / "site/template.html").read_text(encoding="utf-8")
html = html.replace("__DATA__", data.replace("</", "<\\/")).replace("__METRICS__", json.dumps(M))
(ROOT / "site/index.html").write_text(html, encoding="utf-8")
shutil.copy(ROOT / "data/final.json", ROOT / "site/data.json")
shutil.copy(ROOT / "data/final.csv", ROOT / "site/final.csv")
(ROOT / "docs").mkdir(exist_ok=True)
for f in ["index.html", "data.json", "final.csv"]:
    shutil.copy(ROOT / "site" / f, ROOT / "docs" / f)
(ROOT / "docs/.nojekyll").touch()
print(f"built site/index.html + docs/  | accuracy p1 {acc['p1']['all']}% -> p2 {acc['p2']['all']}% -> loops "
      f"{acc['loops']['all']}% (holdout {acc['loops']['B']}%) | {len(M['misses'])} misses")
