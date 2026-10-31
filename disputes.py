"""Dispute Co-pilot module — evidence pack + draft note, human sends.

Never auto-accepts, auto-files, or auto-sends a dispute. It assembles
what a human needs to decide: the transaction, the guard reasons, the
risk/decision, and a draft note the human can edit and send themselves
via PayPal. Receipt-image preprocessing with OpenCV is an optional
future step for this pack (resize/denoise/contrast); until it is wired
and tested, this module does not claim any image work.
"""


def evidence_pack(transaction, reasons=None, risk=None, decision=None):
    reasons = reasons or []
    draft = (
        f"Dispute note draft (edit before sending — not sent automatically):\n"
        f"Transaction: {transaction.get('product')} — ${transaction.get('amount')} "
        f"({transaction.get('status')}, order {transaction.get('order_id')}).\n"
        f"Why it was flagged: {'; '.join(reasons) if reasons else 'No guard reasons recorded.'}\n"
        f"Risk: {risk}, decision: {decision}.\n"
        f"Request: please review this transaction."
    )
    return {
        "transaction": transaction,
        "reasons": reasons,
        "risk": risk,
        "decision": decision,
        "draft_note": draft,
        "sent": False,
        "note": "Draft only. A human must review, edit and send it via PayPal.",
    }
