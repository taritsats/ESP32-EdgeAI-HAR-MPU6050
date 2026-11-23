import unittest
from unittest.mock import patch

import pandas as pd

import har_pipeline


def recording(subject, label, count):
    return pd.DataFrame({
        "subjek": subject, "sesi": "1", "posisi": "genggam", "label": label,
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

    def test_window_stays_inside_timestamp_reset(self):
        data = pd.concat([recording("S01", "diam", 96),
                          recording("S01", "diam", 64)], ignore_index=True)
        features, _ = har_pipeline.extract_windows(data)
        self.assertEqual(features.shape, (3, 20))


if __name__ == "__main__":
    unittest.main()
