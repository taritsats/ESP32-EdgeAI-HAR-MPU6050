import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "Pelatihan_Model_Klasifikasi_Aktivitas_ESP32.ipynb"


def markdown(source):
    return {"cell_type": "markdown", "metadata": {},
            "source": source.strip().splitlines(keepends=True)}


def code(source):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": source.strip().splitlines(keepends=True)}


def build_notebook():
    cells = [
        markdown("""
# Pelatihan Klasifikasi Aktivitas dengan ESP32

Notebook ini mengevaluasi model klasifikasi diam, jalan, dan lari. File contoh
`dataset_aktivitas_primer.csv` berisi sinyal sintetis dari
`generate_handheld_dataset.py`. Untuk menilai kinerja pada rekaman nyata, ubah
`DATASET` ke CSV lokal dan gunakan ID yang konsisten untuk setiap peserta.
"""),
        code("""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.tree import DecisionTreeClassifier

from har_pipeline import CLASSES, CLASS_IDS, evaluate_folds, make_mlp, read_recordings, subject_folds

DATASET = Path("dataset_aktivitas_primer.csv")
data = read_recordings(DATASET)
print(f"{len(data):,} baris, {data['subjek'].nunique()} subjek")
display(data["label"].value_counts().reindex(CLASSES).rename("Sampel"))
"""),
        markdown("""
## Pembagian subjek dan ekstraksi fitur

Tiap fold menahan seluruh rekaman satu subjek. Jendela dibentuk secara terpisah
di set latih dan uji dengan panjang 64 sampel dan langkah 32. Rata-rata,
simpangan baku, minimum, maksimum, dan RMS dihitung untuk setiap sumbu
akselerometer dan magnitudo. Pipeline MLP melakukan fit StandardScaler pada
set latih di setiap fold.
"""),
        code("""
folds = list(subject_folds(data))
models = {
    "MLP": make_mlp,
    "Decision tree": lambda: DecisionTreeClassifier(max_depth=5, random_state=42),
    "Random forest": lambda: RandomForestClassifier(n_estimators=30, max_depth=5, random_state=42),
}
results = {name: evaluate_folds(folds, build) for name, build in models.items()}
display(pd.DataFrame([
    {
        "Model": name,
        "Akurasi": accuracy_score(truth, predicted),
        "Macro F1": f1_score(truth, predicted, labels=CLASS_IDS, average="macro", zero_division=0),
    }
    for name, (_, truth, predicted) in results.items()
]).set_index("Model"))
"""),
        markdown("""
## Evaluasi MLP

Prediksi di bawah berasal dari fold yang menahan subjek bersangkutan. Ketiga
arsitektur memakai fold yang sama sebagai perbandingan eksploratif. Jika
hasil ini dipakai untuk memilih model, gunakan rekaman terpisah dari subjek
baru untuk pengujian akhir.
"""),
        code("""
scores, truth, predicted = results["MLP"]
fold_scores = pd.DataFrame(
    [score[1:] for score in scores], columns=["Jendela latih", "Jendela uji", "Akurasi"]
)
fold_scores.index = pd.RangeIndex(1, len(fold_scores) + 1, name="Fold")
display(fold_scores)
print(classification_report(truth, predicted, labels=CLASS_IDS,
                            target_names=CLASSES, zero_division=0))
ax = sns.heatmap(confusion_matrix(truth, predicted, labels=CLASS_IDS),
                 annot=True, fmt="d", cmap="Blues", cbar=False,
                 xticklabels=CLASSES, yticklabels=CLASSES)
ax.set(xlabel="Prediksi", ylabel="Label sebenarnya", title="Matriks Konfusi MLP per Subjek")
plt.show()
"""),
        markdown("""
## Ekspor model firmware

Jalankan `python train_and_export.py` untuk artefak demo atau
`python train_and_export.py --dataset data_local/rekaman_aktivitas.csv` untuk
rekaman lokal. Setelah evaluasi, skrip melatih ulang MLP pada seluruh input
dan mengekspor scaler, bobot, bias, dan fungsi inferensi ke `model_weights.h`.
Artefak dari CSV lokal tersimpan di `data_local/training/` secara bawaan.
Metrik validasi berasal dari model tiap fold.
"""),
    ]
    document = {
        "cells": cells,
        "metadata": {"kernelspec": {
            "display_name": "Python 3", "language": "python", "name": "python3",
        }},
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    NOTEBOOK.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_notebook()
