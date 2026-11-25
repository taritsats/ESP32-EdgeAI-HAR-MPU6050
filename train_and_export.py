import argparse
import hashlib
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from har_pipeline import (
    CLASSES, CLASS_IDS, evaluation_folds, evaluate_folds, extract_windows,
    infer_accel_unit, make_mlp, read_recordings,
)

ROOT = Path(__file__).resolve().parent
REAL_DATASET = ROOT / "dataset_aktivitas.csv"
DEMO_DATASET = ROOT / "dataset_aktivitas_primer.csv"
DEFAULT_DATASET = REAL_DATASET if REAL_DATASET.exists() else DEMO_DATASET


def save_figures(model, truth, predictions, images):
    images.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(model["mlpclassifier"].loss_curve_, color="#1f77b4", lw=2)
    ax.set(title="Kurva Loss Pelatihan Model Ekspor", xlabel="Epoch",
           ylabel="Cross-entropy loss")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    fig.savefig(images / "gambar3_kurva_loss_pelatihan.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    matrix = confusion_matrix(truth, predictions, labels=CLASS_IDS)
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=CLASSES, yticklabels=CLASSES, ax=ax)
    ax.set(title="Matriks Konfusi MLP (Validasi Bebas Kebocoran)",
           xlabel="Prediksi model", ylabel="Label sebenarnya")
    fig.tight_layout()
    fig.savefig(images / "gambar4_matriks_konfusi_mlp.png", dpi=300)
    plt.close(fig)


def fmt_arr_1d(arr, name):
    res = f"const float {name}[{len(arr)}] = {{\n  "
    res += ", ".join([f"{v:.6f}f" for v in arr])
    res += "\n};\n\n"
    return res

def fmt_arr_2d(arr, name):
    r, c = arr.shape
    res = f"const float {name}[{r}][{c}] = {{\n"
    for i in range(r):
        res += "  {" + ", ".join([f"{v:.6f}f" for v in arr[i]]) + "}"
        if i < r - 1:
            res += ",\n"
        else:
            res += "\n"
    res += "};\n\n"
    return res

def export_model(model, header_path, dataset_sha256, accel_unit):
    sc = model["standardscaler"]
    mlp = model["mlpclassifier"]
    W1, W2, W3 = mlp.coefs_
    b1, b2, b3 = mlp.intercepts_
    lines = [
        "/*",
        " * ======================================================================================",
        " * MODEL PARAMETERS & INFERENCE ENGINE FOR ESP32",
        " * Multi-Layer Perceptron (MLP: 20 Input -> 16 Hidden1 -> 8 Hidden2 -> 3 Output)",
        " * Model fitted on all subjects after evaluation.",
        f" * Training CSV SHA-256: {dataset_sha256}",
        " * ======================================================================================",
        " */",
        "",
        "#ifndef MODEL_WEIGHTS_H",
        "#define MODEL_WEIGHTS_H",
        "",
        "#include <math.h>",
        "",
        "#define NUM_FEATURES 20",
        "#define NUM_CLASSES 3",
        "#define H1_SIZE 16",
        "#define H2_SIZE 8",
        f"#define MODEL_ACCEL_G_TO_UNIT {9.80665 if accel_unit == 'm/s2' else 1.0}f",
        "",
        "// Parameter Normalisasi Fitur (StandardScaler: mu & sigma)",
        fmt_arr_1d(sc.mean_, "SCALER_MEAN"),
        fmt_arr_1d(sc.scale_, "SCALER_SCALE"),
        fmt_arr_2d(W1, "W1"),
        fmt_arr_1d(b1, "B1"),
        fmt_arr_2d(W2, "W2"),
        fmt_arr_1d(b2, "B2"),
        fmt_arr_2d(W3, "W3"),
        fmt_arr_1d(b3, "B3"),
        "",
        '// Label Aktivitas',
        'const char* const CLASS_NAMES[3] = {"DIAM", "JALAN", "LARI"};',
        "",
        "// Fungsi Inferensi Ringan MLP pada Edge Device",
        "inline int predictActivity(const float features[20], float probs[3]) {",
        "    // 1. Standarisasi Fitur (Z-score Normalization)",
        "    float z[20];",
        "    for (int i = 0; i < 20; i++) {",
        "        z[i] = (features[i] - SCALER_MEAN[i]) / SCALER_SCALE[i];",
        "    }",
        "",
        "    // 2. Hidden Layer 1 (20 -> 16, ReLU)",
        "    float h1[16];",
        "    for (int j = 0; j < 16; j++) {",
        "        float sum = B1[j];",
        "        for (int i = 0; i < 20; i++) {",
        "            sum += z[i] * W1[i][j];",
        "        }",
        "        h1[j] = (sum > 0.0f) ? sum : 0.0f; // ReLU",
        "    }",
        "",
        "    // 3. Hidden Layer 2 (16 -> 8, ReLU)",
        "    float h2[8];",
        "    for (int j = 0; j < 8; j++) {",
        "        float sum = B2[j];",
        "        for (int i = 0; i < 16; i++) {",
        "            sum += h1[i] * W2[i][j];",
        "        }",
        "        h2[j] = (sum > 0.0f) ? sum : 0.0f; // ReLU",
        "    }",
        "",
        "    // 4. Output Layer (8 -> 3, Softmax)",
        "    float logits[3];",
        "    float max_logit = -1e9f;",
        "    for (int j = 0; j < 3; j++) {",
        "        float sum = B3[j];",
        "        for (int i = 0; i < 8; i++) {",
        "            sum += h2[i] * W3[i][j];",
        "        }",
        "        logits[j] = sum;",
        "        if (sum > max_logit) max_logit = sum;",
        "    }",
        "",
        "    // Softmax Stabil Numerik",
        "    float exp_sum = 0.0f;",
        "    for (int j = 0; j < 3; j++) {",
        "        probs[j] = expf(logits[j] - max_logit);",
        "        exp_sum += probs[j];",
        "    }",
        "",
        "    int best_class = 0;",
        "    float max_p = 0.0f;",
        "    for (int j = 0; j < 3; j++) {",
        "        probs[j] /= exp_sum;",
        "        if (probs[j] > max_p) {",
        "            max_p = probs[j];",
        "            best_class = j;",
        "        }",
        "    }",
        "    return best_class;",
        "}",
        "",
        "#endif // MODEL_WEIGHTS_H",
        ""
    ]


    header_path.parent.mkdir(parents=True, exist_ok=True)
    header_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description="Evaluasi HAR bebas kebocoran dan ekspor model ESP32.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--accel-unit", choices=("g", "m/s2"),
                        help="Satuan ax, ay, az pada CSV. Default: terdeteksi otomatis dari magnitudo.")
    parser.add_argument("--output-dir", type=Path,
                        help="Default: repositori untuk dataset utama/demo, data_local/training untuk CSV lain.")
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    is_repo_dataset = dataset in (REAL_DATASET, DEMO_DATASET)
    is_demo = dataset == DEMO_DATASET
    output = (args.output_dir or (ROOT if is_repo_dataset else ROOT / "data_local" / "training")).resolve()
    header_dir = output / "ESP32_Edge_Inference_MPU6050" if output == ROOT else output
    header_path = header_dir / "model_weights.h"

    csv_bytes = dataset.read_bytes()
    data = read_recordings(BytesIO(csv_bytes))
    accel_unit = args.accel_unit or infer_accel_unit(data)
    scores, truth, predictions = evaluate_folds(evaluation_folds(data))
    tag = " (demo sintetis)" if is_demo else (" (data primer asli)" if dataset == REAL_DATASET else "")
    print(f"Dataset: {dataset.name}{tag}")
    print(f"Satuan akselerasi pada CSV: {accel_unit}")
    for fold, (fold_name, train_count, test_count, accuracy) in enumerate(scores, 1):
        print(f"Fold {fold} ({fold_name}): latih={train_count}, uji={test_count}, akurasi={accuracy:.2%}")
    print(f"Akurasi gabungan ({len(truth)} jendela): {accuracy_score(truth, predictions):.2%}")
    print(classification_report(truth, predictions, labels=CLASS_IDS,
                                target_names=CLASSES, zero_division=0))

    features, labels = extract_windows(data)
    model = make_mlp().fit(features, labels)
    save_figures(model, truth, predictions, output / "images")
    export_model(model, header_path, hashlib.sha256(csv_bytes).hexdigest(), accel_unit)
    print(f"Bobot dari seluruh rekaman diekspor ke {header_path}")


if __name__ == "__main__":
    main()
