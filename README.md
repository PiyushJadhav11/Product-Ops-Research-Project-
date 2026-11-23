# Composio app research: 100 apps, agent-researched and verified

*Author: Piyush Jadhav*

Can each of 100 apps become an AI-agent toolkit today? For each app this repo records the auth method,
access gate, API surface, official MCP, verdict and main blocker, with the vendor-doc URL behind each answer.
It also shows how accurate those answers are.

**Live case study:** https://piyushjadhav11.github.io/Product-Ops-Research-Project-/ (GitHub Pages, served from `docs/`; source `site/`)  
**Repo:** https://github.com/PiyushJadhav11/Product-Ops-Research-Project-

The page has the findings, the patterns, how the agent works, the verification results and a filterable
table of all 100 apps. Requires only Python 3.9+ to reproduce; no Claude account needed.

## Results

| | |
|---|---|
| Ready today | 38 |
| Ready with friction (app review / paid plan / per-tenant setup / MCP-only) | 52 |
| Blocked (partner or sales gate, no API, or not a SaaS API) | 10 |
| Field accuracy: model memory → web research → after loops | 75.8% → 87.5% → **91.7%** (30-app sample, 120 checks, truth includes human corrections) |
| Accuracy on the holdout sample (never used for tuning) | 70.0% → 82.5% → **87.5%** |

## Pipeline

```
apps.csv ─▶ Pass 1: baseline from model memory (no web)   data/pass1/
        ─▶ Pass 2: 10 parallel research workers, cited    data/pass2/
        ─▶ Loop 1: lint.py        (11 consistency rules)  data/verify/lint_pass2.json
        ─▶ Ground truth: 3 blind verifier agents on a 30-app stratified sample,
                         the orchestrator agent adjudicates each disagreement, rubric.md fixes the definitions
        ─▶ Loop 2: normalize.py   (re-derive verdict from facts per rubric)
        ─▶ Loop 3: fix agents     (patch + URL + quote for 5 error patterns found on sample A)
        ─▶ Loop 4: browser check  (JS-rendered pages)
        ─▶ adjudicated truth + documented overrides (data/verify/overrides.json)
        ─▶ Human spot-check: 20 answers (all disputed + random controls) checked by hand  data/verify/human_spotcheck.csv
        ─▶ data/final.json / data/final.csv        ← agent/pipeline.py rebuilds this whole chain
```

Every field change is logged in `data/verify/changes_all.json` with the loop that made it, plus a URL and quote where one applies.

## Reproduce the numbers (no keys needed)

```bash
pip install jsonschema           # optional, used for schema validation
python agent/lint.py      data/pass2/pass2.json
python agent/normalize.py data/pass3/patched.json data/pass3/patched_norm.json
python agent/score.py     data/pass1/pass1.json all          # 75.8%
python agent/score.py     data/pass2/pass2.json all          # 87.5%
python agent/score.py     data/pass3/patched_norm.json B     # 87.5% on the holdout
python agent/pipeline.py                                     # rebuilds data/final.json + final.csv from the agent outputs
python site/build.py                                         # rebuilds site/index.html and copies it to docs/ (GitHub Pages)
```

## Re-run the research agent

```bash
pip install anthropic             # plus: composio composio-anthropic (optional)
export ANTHROPIC_API_KEY=...      # Windows: set ANTHROPIC_API_KEY=...
export COMPOSIO_API_KEY=...       # optional: Composio's Firecrawl toolkit does the page fetching
python agent/run.py research --ids 41-50 --out data/run/ecom.json --workers 6
python agent/run.py fix --in data/run/ecom.json --out data/run/ecom.patches.json
python agent/lint.py data/run/ecom.patched.json
python agent/normalize.py data/run/ecom.patched.json data/run/ecom.final.json
```

`RESEARCH_MODEL` sets the model. **Honest note:** the submitted dataset was produced by Claude agents
(in Claude Cowork) running these exact prompts with web search and fetch tools: 10 research workers,
3 blind verifiers, 5 fix-loop workers and a browser check. `run.py` is the same loop as a standalone
script. Its full loop (pause/continue, schema-validation retry, evidence-only patching, lint, normalise)
is tested offline against a mocked API client; it has not yet been run with a live key.

## Layout

```
agent/prompts/research.md   worker prompt (method + rules)
agent/prompts/rubric.md     label definitions (pinned after loop 1 found definition drift)
agent/prompts/fix_loop.md   the 5 error patterns from sample A → checks C1-C5
agent/schema.json           record schema
agent/run.py                portable agent (Anthropic API + optional Composio tools)
agent/lint.py normalize.py score.py   deterministic loops + scorer
agent/pipeline.py           rebuilds data/final.json from pass2 + patches + browser checks + truth + overrides
data/apps.csv               the 100 apps
data/pass1 pass2 pass3      every intermediate pass and the fix-loop patches
data/verify/                sample.json (seed 2026), gt_raw.json (blind verifiers), truth.json (adjudicated),
                            human_review.csv (120 sampled answers with proof links, ready for a human audit), browser_checks.json,
                            overrides.json (2 documented policy calls), changes_all.json (every field change),
                            human_spotcheck.csv (20 rows checked by hand), human_check.json + truth_final.json (its result)
data/final.json final.csv   the deliverable dataset
site/                       page template + build script (build.py writes index.html)
docs/                       built page for GitHub Pages
```

## Known limits

- **Human checks are a spot-check, not a full audit.** Ground truth for the 30-app sample comes from blind verifier agents reading vendor pages, with disagreements adjudicated by the orchestrator agent. A human (Piyush Jadhav) then checked 20 of those answers by hand (15 confirmed, 5 corrected) in `data/verify/human_spotcheck.csv`; corrections override the agents and the page reports the result. `human_review.csv` has all 120 sampled answers for a fuller audit.
- Access is still `unknown` for 4 long-tail apps (Zoho Cliq, fanbasis, Paygent Connect, iPayX). They need a vendor contact.
- The 70 apps outside the sample are about 87.5% accurate per field (holdout estimate). Re-check the lowest-confidence rows first (`confidence < 0.7`).
- Gates and MCP availability change monthly. Data as of 23 Nov 2026.

## Human spot-check (how to do it, ~20 minutes)

1. Open `data/verify/human_spotcheck.csv` in Excel or Google Sheets.
2. For each row, open `proof_url`, read `how_to_check`, and type `y` (our answer is right) or `n` in `your_verdict (y/n)`.
   If `n`, put the right value in `correct_value_if_n` (same words as `our_answer` uses) and a short `note`.
3. Save as CSV (same name), then run:
   ```
   python agent/pipeline.py
   python site/build.py
   ```
   The page, the accuracy numbers and the "where a human was needed" text update automatically.
