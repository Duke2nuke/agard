# Agard — Project Blueprint (polished, guideline-checked)

## One line
Agard is an AI shopping agent with guardrails: it finds what you asked
for, checks merchant and price risk, blocks the risky purchase with a
plain-English explanation, and only completes a PayPal sandbox checkout
after a human approves it.

## The problem, in one paragraph
Agentic commerce is stuck on trust, not on shopping. A buyer will not hand
an agent their wallet if the agent can buy the wrong item, from a seller
with no history, for six times the budget — and a merchant will not expose
inventory to agents they cannot audit. PayPal's own framing is "know your
agent". Agard is that missing layer, on the buyer's side, before money
moves. It does not claim to detect real-world fraud. It claims something
smaller and provable: this agent cannot spend outside your rules, and
every decision it makes can be read back in plain English.

## Who it is for
- Everyday online buyers who want an agent to shop, but not to surprise them.
- Judges can test it in 30 seconds with no account, no card, no install:
  search "earbuds", budget $100, see a block and an approval.

## Why this is not a generic "AI + PayPal" demo
1. **Proposer vs executor separation.** The agent proposes. The guard
   scores. The checkout service — a separate step — is the only code that
   can call PayPal, and only after human approval. The agent can never
   approve its own proposal, raise its own budget, or call capture.
2. **Policy as data, not vibes.** The user's rules live in `policy.py`:
   budget, a first-time-merchant cap ($75), always-require-approval.
   Change the policy, the agent's behaviour changes — visibly.
3. **Explainable numbers, not LLM excuses.** Risk comes from a median/MAD
   modified z-score against the user's own past spend, plus three rules
   (new merchant, over budget, price spike). Every reason shows its number.
   An LLM, if used, may only rewrite those verified facts into plainer
   words — it may never invent a number, a merchant history, or a reason.
4. **Human override with an audit trail, not a bypass.** A BLOCKED item
   has no approve button. A human may override only by acknowledging
   every reason, and that transaction is logged as USER_OVERRIDDEN, never
   as agent-approved. Autonomy is preserved, and the log tells the truth.
5. **A trust ledger, not a one-off score.** Merchants carry prior-order
   counts (AudioHub: 12, BrandNewStore99: 0). Safe purchases build history;
   a first-time seller starts under a cap. Post-purchase, transactions sit
   in a review list — flagged vs normal, mark-as-reviewed — instead of
   disappearing after checkout.

## Workflow — the full journey, step by step

```
USER  ──► 1. INTENT + POLICY        "earbuds, budget $100"
            Policy: budget, new-merchant cap, always-approve
  │
AGENT ──► 2. SEARCH + RANK          TF-IDF / relevance + price fit
            Output: ranked candidates, never a purchase
  │
GUARD ──► 3. SCORE EACH CANDIDATE   median/MAD z + 3 rules
            Output: risk 0-100, reasons with numbers, verdict,
                    decision tier: SAFE / CAUTION / BLOCKED
  │
HUMAN ──► 4. DECIDE
            SAFE (<40):      one-click approve
            CAUTION (40-69): approve + acknowledge every reason
            BLOCKED (70+):   agent stopped; human override only,
                             acknowledged + logged as USER_OVERRIDDEN
  │
CHECKOUT► 5. PAYPAL SANDBOX         Orders API: create order
SERVICE      (executor only)        → buyer approves on PayPal sandbox
                                     → capture → receipt
  │
LEDGER ─► 6. RECEIPT + REVIEW       Transaction recorded with decision
            + risk + reasons; blocked items never appear as purchases;
            overrides are flagged for review
  │
LEARN ──► 7. TRUST UPDATE (manual, honest)
            Prior-order counts update after a completed purchase.
            The guard's thresholds do NOT silently loosen themselves.
```

### Stage table

| Stage | Actor | Input | Output | If it fails |
|---|---|---|---|---|
| 1 Intent + policy | User | Prompt + budget | Policy object | Empty prompt → show example prompts, no guess purchase |
| 2 Search + rank | Agent | Prompt, catalogue | Ranked products | No match → "try earbuds/headphones", no fake product |
| 3 Guard | Guard | Price, usual spend, merchant, budget | Risk, reasons, tier | Bad data → CAUTION, not silent approval |
| 4 Decide | Human | Risk + reasons | Approve / acknowledge / override / walk away | No approval → no checkout, ever |
| 5 Checkout | Checkout service | Approved product | Sandbox order → approve → capture | Sandbox error → show the error, fall back to labelled MOCK only if no credentials; never claim a failed order succeeded |
| 6 Ledger | App | Completed / blocked / overridden | Transaction list | Blocked items are not recorded as purchases |
| 7 Review | Human | Transaction list | Mark-as-reviewed | — |

### The two demo paths judges will see
- **Risky path (the headline):** "earbuds", $100 → $299 Ultra, new
  merchant, 0 prior orders → risk 100, BLOCKED, reasons listed, no
  approve button. Override is possible only as a logged human decision.
- **Safe path (the proof it still shops):** $49.99 Pro, established
  merchant, 12 prior orders → risk 0, SAFE → human approves → sandbox
  order (or clearly labelled MOCK if no credentials) → transaction listed.

## AI, honestly stated
- **Used, in the build:** TF-IDF-style relevance ranking for search;
  median/MAD statistical anomaly scoring for the guard (ported from the
  Day 2 detector); agent orchestration (propose → guard → approve →
  execute) as the agentic pattern.
- **Planned, not yet claimed:** an LLM explanation layer that rewrites
  only verified guard facts. Until it is wired and tested, the submission
  will not claim it.
- **Never claimed:** real-world fraud accuracy, PyTorch/OpenCV, production
  PayPal data, Channel3/AG Grid/Elastic/Bryntum/Zapier until actually wired.

## PayPal, honestly stated
- **Used:** PayPal Orders API in the free sandbox — create order, buyer
  approve link, capture (capture wiring is the sandbox step still blocked
  on credentials). Currency is USD in sandbox throughout; demo text will
  not mix INR amounts into a USD checkout call.
- **Least-privilege agent tools:** orders create/get/capture, transactions
  list, disputes list/get. Dispute acceptance stays manual, never
  auto-accepted by the agent.
- **Never claimed:** real money, production data, PayPal affiliation.
  The name Agard deliberately avoids PayPal's trademark.

## Architecture
```
Browser UI (search, budget, risk cards, transactions)
  │  /search, /checkout, /transactions, /health, /mode
  ▼
Flask app.py — proposer/executor boundary, policy enforcement
  ├── guard.py — median/MAD + rules, plain-English verdict
  ├── policy.py — budget, new-merchant cap, decision tiers
  ├── products.py — mock catalogue (labelled MOCK until Channel3 is wired)
  └── paypal_client.py — Orders API, sandbox only, env credentials only
Hosted on Render (render.yaml, gunicorn) once the repo is pushed.
```

## How this maps to judging (official Devpost criteria)
- **Technological Implementation:** real sandbox Orders API + a guard with
  a real formula and testable numbers, not a screenshot flow.
- **Design:** a complete product in 30 seconds — intent, ranking, risk
  cards, approval, receipt, review list — with empty states and error
  states, not just a happy path.
- **Potential Impact:** a specific, credible audience (buyers afraid to
  delegate spending) and a specific mechanism (policy + guard + human
  gate) that addresses exactly that fear.
- **Innovation/Idea:** proposer/executor separation + policy-as-data +
  audited human override. Most agent demos let the agent check itself out.
  This one structurally cannot.
- **Presentation:** video script (DEMO_VIDEO_SCRIPT.md, 2:30 target)
  shows blocked → approved → receipt end-to-end, with the honest
  sandbox/synthetic footer on screen.

## Prize targeting (one build, several honest shots)
Overall, Best Use of PayPal + AI, Best Use of Agentic Commerce,
Most Impactful, Best Demo Delivery. Sponsor shots only for tools actually
used: Render (hosted demo) and AG Grid (transactions dashboard, to be
wired 3–5 Nov) — never name-dropped.

## Guidelines compliance checklist
- [x] Meaningful PayPal sandbox use (Orders API, not a logo)
- [x] Meaningful AI use (ranking + guard + agent orchestration)
- [ ] Working prototype end-to-end in sandbox — blocked on credentials
- [ ] Public repo with visible licence + clean-clone run instructions —
      prepared, push awaiting go-ahead
- [ ] Functional demo (hosted URL or buildable repo) — Render blocked on repo push
- [ ] Demo video under 3 minutes, public on YouTube — script ready, final
      take waits for sandbox build
- [x] AI tools/models stated honestly in README + submission
- [ ] Eligibility checked on official rules page before submit
- [x] No unverified claims, no planned certs/skills as earned, no
      trademark in the project name, no real-money claims

## Polish standard — what "perfect" means here
- **UI:** every state has a screen — safe, caution, blocked, override,
  empty search, sandbox error, mock mode. No dead buttons, no silent fails.
- **Code:** guard has unit-style checks (safe 0, cheap-safe 0, spike 50,
  spike+new 80, spike+new+over-budget 100, caution needs acknowledgement,
  blocked needs override). Every number shown has a source.
- **README:** clean-clone run in under 2 minutes, demo script, honest
  limits, sponsor tools only if wired.
- **Submission copy:** elevator pitch in one sentence, problem → who →
  PayPal parts → AI parts → what judges can click in 30 seconds. No
  superlatives without evidence ("first", "best", "revolutionary" are out).
- **Video:** problem in 20s, blocked in 40s, approved in 40s, receipt +
  repo in 20s, honest footer throughout. No copyrighted music.

## Deliberately NOT in scope (scope freeze 5 Nov)
No real-money flow, no production fraud claims, no auto-learning guard
that loosens itself, no dispute auto-acceptance, no multi-currency
checkout, no Channel3/AG Grid claims before they are wired, no new
features after 5 Nov — only bug fixes, polish, and the video.

## Risks and mitigations
- Sandbox credentials late → demo stays honestly in MOCK mode, labelled
  everywhere; submission does not claim sandbox until it is live.
- Render cold start (free tier, ~50s, as seen on PromptShield) → video
  and README warn judges; /health endpoint proves the service is up.
- Guard false positives → caution tier + human acknowledgement, not
  silent blocks for everything; cheap-safe fix already shipped.
- Judge scepticism about "AI" → show the formula, the baseline, and the
  test numbers in the README; the guard is inspectable, not a black box.

## Alternatives audit (31 Oct 2026) — why Agard, and what could beat it
CORRECTED 31 Oct ~02:10 IST by Aarambh: the old filter below is removed.
Do NOT use it anymore. New constraints: time is parallelised across
multiple AIs, laptops and people; skills are not limited to the scaffold
stack — Aarambh is mastering PyTorch, OpenCV and other skills, with a
mentor helping while applying them (PromptShield already had a PyTorch
MLP classifier and an OpenCV preprocessing module, so the earlier
"no PyTorch/OpenCV" note was about what was claimed in one job
application, not what he can build); open-source data may be used if
the contest allows it and its licence is respected; Muse is his team
and a second system can be built in parallel. Calendar deadline is still
13 Nov 01:30 IST — parallel work raises throughput, it does not move
the deadline.
Old filter (superseded): 13 days solo, Mozark until 6 Nov, working
sandbox prototype required, no real PayPal production data, no paid
tools, only verified skills (Python/Flask, statistics, TF-IDF).
Not filtered by GPU or by difficulty alone.
- PayGuard alone (anomaly dashboard only): weaker — no shopping, no
  Agentic Commerce prize, judges see a dashboard, not a product.
- Invoice explainer for freelancers: strong PayPal Invoicing use, clear
  audience, weaker on agentic commerce and innovation.
- Subscription Guardian (closest challenger): potentially better on
  Impact and PayPal depth (Subscriptions API), but subscription lifecycle
  + webhooks + consequential cancels are harder to demo safely in 3 min
  in 13 days. Could beat Agard if time/team were larger.
- Dispute co-pilot for merchants: good merchant impact, uses Disputes
  API, but synthetic dispute data weakens proof and auto-evidence is risky.
- Agent escrow / pay-on-delivery: highest innovation and agentic story,
  but PayPal has no simple escrow API to use honestly, so it risks
  looking simulated, plus compliance questions. Highest build risk.
- Voice/accessibility checkout: strong impact story, too much
  (voice + PayPal + guard) to demo reliably in 13 days.
Verdict under old constraints: Agard wins on combined score
across all five judging criteria with no weak criterion. The challengers
win on one criterion and lose on execution/demo risk. Cheap upgrade
without switching: add subscription-renewal flags and a dispute-note
explainer to Agard's post-purchase review list.
Ultra modules BUILT 31 Oct (skeleton, tested, not yet ULB-trained):
ml_model.py (PyTorch MLP, torch-optional — falls back to rule guard if
torch missing; synthetic demo training: TP 5, FP 0, TN 7, FN 0, risky
proba 1.0, safe proba ~0.00003, tested with the PromptShield venv's
torch 2.15 CPU; Agard's own venv currently has no torch, so /ml
there correctly reports torch_available=False with no crash),
subscriptions.py (/subscriptions flags Music Stream 6x and Cloud Storage
4x as recurring candidates, cancellation manual), disputes.py
(/disputes returns an evidence pack + draft note with sent=False).
ULB open-data training/evaluation is NOT yet run and must not be claimed.
Verdict under CORRECTED constraints (31 Oct): build Agard Ultra —
keep the guarded checkout core, and add, in parallel: (1) a PyTorch
risk model trained on open data (ULB European card data first: 284,807
transactions, 492 fraud, open database licence — do not redistribute
the data, cite it, report precision/recall and false positives
separately, and state clearly it was NOT trained on PayPal data and
does NOT prove PayPal fraud detection; in live checkout the rule guard
remains the gate and the ML score is an additional, explained signal);
(2) a Subscription Guardian module (recurring-pattern flags, renewal
alerts, manual cancel guidance); (3) a Dispute Co-pilot module
(explain a flagged transaction, assemble an evidence pack, draft a
dispute note a human sends — never auto-accepted; OpenCV only where
it earns its place, e.g. preprocessing a receipt image for that pack);
(4) a review-hold note for first-time merchants (our app's hold, NOT
a claimed PayPal escrow). Parallel Track B — VERIFIED 31 Oct from PayPal's official rules page:
"An Entrant may submit more than one Submission, however, each
Submission must be unique and substantially different from each of the
Entrant's other Submissions." Open data / open source are also allowed
in the official rules, provided the entrant is authorised under the
tool/data licence and the submission enhances/builds on the underlying
open-source product. So a standalone Subscription Guardian, substantially
different from Agard, is a legitimate second entry — not an
assumption. Third-party technical assistance is also allowed in the
rules, provided the submission remains the entrant's own work product
and ideas.

## Remaining timeline
31 Oct–2 Nov: sandbox proof + AG Grid dashboard start. 3–5 Nov: dashboard
+ end-to-end + scope freeze. 6 Nov: Mozark only. 7–9 Nov: polish + README
from clean clone. 10 Nov: video. 11 Nov evening IST: submit (deadline
13 Nov 01:30 IST).
