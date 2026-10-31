"""Agard guard — anomaly flag for transactions/products.

Ported conceptually from the Day 2 server-metrics detector:
same-context baseline + median / MAD modified z-score, pure Python, no deps.
This is a statistical flag, NOT a production fraud system.
Sandbox/synthetic data only.

Fixes vs scaffold (31 Oct 2026):
- Asymmetric risk: a price BELOW your usual spend is a good deal, not a
  fraud risk. Only upward spikes add risk. This fixes the scaffold bug where
  a $29.99 safe product scored 50 just for being cheaper than usual.
- MAD floor: MAD is floored at 15% of the median, so a tight history
  (e.g. all past buys $45-$55) does not turn a $30 buy into a huge z-score.
- Plain-English explanation: score() now also returns a one-sentence
  verdict the UI and demo can show verbatim.
"""
import statistics


def _median_mad(values):
    if not values:
        return 0.0, 0.0
    med = statistics.median(values)
    mad = statistics.median([abs(v - med) for v in values]) or 0.0
    # Floor MAD so tiny spread does not explode the z-score.
    mad = max(mad, 0.15 * med if med else 1.0)
    return med, mad


def explain(risk, reasons, blocked):
    if blocked:
        return "Blocked: this purchase looks risky, so Agard stopped it before any money moved."
    if risk >= 40:
        return "Caution: something here is unusual. Review it before you approve."
    return "Looks safe: price fits your usual pattern, merchant is known, and it is within your budget."


def score(amount, usual_amounts, is_new_merchant=False, over_budget=False):
    """Return (risk_score 0-100, reasons list, blocked bool, verdict str)."""
    reasons = []
    med, mad = _median_mad(usual_amounts)
    # Only upward deviation is a spending risk.
    z = 0.6745 * (amount - med) / mad if mad and amount > med else 0.0
    risk = 0
    if z > 3.5:
        risk += 50
        reasons.append(f"Price is far above your usual spend (modified z={z:.1f}, usual median=${med:.0f})")
    elif z > 2.0:
        risk += 25
        reasons.append(f"Price is higher than usual (modified z={z:.1f}, usual median=${med:.0f})")
    if amount < med:
        reasons.append(f"Below your usual spend (${med:.0f}) — good value, not a risk flag")
    if is_new_merchant:
        risk += 30
        reasons.append("Merchant is new — no history with you")
    if over_budget:
        risk += 40
        reasons.append("This would breach the spending limit you set")
    risk = min(100, risk)
    blocked = risk >= 70
    return risk, reasons, blocked, explain(risk, reasons, blocked)


if __name__ == "__main__":
    # Same style as Day 2: normal vs spike vs new merchant, plus cheap-safe.
    usual = [42, 48, 55, 50, 60, 45, 52]
    print("normal $49.99:", score(49.99, usual))
    print("cheap safe $29.99:", score(29.99, usual))
    print("spike $299:", score(299.00, usual))
    print("spike + new merchant:", score(299.00, usual, is_new_merchant=True))
    print("spike + new + over budget:", score(299.00, usual, is_new_merchant=True, over_budget=True))
