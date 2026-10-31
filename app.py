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

PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agard — the agent that guards every buy</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:900px;margin:0 auto;padding:24px;color:#111;background:#f7f7f8}
h1{font-size:28px;margin-bottom:4px}.sub{color:#555;margin-top:0}
.card{background:#fff;border:1px solid #ddd;border-radius:12px;padding:16px;margin:12px 0}
input,button{font-size:16px;padding:10px;border-radius:8px;border:1px solid #ccc}
button{background:#111;color:#fff;cursor:pointer;border-color:#111} button:disabled{background:#999;border-color:#999;cursor:not-allowed}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:13px;font-weight:600}
.safe{background:#dcfce7}.warn{background:#fef9c3}.blocked{background:#fee2e2}
.riskbar{height:10px;background:#eee;border-radius:6px;overflow:hidden}.riskfill{height:100%;background:#16a34a}
.muted{color:#666;font-size:14px}.verdict{font-weight:600}
</style></head><body>
<h1>Agard</h1><p class="sub">The agent that guards every buy. Agent finds it, guard checks it, <b>you</b> approve it — then PayPal sandbox checkout.</p>
<div class="card"><b>Try it in 30 seconds:</b> search <i>earbuds</i> with a $100 budget. The $299 new-merchant item is blocked. The $49.99 established-merchant item can be approved.
<p class="muted" id="mode">Checking mode…</p>
<label>What do you want? <input id="q" value="earbuds" size="20"></label>
<label> Budget (USD) <input id="budget" type="number" value="100" style="width:90px"></label>
<button onclick="doSearch()">Ask the agent</button>
<button onclick="quick('p2')">Try the risky one</button>
<button onclick="quick('p1')">Try the safe one</button>
</div>
<div id="results"></div>
<div class="card"><h2>Transactions</h2><div id="tx" class="muted">None yet.</div>
<button onclick="loadTx()">Refresh transactions</button></div>
<p class="muted">Sandbox / synthetic data only. No real money, no production PayPal data. Mock products are labelled in the API; the guard is a statistical flag, not a production fraud system.</p>
<script>
async function doSearch(){
  const q=document.getElementById('q').value, budget=document.getElementById('budget').value;
  const r=await fetch(`/search?q=${encodeURIComponent(q)}&budget_usd=${budget}`);
  const items=await r.json(); const el=document.getElementById('results'); el.innerHTML='';
  if(!items.length){el.innerHTML='<div class="card">No matches. Try “earbuds” or “headphones”.</div>';return;}
  items.forEach(p=>{
    const cls=p.blocked?'blocked':(p.risk>=40?'warn':'safe');
    const label=p.blocked?'BLOCKED':(p.risk>=40?'CAUTION':'SAFE');
    const btn=p.blocked?`<button onclick="overrideCheckout('${p.id}')">Human override (logged) — $${p.price_usd}</button>`:`<button onclick="approve('${p.id}')">Approve checkout — $${p.price_usd}</button>`;
    el.innerHTML+=`<div class="card"><h3>${p.name} — $${p.price_usd}</h3><p class="muted">${p.merchant}</p>
    <span class="badge ${cls}">${label} · risk ${p.risk}/100</span><div class="riskbar"><div class="riskfill" style="width:${p.risk}%;background:${p.blocked?'#dc2626':(p.risk>=40?'#d97706':'#16a34a')}"></div></div>
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
  document.getElementById('tx').innerHTML=t.length?t.map(x=>`<div>${x.product} — $${x.amount} — ${x.status} ${x.order_id||''}</div>`).join(''):'None yet.';
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
