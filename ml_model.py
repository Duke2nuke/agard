"""Agard Ultra — PyTorch risk model (optional, never overrides the rule guard).

Design, following the PromptShield pattern:
- If torch is not installed, available=False and the rule guard in guard.py
  is the only scorer. No crash, no fake ML score.
- If torch is installed, a small MLP scores 4 honest features:
  amount / usual-median, new-merchant (0/1), over-budget (0/1),
  price-spike z (clipped). It is trained here on SYNTHETIC labelled data
  for the demo/test path only.
- The ULB open-data path (not yet run — needs a Kaggle/ULB download with
  its licence respected, data never committed to the repo) will replace
  the synthetic training set with real open data, with precision/recall
  and false positives reported separately. Until that evaluation is run
  and saved, the submission must NOT claim ULB accuracy.
- The ML score is an additional signal. The rule guard remains the gate:
  a BLOCKED rule decision stays blocked even if the ML score is low,
  and a high ML score alone never blocks without a rule reason — it
  raises the decision to CAUTION for human review.
"""
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except Exception:  # noqa: BLE001 — torch is optional by design
    torch = None
    nn = None
    TORCH_AVAILABLE = False


def features(amount, usual_median, is_new_merchant, over_budget, z=0.0):
    return [
        float(amount) / max(usual_median, 1.0),
        1.0 if is_new_merchant else 0.0,
        1.0 if over_budget else 0.0,
        max(-5.0, min(25.0, float(z))),
    ]


if TORCH_AVAILABLE:
    class RiskMLP(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(4, 16), nn.ReLU(),
                nn.Linear(16, 8), nn.ReLU(),
                nn.Linear(8, 1), nn.Sigmoid(),
            )

        def forward(self, x):
            return self.net(x)

    def train_synthetic(seed=0, epochs=200):
        """Train on synthetic labelled examples. Demo/test only, not ULB."""
        torch.manual_seed(seed)
        model = RiskMLP()
        opt = torch.optim.Adam(model.parameters(), lr=0.01)
        loss_fn = nn.BCELoss()
        # (features, label) — high ratio + new merchant + over budget = risky
        raw = [
            ([1.0, 0, 0, 0.0], 0), ([0.6, 0, 0, 0.0], 0), ([1.2, 0, 0, 1.0], 0),
            ([1.8, 0, 0, 3.0], 0), ([2.5, 1, 0, 5.0], 1), ([6.0, 1, 1, 22.0], 1),
            ([5.0, 1, 0, 15.0], 1), ([3.0, 1, 1, 8.0], 1), ([1.1, 1, 0, 0.5], 0),
            ([0.9, 0, 1, 0.0], 0), ([4.0, 0, 1, 10.0], 1), ([1.5, 0, 0, 2.0], 0),
        ]
        X = torch.tensor([r[0] for r in raw], dtype=torch.float32)
        y = torch.tensor([[r[1]] for r in raw], dtype=torch.float32)
        for _ in range(epochs):
            opt.zero_grad()
            loss = loss_fn(model(X), y)
            loss.backward()
            opt.step()
        with torch.no_grad():
            preds = (model(X) >= 0.5).int().flatten().tolist()
            labels = [r[1] for r in raw]
            tp = sum(1 for p, t in zip(preds, labels) if p == 1 and t == 1)
            fp = sum(1 for p, t in zip(preds, labels) if p == 1 and t == 0)
            tn = sum(1 for p, t in zip(preds, labels) if p == 0 and t == 0)
            fn = sum(1 for p, t in zip(preds, labels) if p == 0 and t == 1)
        return model, {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
                       "accuracy": (tp + tn) / len(labels), "dataset": "synthetic-demo-only"}

    def predict_proba(model, feat):
        with torch.no_grad():
            x = torch.tensor([feat], dtype=torch.float32)
            return float(model(x)[0][0])
else:
    def train_synthetic(*args, **kwargs):
        return None, {"error": "torch not installed", "dataset": "none"}

    def predict_proba(model, feat):
        return None
