import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import har_pipeline


def recording(subject, label, count, session="1"):
    return pd.DataFrame({
        "subjek": subject, "sesi": session, "posisi": "genggam", "label": label,
        "timestamp_ms": range(0, count * 20, 20), "ax": 1.0, "ay": 2.0, "az": 3.0,
    })


class SubjectSplitTest(unittest.TestCase):
    def test_partition_precedes_feature_extraction(self):
        data = pd.concat([
            recording(subject, label, 96)
            for subject in ("S01", "S02", "S03")
            for label in har_pipeline.CLASSES
        ], ignore_index=True)
        with patch.object(har_pipeline, "extract_windows",
                          wraps=har_pipeline.extract_windows) as extract:
            folds = list(har_pipeline.subject_folds(data))

        self.assertEqual(len(folds), 3)
        self.assertEqual(extract.call_count, 2 * len(folds))
        partitions = [call.args[0] for call in extract.call_args_list]
        seen = set()
        for index, (subject, X_train, _, X_test, _) in enumerate(folds):
            train, test = partitions[2 * index : 2 * index + 2]
            self.assertEqual(set(test["subjek"]), {subject})
            self.assertNotIn(subject, set(train["subjek"]))
            self.assertTrue(set(train.index).isdisjoint(test.index))
            self.assertTrue(seen.isdisjoint(test.index))
            seen.update(test.index)
            self.assertEqual(X_train.shape, (12, 20))
            self.assertEqual(X_test.shape, (6, 20))
        self.assertEqual(seen, set(data.index))

    def test_session_folds_partition_precedes_feature_extraction(self):
        data = pd.concat([
            recording("S01", label, 96, session=f"{label}_{ses}")
            for ses in ("a", "b", "c")
            for label in har_pipeline.CLASSES
        ], ignore_index=True)
        with patch.object(har_pipeline, "extract_windows",
                          wraps=har_pipeline.extract_windows) as extract:
            folds = list(har_pipeline.evaluation_folds(data))

        self.assertEqual(len(folds), 3)
        self.assertEqual(extract.call_count, 2 * len(folds))
        partitions = [call.args[0] for call in extract.call_args_list]
        seen = set()
        for index, (fold_name, X_train, y_train, X_test, y_test) in enumerate(folds):
            train, test = partitions[2 * index : 2 * index + 2]
            self.assertTrue(fold_name.startswith("Sesi-"))
            self.assertTrue(set(train["sesi"]).isdisjoint(set(test["sesi"])))
            self.assertTrue(seen.isdisjoint(test.index))
            seen.update(test.index)
            self.assertEqual(X_train.shape, (12, 20))
            self.assertEqual(X_test.shape, (6, 20))
            self.assertEqual(set(y_test), set(har_pipeline.CLASS_IDS))
        self.assertEqual(seen, set(data.index))

    def test_window_stays_inside_timestamp_reset_and_allows_equal_burst(self):
        first = recording("S01", "diam", 96)
        first.loc[1, "timestamp_ms"] = first.loc[0, "timestamp_ms"]  # burst sharing same ms
        data = pd.concat([first, recording("S01", "diam", 64)], ignore_index=True)
        features, _ = har_pipeline.extract_windows(data)
        self.assertEqual(features.shape, (3, 20))

    def test_read_real_recording_schema_and_unit_inference(self):
        raw = pd.DataFrame({
            "timestamp": ["2026-11-25T14:16:26.000", "2026-11-25T14:16:26.023"],
            "elapsed": [0.005, 0.028],
            "ax": [0.1, 0.2], "ay": [-0.1, -0.2], "az": [-9.81, -9.80],
            "gx": [0.0, 0.0], "gy": [0.0, 0.0], "gz": [0.0, 0.0],
            "label": ["diam", "diam"],
            "session": ["20261125_141624", "20261125_141624"],
        })
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "real.csv"
            raw.to_csv(csv_path, index=False)
            loaded = har_pipeline.read_recordings(csv_path)
        self.assertEqual(loaded["subjek"].iloc[0], "S01")
        self.assertEqual(loaded["sesi"].iloc[0], "20261125_141624")
        self.assertEqual(list(loaded["timestamp_ms"]), [5, 28])
        self.assertEqual(har_pipeline.infer_accel_unit(loaded), "m/s2")


if __name__ == "__main__":
    unittest.main()
