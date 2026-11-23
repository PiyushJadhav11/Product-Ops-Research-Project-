<<<<<<< HEAD
# Composio app research: 100 apps, agent-researched and verified

Can each of 100 apps become an AI-agent toolkit today? For each app this repo records the auth method,
access gate, API surface, official MCP, verdict and main blocker, with the vendor-doc URL behind each answer.
It also shows how accurate those answers are.

**Case study page:** `site/index.html` (the live link is in the submission). The page has the findings,
the patterns, how the agent works, the verification results and a filterable table of all 100 apps.

## Results

| | |
|---|---|
| Ready today | 41 |
| Ready with friction (app review / paid plan / per-tenant setup) | 49 |
| Blocked (partner or sales gate, no API, or not a SaaS API) | 10 |
| Field accuracy: model memory → web research → after loops | 74.2% → 86.7% → **92.5%** (30-app sample, 120 checks) |
| Accuracy on the holdout sample (never used for tuning) | 72.5% → 85.0% → **90.0%** |

## Pipeline

```
apps.csv ─▶ Pass 1: baseline from model memory (no web)   data/pass1/
        ─▶ Pass 2: 10 parallel research workers, cited    data/pass2/
        ─▶ Loop 1: lint.py        (11 consistency rules)  data/verify/lint_pass2.json
        ─▶ Ground truth: 3 blind verifier agents on a 30-app stratified sample,
                         a reviewer adjudicates each disagreement, rubric.md fixes the definitions
        ─▶ Loop 2: normalize.py   (re-derive verdict from facts per rubric)
        ─▶ Loop 3: fix agents     (patch + URL + quote for 5 error patterns found on sample A)
        ─▶ Loop 4: browser check  (JS-rendered pages)
        ─▶ data/final.json / data/final.csv
```

Every field change is logged in `data/verify/changes_all.json` with the loop that made it, plus a URL and quote where one applies.

## Reproduce the numbers (no keys needed)

```bash
pip install jsonschema           # optional, used for schema validation
python agent/lint.py      data/pass2/pass2.json
python agent/normalize.py data/pass3/patched.json data/pass3/patched_norm.json
python agent/score.py     data/pass1/pass1.json all          # 74.2%
python agent/score.py     data/pass2/pass2.json all          # 86.7%
python agent/score.py     data/pass3/patched_norm.json B     # 90.0% on the holdout
python site/build.py                                         # rebuilds site/index.html from the data
```

## Re-run the research agent

```bash
pip install anthropic             # plus: composio composio-anthropic (optional)
export ANTHROPIC_API_KEY=...
export COMPOSIO_API_KEY=...       # optional: Composio's Firecrawl toolkit does the page fetching
python agent/run.py research --ids 41-50 --out data/run/ecom.json --workers 6
python agent/run.py fix --in data/run/ecom.json --out data/run/ecom.patches.json
python agent/lint.py data/run/ecom.json
python agent/normalize.py data/run/ecom.patched.json data/run/ecom.final.json
```

`RESEARCH_MODEL` sets the model. **Honest note:** the submitted dataset was produced by Claude agents
(in Claude Cowork) running these exact prompts with web search and fetch tools: 10 research workers,
3 blind verifiers, 5 fix-loop workers and a browser check. `run.py` is the same loop as a standalone
script. It is syntax-checked but had not been run end to end with live keys when this was submitted.

## Layout

```
agent/prompts/research.md   worker prompt (method + rules)
agent/prompts/rubric.md     label definitions (pinned after loop 1 found definition drift)
agent/prompts/fix_loop.md   the 5 error patterns from sample A → checks C1-C5
agent/schema.json           record schema
agent/run.py                portable agent (Anthropic API + optional Composio tools)
agent/lint.py normalize.py score.py   deterministic loops + scorer
data/apps.csv               the 100 apps
data/pass1 pass2 pass3      every intermediate pass and the fix-loop patches
data/verify/                sample.json (seed 2026), gt_raw.json (blind verifiers), truth.json (adjudicated),
                            human_review.csv (120-row sign-off sheet with proof links), browser_checks.json
data/final.json final.csv   the deliverable dataset
site/                       case-study page + build script
```

## Known limits

- Access is still `unknown` for 4 long-tail apps (Zoho Cliq, fanbasis, Paygent Connect, iPayX). They need a vendor contact.
- The 70 apps outside the sample are about 90% accurate per field (holdout estimate). Re-check the lowest-confidence rows first (`confidence < 0.7`).
- Gates and MCP availability change monthly. Data as of 23 Nov 2026.
=======
# Product-Ops-Research-Project-
>>>>>>> e8180f47efb516b18082d7ae1ae9cad971daa449
