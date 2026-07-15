from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

import analyze  # noqa: E402


class CommerceOpsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.example = PROJECT / "data" / "example" / "operacao_ecommerce.csv"

    def write_csv(self, frame: pd.DataFrame) -> Path:
        temporary = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        temporary.close()
        path = Path(temporary.name)
        frame.to_csv(path, index=False)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_example_dataset_is_valid(self) -> None:
        frame, quality = analyze.load_data(self.example)
        self.assertEqual(len(frame), 28)
        self.assertEqual(quality["duplicates"], 0)
        self.assertEqual(quality["columns"], 12)

    def test_missing_required_column_is_rejected(self) -> None:
        frame = pd.read_csv(self.example).drop(columns=["orders"])
        with self.assertRaisesRegex(ValueError, "orders"):
            analyze.load_data(self.write_csv(frame))

    def test_invalid_numeric_value_is_rejected(self) -> None:
        frame = pd.read_csv(self.example)
        frame["revenue"] = frame["revenue"].astype("object")
        frame.loc[0, "revenue"] = "valor inválido"
        with self.assertRaisesRegex(ValueError, "inválidos"):
            analyze.load_data(self.write_csv(frame))

    def test_on_time_orders_cannot_exceed_orders(self) -> None:
        frame = pd.read_csv(self.example)
        frame.loc[0, "on_time_orders"] = frame.loc[0, "orders"] + 1
        with self.assertRaisesRegex(ValueError, "on_time_orders"):
            analyze.load_data(self.write_csv(frame))

    def test_duplicate_rows_are_removed_and_reported(self) -> None:
        frame = pd.read_csv(self.example)
        frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
        cleaned, quality = analyze.load_data(self.write_csv(frame))
        self.assertEqual(len(cleaned), 28)
        self.assertEqual(quality["duplicates"], 1)

    def test_metrics_match_expected_totals(self) -> None:
        frame, _ = analyze.load_data(self.example)
        result = analyze.metrics(frame)
        self.assertEqual(result["orders"], 4344)
        self.assertAlmostEqual(result["sla"], 0.8639502762, places=6)
        self.assertAlmostEqual(result["cancellation_rate"], 0.0471915285, places=6)

    def test_risk_ranking_identifies_lognorte(self) -> None:
        frame, _ = analyze.load_data(self.example)
        carriers = analyze.grouped_metrics(frame, "carrier")
        self.assertEqual(carriers.iloc[0]["carrier"], "LogNorte")
        self.assertGreater(carriers.iloc[0]["risk_score"], 50)

    def test_action_plan_contains_priority_and_evidence(self) -> None:
        frame, _ = analyze.load_data(self.example)
        actions = analyze.action_plan(
            analyze.grouped_metrics(frame, "carrier"),
            analyze.grouped_metrics(frame, "channel"),
            analyze.grouped_metrics(frame, "state"),
        )
        self.assertGreaterEqual(len(actions), 3)
        self.assertTrue(all(item["priority"] in {"P1", "P2", "P3"} for item in actions))
        self.assertTrue(all(item["evidence"] for item in actions))


if __name__ == "__main__":
    unittest.main()
