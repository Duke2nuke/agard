"""Agard user policy — the human's rules, in plain data, not agent whims.

The agent may propose, the guard may score, but only this policy + an
explicit human approval may move money. The agent can never change the
policy, raise its own budget, or approve its own proposal.

Decision tiers (see guard.py for scoring):
- SAFE (risk < 40): one-click human approval.
- CAUTION (40-69): human approval + must acknowledge the listed reasons
  (the UI asks for that acknowledgement; the API requires acknowledged=True).
- BLOCKED (70+): the agent is stopped. A human may still override, but
  only by acknowledging every reason AND confirming override=True, and
  the transaction is then logged as USER_OVERRIDDEN — never as
  agent-approved. An override is a human decision with an audit trail,
  not a guard bypass.
"""
from dataclasses import dataclass


@dataclass
class Policy:
    budget_usd: float = 100.0
    # A first-time merchant may never be auto-approved above this, even
    # if the price spike alone would not block it.
    new_merchant_max_usd: float = 75.0
    require_approval_always: bool = True

    def decision(self, risk, blocked, price_usd, is_new_merchant):
        if blocked:
            return "BLOCKED"
        if risk >= 40:
            return "CAUTION"
        if is_new_merchant and price_usd > self.new_merchant_max_usd:
            return "CAUTION"
        return "SAFE"


DEFAULT_POLICY = Policy()
