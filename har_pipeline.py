"""Feature extraction and leak-free evaluation for ESP32 HAR."""

import numpy as np
import pandas as pd
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

CLASSES = ("diam", "jalan", "lari")
CLASS_IDS = tuple(range(len(CLASSES)))
LABEL_IDS = dict(zip(CLASSES, CLASS_IDS))
ACCELERATION = ["ax", "ay", "az"]
RECORDING_COLUMNS = ["subjek", "sesi", "posisi", "label"]
WINDOW_SIZE = 64
STEP_SIZE = 32


def _normalize_schema(data):
    """Map real-recording columns (session/elapsed) onto the pipeline schema."""
    normalized = data.copy()
    if "sesi" not in normalized.columns and "session" in normalized.columns:
        normalized["sesi"] = normalized["session"]
    if "timestamp_ms" not in normalized.columns and "elapsed" in normalized.columns:
        elapsed_sec = pd.to_numeric(normalized["elapsed"], errors="raise")
        normalized["timestamp_ms"] = np.round(elapsed_sec * 1000.0)
    if "subjek" not in normalized.columns and "sesi" in normalized.columns:
        normalized["subjek"] = "S01"
    if "posisi" not in normalized.columns and "sesi" in normalized.columns:
        normalized["posisi"] = "genggam"
    return normalized


def read_recordings(path):
    """Load and validate either standard or real-device HAR CSV recordings."""
    data = pd.read_csv(path, dtype={"subjek": "string", "sesi": "string", "session": "string"})
    data = _normalize_schema(data)
    required = RECORDING_COLUMNS + ["timestamp_ms"] + ACCELERATION
    missing_columns = sorted(set(required) - set(data.columns))
    if missing_columns:
        raise ValueError(f"Kolom wajib tidak ditemukan: {', '.join(missing_columns)}")
    if data[required].isna().any().any():
        raise ValueError("Kolom wajib berisi nilai kosong.")
    for name in RECORDING_COLUMNS:
        data[name] = data[name].astype("string").str.strip()
    data["subjek"] = data["subjek"].str.upper()
    data["label"] = data["label"].str.lower()
    if (data[RECORDING_COLUMNS] == "").any().any():
        raise ValueError("Identitas rekaman atau label kosong.")
    if not data["label"].isin(CLASSES).all():
        raise ValueError("Label harus berupa diam, jalan, atau lari.")
    numeric_columns = ["timestamp_ms", *ACCELERATION]
    data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(data[numeric_columns].to_numpy()).all():
        raise ValueError("Waktu dan akselerasi harus berisi angka berhingga.")
    return data


def infer_accel_unit(data):
    """Infer whether acceleration readings are in 'm/s2' (~9.8) or 'g' (~1.0)."""
    magnitudes = np.linalg.norm(data[ACCELERATION].to_numpy(dtype=float), axis=1)
    return "m/s2" if float(np.median(magnitudes)) >= 4.5 else "g"


def extract_windows(data):
    """Use acquisition order within each recording; split when its clock resets."""
    features, labels = [], []
    for (*_, activity), group in data.groupby(RECORDING_COLUMNS, sort=False):
        timestamps = group["timestamp_ms"].to_numpy(dtype=float)
        values = group[ACCELERATION].to_numpy(dtype=float)
        # Split only on backward clock resets; serial bursts can share the same millisecond.
        resets = np.flatnonzero(np.diff(timestamps) < 0) + 1
        for segment in np.split(values, resets):
            for start in range(0, len(segment) - WINDOW_SIZE + 1, STEP_SIZE):
                window = segment[start : start + WINDOW_SIZE]
                channels = np.column_stack((window, np.linalg.norm(window, axis=1)))
                rms = np.sqrt(np.mean(channels**2, axis=0))
                statistics = (channels.mean(0), channels.std(0),
                              channels.min(0), channels.max(0), rms)
                features.append(np.column_stack(statistics).ravel())
                labels.append(LABEL_IDS[activity])
    return np.asarray(features).reshape(-1, 20), np.asarray(labels, dtype=int)


def _yield_group_folds(data, group_labels, label_fn):
    for train_rows, test_rows in LeaveOneGroupOut().split(data, groups=group_labels):
        test = data.iloc[test_rows]
        fold_name = label_fn(test)
        X_train, y_train = extract_windows(data.iloc[train_rows])
        X_test, y_test = extract_windows(test)
        if set(y_train) != set(CLASS_IDS):
            raise ValueError(f"Fold {fold_name}: data latih harus memiliki jendela dari ketiga aktivitas.")
        if set(y_test) != set(CLASS_IDS) or not len(y_test):
            raise ValueError(f"Fold {fold_name}: data uji harus memiliki jendela dari ketiga aktivitas.")
        yield fold_name, X_train, y_train, X_test, y_test


def subject_folds(data):
    """Hold out one whole subject before building overlapping windows."""
    subjects = data["subjek"]
    if subjects.nunique() < 2:
        raise ValueError("Evaluasi antar-subjek membutuhkan rekaman dari minimal dua subjek berbeda.")
    yield from _yield_group_folds(data, subjects, lambda test: test["subjek"].iloc[0])


def session_folds(data):
    """Pair the k-th session of each activity into held-out folds for single-subject data."""
    session_to_fold = {}
    for _, group in data.groupby("label", sort=False):
        for idx, sess in enumerate(group["sesi"].drop_duplicates()):
            session_to_fold[(group["label"].iloc[0], sess)] = idx
    fold_ids = pd.Series(
        [session_to_fold[(lbl, ses)] for lbl, ses in zip(data["label"], data["sesi"])],
        index=data.index,
    )
    if fold_ids.nunique() < 2:
        raise ValueError("Evaluasi antar-sesi membutuhkan minimal dua sesi per aktivitas.")
    yield from _yield_group_folds(
        data,
        fold_ids,
        lambda test: f"Sesi-{int(fold_ids.loc[test.index].iloc[0]) + 1}",
    )


def evaluation_folds(data):
    """Choose subject-wise CV for multi-subject data, or session-wise CV for single-subject."""
    if data["subjek"].nunique() >= 2:
        yield from subject_folds(data)
    else:
        yield from session_folds(data)


def make_mlp():
    return make_pipeline(
        StandardScaler(),
        MLPClassifier(hidden_layer_sizes=(16, 8), max_iter=300, random_state=42,
                      activation="relu", solver="adam"),
    )


def evaluate_folds(folds, make_model=make_mlp):
    scores, truths, predictions = [], [], []
    for subject, X_train, y_train, X_test, y_test in folds:
        model = make_model().fit(X_train, y_train)
        predicted = model.predict(X_test)
        scores.append((subject, len(y_train), len(y_test), np.mean(predicted == y_test)))
        truths.append(y_test)
        predictions.append(predicted)
    return scores, np.concatenate(truths), np.concatenate(predictions)
