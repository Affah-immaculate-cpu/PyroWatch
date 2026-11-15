import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pyro.prediction import FEATURES, make_cell_days, train_and_evaluate
from pyro.processing import load_training_hotspots, training_fingerprint


MODEL_PATH = PROJECT_ROOT / "models" / "hotspot_model.joblib"

training_data = load_training_hotspots()
if training_data.empty:
    raise SystemExit("No valid training observations were found in data/training/.")

cell_days = make_cell_days(training_data)
model, metrics, info = train_and_evaluate(cell_days)
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

artifact = {
    "model": model,
    "features": FEATURES,
    "cell_size_degrees": 0.25,
    "trained_at_utc": datetime.now(timezone.utc).isoformat(),
    "trained_through": training_data["date"].max().date().isoformat(),
    "training_observations": len(training_data),
    "training_dates": int(training_data["date"].nunique()),
    "training_fingerprint": training_fingerprint(),
    "evaluation": metrics,
    "evaluation_info": info,
}
joblib.dump(artifact, MODEL_PATH, compress=3)

print(f"Saved trained hotspot model to {MODEL_PATH}")
print(f"Training observations: {len(training_data):,}")
print(f"Training date range: {training_data['date'].min().date()} to {artifact['trained_through']}")
print(f"Evaluation cutoff: {info['cutoff']}")
print("\nHeld-out evaluation metrics")
print(metrics.round(3))
