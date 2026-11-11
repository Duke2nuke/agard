"""Agard demo app — judge-ready demo UI + API.

Run: .venv/bin/python app.py  ->  http://127.0.0.1:5000
Flow judges see (under 60 seconds):
  1. Type what you want + a budget, e.g. "earbuds", $100
  2. Agent ranks products, guard scores each one with a plain-English verdict
  3. Risky product is BLOCKED before money moves — no approve button
  4. Safe product shows "Approve checkout" — only after you click does it
     create a PayPal sandbox order (or a clearly-labelled MOCK order if no
     sandbox credentials are set). No money moves on search alone.

Mock mode unless PayPal sandbox credentials are set in .env.
Sandbox mode uses paypal_client.py (Orders API, create + capture).
"""
import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, jsonify, request, render_template_string
from guard import score
from policy import DEFAULT_POLICY
from products import search as product_search
import paypal_client
import ml_model
import subscriptions as sub_mod
import disputes as dispute_mod

app = Flask(__name__)

# Realistic past earbuds/headphones spend in USD — the guard's baseline.
USUAL_USD = [42, 48, 55, 50, 60, 45, 52]
TRANSACTIONS = []

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agard — the agent that guards every buy</title>
<style>
*{box-sizing:border-box}
:root{--pp-dark:#003087;--pp-blue:#0070e0;--pp-blue-hover:#005ea6;--ink:#2c2e2f;--muted:#687173;--bg:#f5f7fa;--line:#d9dee3;--card-line:#e3e6ea;--green:#007a3d;--green-bg:#e6f7ee;--amber:#8a5a00;--amber-bg:#fff4d6;--red:#b42318;--red-bg:#fdecea}
html{-webkit-text-size-adjust:100%}
body{font-family:"Helvetica Neue",Helvetica,Arial,system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;color:var(--ink);background:var(--bg);line-height:1.5;-webkit-tap-highlight-color:transparent}
a{color:var(--pp-blue)}
.topbar{position:sticky;top:0;z-index:10;background:#fff;border-bottom:1px solid var(--card-line)}
.topbar-inner{max-width:720px;margin:0 auto;padding:12px 16px;display:flex;align-items:center;gap:10px}
.brand{display:flex;align-items:center;gap:9px;font-size:21px;font-weight:800;color:var(--pp-dark);letter-spacing:-.02em}
.brand svg{flex:none}
.pp-chip{margin-left:auto;font-size:12px;font-weight:700;color:var(--pp-dark);background:#e8f1fb;border:1px solid #cfe2f5;padding:4px 10px;border-radius:999px;white-space:nowrap}
.container{max-width:720px;margin:0 auto;padding:0 16px 40px}
.hero{padding:26px 0 6px}
.hero h1{font-size:29px;line-height:1.2;margin:0 0 8px;color:var(--pp-dark);letter-spacing:-.02em}
.hero p{margin:0;color:#3c4043;font-size:16px;max-width:56ch}
.card{background:#fff;border:1px solid var(--card-line);border-radius:16px;padding:20px;margin:16px 0;box-shadow:0 1px 2px rgba(16,24,40,.05)}
.card h2{font-size:18px;margin:0 0 4px;color:var(--pp-dark)}
.card h3{font-size:17px;margin:0}
.lede{font-size:15px;margin:0 0 4px}
.lede b{color:var(--pp-dark)}
.muted{color:var(--muted);font-size:14px}
.fineprint{color:var(--muted);font-size:13px;line-height:1.55}
.field{margin:12px 0}
.field label{display:block;font-size:14px;font-weight:600;margin-bottom:6px}
.field input{width:100%;font-size:16px;padding:12px;border-radius:10px;border:1px solid #b7bfc6;background:#fff;color:var(--ink)}
.field input:focus{outline:none;border-color:var(--pp-blue);box-shadow:0 0 0 3px rgba(0,112,224,.18)}
.btn-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
button{font-family:inherit;font-size:15px;font-weight:600;padding:12px 20px;border-radius:999px;cursor:pointer;border:1px solid transparent}
.btn-primary{background:var(--pp-blue);color:#fff;width:100%}
.btn-primary:hover{background:var(--pp-blue-hover)}
.btn-secondary{background:#fff;color:var(--pp-blue);border-color:var(--pp-blue)}
.btn-secondary:hover{background:#eef6ff}
.btn-outline-danger{background:#fff;color:var(--red);border-color:#e5a49e;width:100%}
.btn-outline-danger:hover{background:var(--red-bg)}
button:disabled{background:#9aa3ab;border-color:#9aa3ab;cursor:not-allowed}
.btn-block{width:100%;margin-top:12px}
.mode-line{font-size:13px;color:var(--muted);margin:10px 0 0}
.badge{display:inline-block;padding:4px 12px;border-radius:999px;font-size:12px;font-weight:700;letter-spacing:.02em}
.safe{background:var(--green-bg);color:var(--green)}
.warn{background:var(--amber-bg);color:var(--amber)}
.blocked{background:var(--red-bg);color:var(--red)}
.riskbar{height:8px;background:#e9ecef;border-radius:999px;overflow:hidden;margin:12px 0 4px}
.riskfill{height:100%;border-radius:999px}
.verdict{font-weight:600;font-size:15px;margin:10px 0 6px}
.product ul{margin:6px 0 0;padding-left:19px;color:#4a5054;font-size:14px;line-height:1.55}
.product ul li{margin:3px 0}
.prod-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
.price{font-size:17px;font-weight:800;color:var(--pp-dark);white-space:nowrap}
.blocked-card{border-color:#f3c2be;background:#fff9f8}
.tx-row{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px;padding:10px 0;border-bottom:1px solid #eef1f4;font-size:14px}
.tx-row:last-child{border-bottom:none}
.tx-amt{font-weight:700;color:var(--pp-dark);white-space:nowrap}
pre{background:var(--bg);border:1px solid var(--card-line);border-radius:12px;padding:12px;font-size:12.5px;line-height:1.5;overflow-x:auto;white-space:pre-wrap;word-break:break-word;margin:12px 0 0}
@media (min-width:640px){
  .hero{padding:36px 0 10px}
  .hero h1{font-size:34px}
  .card{padding:24px}
  .form-row{display:flex;gap:12px;align-items:flex-end}
  .form-row .field{flex:1;margin:12px 0 0}
  .btn-primary{width:auto}
  .btn-outline-danger{width:auto}
  .btn-block{width:100%}
}
</style></head><body>
<header class="topbar"><div class="topbar-inner">
<span class="brand"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 2l8 3v6c0 5.25-3.4 9.74-8 11-4.6-1.26-8-5.75-8-11V5l8-3z" fill="#0070e0"/><path d="M12 4.6l5.4 2.02v4.13c0 3.9-2.3 7.2-5.4 8.3-3.1-1.1-5.4-4.4-5.4-8.3V6.62L12 4.6z" fill="#003087"/><path d="M10.6 12.6l-1.9-1.9-1 1 2.9 2.9 5.7-5.7-1-1-4.7 4.7z" fill="#fff"/></svg>Agard</span>
<span class="pp-chip">Built with PayPal Sandbox</span>
</div></header>
<main class="container">
<div class="hero">
<h1>The agent that guards every buy.</h1>
<p>Agard finds it, the guard checks it, <b>you</b> approve it — then PayPal sandbox checkout. No money moves on search alone.</p>
</div>
<div class="card"><p class="lede"><b>Try it in 30 seconds:</b> search <i>earbuds</i> with a $100 budget. The $299 new-merchant item is blocked. The $49.99 established-merchant item can be approved.</p>
<p class="mode-line" id="mode">Checking mode…</p>
<div class="form-row">
<div class="field"><label for="q">What do you want?</label><input id="q" value="earbuds" autocomplete="off"></div>
<div class="field"><label for="budget">Budget (USD)</label><input id="budget" type="number" value="100" inputmode="decimal"></div>
</div>
<div class="btn-row">
<button class="btn-primary" onclick="doSearch()">Ask the agent</button>
<button class="btn-secondary" onclick="quick('p2')">Try the risky one</button>
<button class="btn-secondary" onclick="quick('p1')">Try the safe one</button>
</div>
</div>
<div id="results"></div>
<div class="card"><h2>Transactions</h2><div id="tx" class="muted">None yet.</div>
<div class="btn-row"><button class="btn-secondary" onclick="loadTx()">Refresh transactions</button></div></div>
<p class="fineprint">Sandbox / synthetic data only. No real money, no production PayPal data. Mock products are labelled in the API; the guard is a statistical flag, not a production fraud system.</p>
</main>
<script>
async function doSearch(){
  const q=document.getElementById('q').value, budget=document.getElementById('budget').value;
  const r=await fetch(`/search?q=${encodeURIComponent(q)}&budget_usd=${budget}`);
  const items=await r.json(); const el=document.getElementById('results'); el.innerHTML='';
  if(!items.length){el.innerHTML='<div class="card">No matches. Try “earbuds” or “headphones”.</div>';return;}
  items.forEach(p=>{
    const cls=p.blocked?'blocked':(p.risk>=40?'warn':'safe');
    const label=p.blocked?'BLOCKED':(p.risk>=40?'CAUTION':'SAFE');
    const btn=p.blocked?`<button class="btn-outline-danger btn-block" onclick="overrideCheckout('${p.id}')">Human override (logged) — $${p.price_usd}</button>`:`<button class="btn-primary btn-block" onclick="approve('${p.id}')">Approve checkout — $${p.price_usd}</button>`;
    el.innerHTML+=`<div class="card product ${p.blocked?'blocked-card':''}"><div class="prod-head"><h3>${p.name}</h3><span class="price">$${p.price_usd}</span></div><p class="muted">${p.merchant}</p>
    <span class="badge ${cls}">${label} · risk ${p.risk}/100</span><div class="riskbar"><div class="riskfill" style="width:${p.risk}%;background:${p.blocked?'#d92d20':(p.risk>=40?'#f59e0b':'#00a94f')}"></div></div>
    <p class="verdict">${p.verdict}</p><ul>${p.reasons.map(x=>`<li>${x}</li>`).join('')}</ul>${btn}<div id="out-${p.id}"></div></div>`;
  });
}
async function approve(id){
  const budget=document.getElementById('budget').value;
  const r=await fetch('/checkout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:id,budget_usd:parseFloat(budget),approved:true,acknowledged:true})});
  const d=await r.json();
  document.getElementById('out-'+id).innerHTML='<pre>'+JSON.stringify(d,null,2)+'</pre>';
  if(d.approve_url) document.getElementById('out-'+id).innerHTML+=`<p><a href="${d.approve_url}" target="_blank">Approve this sandbox order on PayPal (sandbox buyer) →</a></p>`;
  loadTx();
}
async function overrideCheckout(id){
  if(!confirm('This purchase was BLOCKED by the guard. Override it as a human? It will be logged as USER_OVERRIDDEN, not agent-approved.')) return;
  const budget=document.getElementById('budget').value;
  const r=await fetch('/checkout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:id,budget_usd:parseFloat(budget),approved:true,acknowledged:true,override:true})});
  const d=await r.json();
  document.getElementById('out-'+id).innerHTML='<pre>'+JSON.stringify(d,null,2)+'</pre>'; loadTx();
}
async function quick(id){
  document.getElementById('q').value='earbuds'; await doSearch();
  document.querySelectorAll('button').forEach(b=>{});
  setTimeout(()=>{const el=document.getElementById('out-'+id); if(el) el.scrollIntoView({behavior:'smooth'});},100);
}
async function loadTx(){
  const r=await fetch('/transactions'); const t=await r.json();
  document.getElementById('tx').innerHTML=t.length?t.map(x=>`<div class="tx-row"><span>${x.product}</span><span class="tx-amt">$${x.amount} · ${x.status}</span></div>`).join(''):'None yet.';
  const m=await fetch('/mode'); const mj=await m.json();
  document.getElementById('mode').textContent='Mode: '+mj.mode+(mj.mode==='MOCK'?' — no PayPal credentials set, so checkouts are labelled mock, not real sandbox orders.':' — real PayPal sandbox API.');
}
loadTx(); doSearch();
</script></body></html>"""


def _scored(query, budget):
    out = []
    for p in product_search(query):
        risk, reasons, blocked, verdict = score(
            p["price_usd"], USUAL_USD,
            is_new_merchant=p["is_new_merchant"],
            over_budget=p["price_usd"] > budget)
        if p.get("prior_orders", 0) > 0:
            reasons = reasons + [f"Merchant history: {p['prior_orders']} prior orders with you"]
        else:
            reasons = reasons + ["Merchant history: 0 prior orders — first time with this seller"]
        decision = DEFAULT_POLICY.decision(risk, blocked, p["price_usd"], p["is_new_merchant"])
        out.append({**p, "risk": risk, "reasons": reasons, "blocked": blocked, "verdict": verdict, "decision": decision})
    # Agent ranking: safe first, then by price fit to budget.
    out.sort(key=lambda x: (x["blocked"], x["risk"], abs(x["price_usd"] - budget)))
    return out


@app.route("/")
def home():
    return render_template_string(PAGE)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "mode": "SANDBOX" if paypal_client.has_credentials() else "MOCK"})


@app.route("/mode")
def mode():
    return jsonify({"mode": "SANDBOX" if paypal_client.has_credentials() else "MOCK"})


@app.route("/search")
def search():
    q = request.args.get("q", "earbuds")
    try:
        budget = float(request.args.get("budget_usd", 100))
    except ValueError:
        budget = 100.0
    return jsonify(_scored(q, budget))


@app.route("/checkout", methods=["POST"])
def checkout():
    data = request.get_json(force=True, silent=True) or {}
    pid = data.get("product_id")
    try:
        budget = float(data.get("budget_usd", 100))
    except (TypeError, ValueError):
        budget = 100.0
    approved = bool(data.get("approved"))
    acknowledged = bool(data.get("acknowledged"))
    override = bool(data.get("override"))
    prod = next((p for p in _scored("", budget) if p["id"] == pid), None)
    if not prod:
        return jsonify({"error": "product not found"}), 404
    if prod["blocked"] and not (override and acknowledged):
        # Agent is stopped. A human override needs both flags, and is logged
        # as USER_OVERRIDDEN below — never as agent-approved.
        return jsonify({"status": "BLOCKED", "product": prod, "risk": prod["risk"],
                        "reasons": prod["reasons"], "verdict": prod["verdict"],
                        "decision": prod["decision"],
                        "override_instructions": "A human may override only with override=true AND acknowledged=true, after reading every reason."})
    if prod["decision"] == "CAUTION" and approved and not acknowledged:
        return jsonify({"status": "NEEDS_ACKNOWLEDGEMENT", "product": prod, "risk": prod["risk"],
                        "reasons": prod["reasons"], "verdict": prod["verdict"],
                        "decision": prod["decision"]})
    if not approved:
        # Two-step flow: guard check first, money only after explicit approval.
        return jsonify({"status": "NEEDS_APPROVAL", "product": prod, "risk": prod["risk"],
                        "reasons": prod["reasons"], "verdict": prod["verdict"],
                        "decision": prod["decision"]})
    tx_status = "USER_OVERRIDDEN" if (prod["blocked"] and override) else "APPROVED_BY_HUMAN"
    if paypal_client.has_credentials():
        try:
            order_id, approve = paypal_client.create_order(prod["price_usd"], prod["name"])
            TRANSACTIONS.append({"product": prod["name"], "amount": prod["price_usd"], "order_id": order_id, "status": f"CREATED_SANDBOX_{tx_status}"})
            return jsonify({"status": f"CREATED_SANDBOX_{tx_status}", "order_id": order_id, "approve_url": approve,
                            "risk": prod["risk"], "reasons": prod["reasons"], "verdict": prod["verdict"],
                            "decision": prod["decision"],
                            "next": "Approve on PayPal sandbox, then capture — capture endpoint to be wired in the sandbox step."})
        except Exception as e:  # noqa: BLE001 — surface the sandbox error, don't hide it
            return jsonify({"status": "SANDBOX_ERROR", "error": str(e)}), 502
    TRANSACTIONS.append({"product": prod["name"], "amount": prod["price_usd"], "order_id": "MOCK-001", "status": f"MOCK_{tx_status}"})
    return jsonify({"status": f"MOCK_{tx_status}", "note": "No PayPal credentials set — this is a mock checkout, not a real sandbox order.",
                    "product": prod, "risk": prod["risk"], "reasons": prod["reasons"], "verdict": prod["verdict"],
                    "decision": prod["decision"]})


@app.route("/ml")
def ml_status():
    model, metrics = ml_model.train_synthetic()
    return jsonify({"torch_available": ml_model.TORCH_AVAILABLE, "metrics": metrics,
                    "note": "Synthetic demo training only. ULB open-data evaluation not yet run — do not claim ULB accuracy."})


@app.route("/subscriptions")
def subscriptions_route():
    return jsonify({"recurring_candidates": sub_mod.detect_recurring(TRANSACTIONS, history=sub_mod.MOCK_HISTORY),
                    "note": "Mock history included in demo; flags are for human review, cancellation stays manual."})


@app.route("/disputes", methods=["POST"])
def disputes_route():
    data = request.get_json(force=True, silent=True) or {}
    tx = data.get("transaction") or (TRANSACTIONS[-1] if TRANSACTIONS else {"product": "No transaction yet", "amount": 0, "status": "NONE", "order_id": ""})
    return jsonify(dispute_mod.evidence_pack(tx, reasons=data.get("reasons"), risk=data.get("risk"), decision=data.get("decision")))


@app.route("/transactions")
def transactions():
    return jsonify(TRANSACTIONS)


if __name__ == "__main__":
    # host 0.0.0.0 so it can be reached from the laptop / Render-style run too
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
