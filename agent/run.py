"""Portable research agent: same prompts + schema as the submitted run.

Stages
  research : one worker per app, web search + fetch, returns a schema-valid JSON record
  fix      : re-checks each record for the error patterns in prompts/fix_loop.md, emits patches
Then run the deterministic loops:  lint.py -> normalize.py -> score.py

Usage
  export ANTHROPIC_API_KEY=...            # required
  export COMPOSIO_API_KEY=...             # optional: adds Composio's Firecrawl toolkit as the fetcher
  python agent/run.py research --ids 1-100 --out data/run/research.json --workers 8
  python agent/run.py fix --in data/run/research.json --out data/run/patches.json
  python agent/lint.py data/run/research.json
  python agent/normalize.py data/run/research.patched.json data/run/final.json
  python agent/score.py data/run/final.json all      # only meaningful if --ids covers the sampled apps

Note: the submitted dataset was produced by Claude agents executing these exact prompts with
WebSearch/WebFetch tools (see README). This file reproduces that loop against the Anthropic API.
"""
import argparse, csv, json, os, re, sys, concurrent.futures as cf
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = os.getenv("RESEARCH_MODEL", "claude-sonnet-4-5")
SCHEMA = json.loads((ROOT / "agent/schema.json").read_text())
PROMPT = (ROOT / "agent/prompts/research.md").read_text()
RUBRIC = (ROOT / "agent/prompts/rubric.md").read_text()
FIXLOOP = (ROOT / "agent/prompts/fix_loop.md").read_text()

SERVER_TOOLS = [
    {"type": "web_search_20250305", "name": "web_search", "max_uses": 8},
    {"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 8},
]


def composio_tools(user_id="research-agent"):
    """Optional: pull Composio-hosted tools (e.g. Firecrawl scrape) for page fetching."""
    if not os.getenv("COMPOSIO_API_KEY"):
        return None, []
    try:
        from composio import Composio
        from composio_anthropic import AnthropicProvider
        c = Composio(provider=AnthropicProvider())
        return c, c.tools.get(user_id=user_id, toolkits=["FIRECRAWL"])
    except Exception as e:  # SDK missing / not connected: fall back to server tools only
        print(f"[composio] disabled: {e}", file=sys.stderr)
        return None, []


def ask(client, system, user, composio=None, ctools=()):
    msgs = [{"role": "user", "content": user}]
    resp = None
    for _ in range(15):  # agent loop: server tools run inside the API; Composio tools run here
        resp = client.messages.create(
            model=MODEL, max_tokens=8000, system=system, messages=msgs,
            tools=SERVER_TOOLS + list(ctools),
            extra_headers={"anthropic-beta": "web-fetch-2025-09-10"},
        )
        if resp.stop_reason == "pause_turn":  # long server-tool turn: hand it back to continue
            msgs += [{"role": "assistant", "content": resp.content}]
            continue
        if resp.stop_reason == "tool_use" and composio is not None:
            calls = [b for b in resp.content if b.type == "tool_use"]
            results = composio.provider.handle_tool_calls(user_id="research-agent", response=resp)
            msgs += [{"role": "assistant", "content": resp.content},
                     {"role": "user", "content": [{"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(r, default=str)}
                                                  for b, r in zip(calls, results)]}]
            continue
        break
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else {"error": "no json", "raw": text[:500]}
    except json.JSONDecodeError as e:
        return {"error": f"bad json: {e}", "raw": text[:500]}


def schema_errors(rec):
    try:
        import jsonschema
    except ImportError:  # validation is optional
        return [] if "verdict" in rec else ["missing fields"]
    return [e.message for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(rec)][:5]


def research_one(client, app, composio, ctools):
    system = "You research SaaS APIs for an integrations team. Output only JSON.\n\n" + RUBRIC
    user = PROMPT.format(**app) + "\n\nJSON schema:\n" + json.dumps(SCHEMA)
    rec = {}
    for attempt in range(2):  # one retry with the validation errors fed back
        rec = ask(client, system, user, composio, ctools)
        rec.update(id=int(app["id"]), app=app["app"], category=app["category"])
        errs = schema_errors(rec)
        if not errs:
            break
        user += "\n\nYour previous answer failed schema validation: " + "; ".join(errs) + ". Return corrected JSON."
    if schema_errors(rec):
        rec["needs_human"] = True
        print(f"[{app['app']}] still invalid after retry", file=sys.stderr)
    return rec


def fix_one(client, rec):
    system = "You verify API research records against vendor pages. Output only JSON.\n\n" + RUBRIC
    user = FIXLOOP + "\n\nRecord:\n" + json.dumps(rec) + \
        '\n\nReturn {"patches":[{"id","field","from","to","check","url","quote"}],"note":""}'
    return ask(client, system, user)


def parse_ids(s):
    out = set()
    for part in s.split(","):
        a, _, b = part.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["research", "fix"])
    ap.add_argument("--ids", default="1-100")
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    import anthropic
    client = anthropic.Anthropic()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)

    if a.stage == "research":
        ids = parse_ids(a.ids)
        apps = [r for r in csv.DictReader(open(ROOT / "data/apps.csv")) if int(r["id"]) in ids]
        composio, ctools = composio_tools()
        with cf.ThreadPoolExecutor(a.workers) as ex:
            recs = list(ex.map(lambda x: research_one(client, x, composio, ctools), apps))
        json.dump(sorted(recs, key=lambda r: r["id"]), open(a.out, "w"), indent=1)
    else:
        if not a.inp:
            ap.error("fix needs --in <research.json>")
        recs = json.load(open(a.inp))
        with cf.ThreadPoolExecutor(a.workers) as ex:
            res = list(ex.map(lambda r: fix_one(client, r), recs))
        patches = [p for r in res for p in r.get("patches", [])]
        json.dump({"patches": patches}, open(a.out, "w"), indent=1)
        # apply
        by = {r["id"]: r for r in recs}
        for p in patches:
            pid = int(p.get("id", -1))
            if p.get("url") and p.get("quote") and pid in by:  # no evidence, no patch
                by[pid][p["field"]] = p["to"]
        json.dump(list(by.values()), open(a.inp.replace(".json", ".patched.json"), "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
