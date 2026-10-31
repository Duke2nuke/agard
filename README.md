# Agard — the agent that guards every buy

Full idea, workflow, judging map and guidelines checklist:
[PROJECT_BLUEPRINT.md](PROJECT_BLUEPRINT.md)

PayPal AI Hackathon 2026 submission scaffold (not yet submitted).
Guarded agentic checkout: an AI agent finds a product, checks merchant/price risk,
blocks risky purchases with a plain-English explanation, and only then completes
a real PayPal **sandbox** checkout on user approval.

## Status (updated 31 Oct 2026)
- Judge-ready demo UI at `/`: search + budget, ranked results with risk badge,
  plain-English verdict, and a two-step flow — guard check first, checkout
  only after explicit approval. Blocked items cannot be approved.
- Guard fixed 31 Oct: cheap safe products no longer score risk for being
  below usual spend; only upward spikes count. Verified: $49.99 safe = 0,
  $29.99 safe = 0, $299 new-merchant + over budget = 100 BLOCKED.
- Mock mode by default (no credentials = labelled MOCK, not a real order).
  No real money, no production PayPal data.
- Registered on Devpost (PayPal AI Hackathon, 30 Oct 2026, join only).
- Sandbox proof so far (31 Oct): OAuth ok, $49.99 test order CREATED; buyer approval/capture parked after the approve link crashed — do not retry that link.
- Still needed: hosted demo, video.

## Quick start — clean clone (mock mode, no credentials needed)
```bash
git clone https://github.com/Duke2nuke/agard.git
cd agard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
# open http://127.0.0.1:5000
```
Repo is live at https://github.com/Duke2nuke/agard — clone from there.

## 30-second demo script (for judges / video)
1. Open the home page, search `earbuds`, budget `$100`.
2. Show the $299 Wireless Earbuds Ultra from a new merchant: risk 100,
   BLOCKED, with reasons (price spike vs $50 usual median, new merchant,
   over budget). No approve button — money cannot move.
3. Show the $49.99 Wireless Earbuds Pro from an established merchant:
   risk 0, "Looks safe". Click Approve checkout.
4. In mock mode this records a MOCK_APPROVED transaction and says so
   clearly. In sandbox mode it creates a real PayPal sandbox order and
   shows the PayPal approve link instead.
5. Open Transactions: the safe purchase is listed, the blocked one is not.

Try: search "earbuds", see a risky product blocked, approve the safe product,
watch the (mock) checkout and the guard dashboard.

## Sandbox mode (real PayPal sandbox API)
1. Create a PayPal Developer account at developer.paypal.com
2. Create a sandbox app, copy Client ID + Secret
3. Create sandbox business (seller) + personal (buyer) test accounts
4. Copy `.env.example` to `.env` and fill in the values. Never commit `.env`.
5. Run `python3 app.py` — if credentials are present it uses
   https://api-m.sandbox.paypal.com, otherwise it stays in mock mode and says so.

## Architecture
- `app.py` — Flask demo app: search, guard check, checkout, transactions dashboard
- `guard.py` — anomaly guard, ported from the Day 2 detector:
  same-hour/seasonal baseline idea + median/MAD modified z-score, pure Python
- `paypal_client.py` — PayPal Orders API client (OAuth, create order, capture,
  list transactions via reporting API). Least-privilege agent tools only:
  orders create/get/capture, transactions list, disputes list/get.
  Dispute acceptance is manual only — never auto-accepted by the agent.
- `products.py` — mock product catalogue, standing in for Channel3 product data
  until a Channel3 key is added. Clearly labelled MOCK in the UI and README.
- `templates/` — not used yet; the demo page is rendered inline in app.py
  for scaffold simplicity. The submission build should move the dashboard
  table to AG Grid (sponsor tool) and deploy on Render (sponsor tool).

## Sponsor tools actually used (at submission, not just listed)
- PayPal Developer Platform + sandbox (core, required)
- AG Grid — dashboard table, filtering, charts (to be wired in the 3–5 Nov build)
- Channel3 — clean product data (mock catalogue until key added; do not claim
  Channel3 integration until it is actually wired)
- Render — hosted demo deployment
- APIMatic Context Plugin — agent PayPal context (only if actually integrated)

Do NOT claim Elastic, Bryntum, Zapier, or any other sponsor tool unless it is
actually integrated and demonstrated.

## Honest limits (keep these in the submission README too)
- Sandbox/synthetic data only. No real-world fraud accuracy is claimed.
- The guard is a statistical anomaly flag + rules, not a production fraud system.
- Prices in the demo checkout must match the sandbox currency used in the
  PayPal order call (USD in sandbox by default) — do not mix INR demo text
  with a USD checkout call without converting/labelling it clearly.
