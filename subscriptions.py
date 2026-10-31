"""Subscription Guardian module — recurring-pattern detection.

Input: a list of transactions (product, amount, merchant/product key).
Output: candidates where the same product+amount appears 2+ times.
This is a flag for human review, not an auto-cancellation. Cancelling a
real subscription is consequential and stays manual (or, in a future
sandbox step, via the PayPal Subscriptions API with explicit approval).
Mock recurring history is used in the demo until real sandbox
transactions exist; it is labelled as such in the API response.
"""

MOCK_HISTORY = [
    {"product": "Music Stream Monthly", "amount": 9.99, "merchant": "MusicStream", "occurrences": 6, "period": "monthly"},
    {"product": "Cloud Storage Monthly", "amount": 4.99, "merchant": "CloudBox", "occurrences": 4, "period": "monthly"},
    {"product": "Wireless Earbuds Pro", "amount": 49.99, "merchant": "AudioHub", "occurrences": 1, "period": "one-off"},
]


def detect_recurring(transactions, history=None):
    grouped = {}
    for t in (history or []):
        # History entries already carry an occurrence count.
        if t.get("occurrences", 0) >= 2:
            grouped[(t.get("product"), t.get("amount"))] = t["occurrences"]
    for t in (transactions or []):
        key = (t.get("product"), t.get("amount"))
        grouped[key] = grouped.get(key, 0) + 1
    out = []
    for (product, amount), count in grouped.items():
        if count >= 2:
            out.append({"product": product, "amount": amount, "occurrences": count,
                        "flag": "RECURRING_CANDIDATE",
                        "action": "Review: is this subscription still wanted? Cancellation stays manual."})
    return out
