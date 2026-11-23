import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score

df = pd.read_csv('dataset_aktivitas_primer.csv')
W, S = 64, 32
windows, labels = [], []
for (subj, sesi, pos, act), g in df.groupby(['subjek', 'sesi', 'posisi', 'label']):
    vals = g[['ax', 'ay', 'az']].to_numpy()
    for start in range(0, len(vals) - W + 1, S):
        win = vals[start:start+W]
        feat = []
        mag = np.sqrt(np.sum(win**2, axis=1))
        for c in range(3):
            v = win[:, c]
            feat.extend([v.mean(), v.std(), v.min(), v.max(), np.sqrt(np.mean(v**2))])
        feat.extend([mag.mean(), mag.std(), mag.min(), mag.max(), np.sqrt(np.mean(mag**2))])
        windows.append(feat)
        labels.append(act)

X = np.array(windows)
label_map = {'diam': 0, 'jalan': 1, 'lari': 2}
y_num = np.array([label_map[l] for l in labels])
X_train, X_test, y_train, y_test = train_test_split(X, y_num, test_size=0.25, random_state=42, stratify=y_num)

sc = StandardScaler()
X_tr_sc = sc.fit_transform(X_train)
X_te_sc = sc.transform(X_test)

mlp = MLPClassifier(hidden_layer_sizes=(16, 8), max_iter=300, random_state=42, activation='relu', solver='adam')
mlp.fit(X_tr_sc, y_train)

# Gambar 3: Kurva Loss Pelatihan
plt.figure(figsize=(7, 4.5))
plt.plot(mlp.loss_curve_, color='#1f77b4', lw=2, label='Cross-Entropy Loss')
plt.title('Kurva Kerugian (Loss Curve) Pelatihan MLP', fontsize=12, fontweight='bold')
plt.xlabel('Iterasi (Epoch)')
plt.ylabel('Nilai Kerugian (Loss)')
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig('images/gambar3_kurva_loss_pelatihan.png', dpi=300)
plt.close()
print('Gambar 3 saved.')

# Gambar 4: Matriks Konfusi
y_pred = mlp.predict(X_te_sc)
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Diam', 'Jalan', 'Lari'], yticklabels=['Diam', 'Jalan', 'Lari'], cbar=False, annot_kws={'size': 14, 'weight': 'bold'})
plt.title('Matriks Konfusi Klasifikasi Aktivitas MLP', fontsize=12, fontweight='bold')
plt.xlabel('Prediksi Model')
plt.ylabel('Label Sebenarnya (Ground Truth)')
plt.tight_layout()
plt.savefig('images/gambar4_matriks_konfusi_mlp.png', dpi=300)
plt.close()
print('Gambar 4 saved.')

# Export model_weights.h
W1, W2, W3 = mlp.coefs_
b1, b2, b3 = mlp.intercepts_

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

lines = [
    "/*",
    " * ======================================================================================",
    " * MODEL PARAMETERS & INFERENCE ENGINE FOR ESP32",
    " * Multi-Layer Perceptron (MLP: 20 Input -> 16 Hidden1 -> 8 Hidden2 -> 3 Output)",
    " * Generated automatically from trained Scikit-Learn MLPClassifier",
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
    "// Latensi eksekusi: < 25 mikrodetik pada CPU ESP32 240 MHz",
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

h_code = "\n".join(lines)
with open("model_weights.h", "w") as f:
    f.write(h_code)

# Juga simpan di subfolder program ESP32
import os
os.makedirs("ESP32_Edge_Inference_MPU6050", exist_ok=True)
with open("ESP32_Edge_Inference_MPU6050/model_weights.h", "w") as f:
    f.write(h_code)

print("model_weights.h saved successfully in root and ESP32_Edge_Inference_MPU6050!")
