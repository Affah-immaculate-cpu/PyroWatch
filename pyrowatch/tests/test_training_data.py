import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from pyro import processing
from pyro.prediction import make_cell_days, predict_next_day, train_and_evaluate


class TrainingDataIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.raw_dir = root / "raw"
        self.training_dir = root / "training"
        for base in (self.raw_dir, self.training_dir):
            (base / "modis").mkdir(parents=True)
            (base / "viirs").mkdir(parents=True)
        self.raw_patch = patch.object(processing, "RAW_DIR", self.raw_dir)
        self.training_patch = patch.object(processing, "TRAINING_DIR", self.training_dir)
        self.raw_patch.start()
        self.training_patch.start()
        self.addCleanup(self.raw_patch.stop)
        self.addCleanup(self.training_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

    @staticmethod
    def write_firms_csv(folder: Path, name: str, latitude: float) -> None:
        pd.DataFrame([{
            "latitude": latitude,
            "longitude": -1.5,
            "acq_date": "2026-01-01",
            "acq_time": 1200,
            "satellite": "N",
            "frp": 4.2,
            "confidence": "h",
        }]).to_csv(folder / name, index=False)

    def test_training_loader_and_dashboard_loader_use_separate_folders(self):
        self.write_firms_csv(self.training_dir / "viirs", "training.csv", 6.0)
        self.write_firms_csv(self.raw_dir / "viirs", "display.csv", 7.0)

        training = processing.load_training_hotspots()
        dashboard = processing.load_raw_hotspots()

        self.assertEqual(training["source_file"].tolist(), ["training.csv"])
        self.assertEqual(training["latitude"].tolist(), [6.0])
        self.assertEqual(dashboard["source_file"].tolist(), ["display.csv"])
        self.assertEqual(dashboard["latitude"].tolist(), [7.0])

    def test_training_file_listing_excludes_display_files(self):
        self.write_firms_csv(self.training_dir / "modis", "training.csv", 6.0)
        self.write_firms_csv(self.raw_dir / "modis", "display.csv", 7.0)

        files = processing.list_training_files()

        self.assertEqual(files["file"].tolist(), ["training.csv"])

    def test_training_loader_rejects_csv_missing_required_columns(self):
        pd.DataFrame([{"latitude": 6.0, "longitude": -1.5}]).to_csv(
            self.training_dir / "modis" / "invalid.csv", index=False
        )

        with self.assertRaisesRegex(ValueError, "acq_date"):
            processing.load_training_hotspots()

    def test_model_trains_and_returns_next_day_probabilities(self):
        start = pd.Timestamp("2026-01-01")
        observations = []
        for day in range(24):
            if day % 2 == 0:
                observations.append({
                    "latitude": 6.0,
                    "longitude": -1.0,
                    "date": start + pd.Timedelta(days=day),
                })
            if day % 3 == 0:
                observations.append({
                    "latitude": 6.2,
                    "longitude": -1.2,
                    "date": start + pd.Timedelta(days=day),
                })
        cell_days = make_cell_days(pd.DataFrame(observations))

        model, metrics, _ = train_and_evaluate(cell_days)
        forecasts = predict_next_day(model, cell_days, cell_days["date"].max())

        self.assertEqual(len(metrics), 2)
        self.assertFalse(forecasts.empty)
        self.assertTrue(forecasts["probability"].between(0, 1).all())


if __name__ == "__main__":
    unittest.main()
