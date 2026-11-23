# Labeling rubric v2 (added after verification loop 1)

Pass 2 showed that several "errors" were really *definition drift* between workers. This rubric pins
each label down. Ground-truth verifiers and the fix-loop agent both use it.

**toolkit_auth** — the auth a multi-tenant toolkit (many end users connecting their own accounts) would use.
OAuth2 if the vendor offers a third-party OAuth2 flow that any developer can register; otherwise the
per-user credential (api_key / bearer_token / basic). `bearer_token` = a user-generated personal token or
access token pasted by the user; `api_key` = a key from a settings page (sent as header or param).

**access** — what a new developer must clear to get credentials that work against a real account:
- `self_serve_free`: free plan / free dev account / free sandbox gives working creds; no human approval.
- `self_serve_trial`: only via a time-boxed free trial; no human.
- `paid_plan`: API/creds only on a paid tier, after any trial (state tier).
- `app_review`: creds are self-serve for your own account, but letting *arbitrary external users* connect
  requires vendor review / verification / developer-token approval / marketplace listing / install caps.
- `partner_gated`: you must be an existing enterprise customer, a partner, or go through sales to get any creds.
Pick the most restrictive gate that a toolkit serving external users would hit.

**official_mcp** — `yes` only if the vendor itself maintains (vendor domain or vendor GitHub org) an MCP
server that acts on the user's account data or actions. Beta / preview / early-access that a developer can
actually use counts as yes. A docs-search-only MCP, an announced-but-unreleased MCP, or a community server
is `no` (note it in community_mcp / notes).

**verdict**
- `ready`: self_serve_free or self_serve_trial AND documented public API of at least moderate breadth.
- `ready_with_friction`: buildable, but behind app_review, a paid plan, or per-tenant setup (customer must
  provision an instance/site/region, admin-enable API, etc.).
- `blocked`: partner_gated, no public API, or not a SaaS API at all (local CLI/library).

**blocker_type** must be `none` iff verdict is `ready`.
