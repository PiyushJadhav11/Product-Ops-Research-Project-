# Fix-loop prompt (verification loop 3: targeted re-research)

Derived from the error patterns found on calibration sample A (20 apps scored against adjudicated truth).
The fix agent does NOT see ground truth. It re-checks every record for exactly these failure modes,
reading vendor primary pages, and emits *patches* (never silent edits).

Error patterns observed on sample A -> check applied to all 100:

| Pattern seen on A | Example | Check |
|---|---|---|
| Announced / waitlisted MCP counted as official | Pinterest | C1: if official_mcp=yes, open the MCP page: is it usable today (GA/beta/preview you can connect to) and vendor-maintained? Docs-search-only MCP = no. |
| "OAuth2" claimed where only client-credentials / service accounts exist | MongoDB Atlas | C2: if toolkit_auth=oauth2, confirm a 3-legged authorization-code flow any developer can register. Else use the per-user key type. |
| Free dev account read as "no gate" though external installs need review | Front | C3: if access is self-serve and toolkit uses OAuth, check whether apps used by other workspaces need listing/review/install caps -> app_review. |
| Partner-only OAuth path labelled as the gate though a per-user key exists | Aircall | C4: if OAuth needs a partner programme but users can paste their own key, toolkit_auth = that key and access follows the key path. |
| Secondary-source gate claims | Otter | C5: replace secondary evidence with a vendor page or downgrade confidence; resolve every `unknown`. |

Rules: WebFetch vendor pages only (search budget exhausted for this run; do not use search engines via
other means). A patch needs `url` + short verbatim `quote`. If you cannot confirm, do not patch; add a note.
Labels follow agent/prompts/rubric.md.
