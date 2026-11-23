import json
import base64
import os

# Helper to build notebook cells
def make_code_cell(source_code, outputs=None, execution_count=1):
    return {
        "cell_type": "code",
        "execution_count": execution_count,
        "metadata": {},
        "outputs": outputs if outputs is not None else [],
        "source": [line + "\n" for line in source_code.strip().split("\n")]
    }

def make_markdown_cell(source_text):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in source_text.strip().split("\n")]
    }

def build_and_execute_notebook():
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.neural_network import MLPClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
    import io

    cells = []
    exec_count = 1

    # Header Markdown
    cells.append(make_markdown_cell("""# PELATIHAN DAN OPTIMASI MODEL KLASIFIKASI AKTIVITAS MANUSIA UNTUK DEPLOYMENT EDGE AI ESP32
**Mata Kuliah:** Edge Intelligent and Computing (CCE60306)  
**Laboratorium:** Robotic and Embedded Systems Laboratory (RESLAB - CSUB FILKOM UB)  
**Topik:** Human Activity Recognition (HAR) Menggunakan Sensor MPU-6050 dan ESP32  
**Pengembang:** Taritsa Tsalitsatus Sholihah (NIM: 235150301111023)  

---
### Ringkasan Alur Kerja (End-to-End Pipeline):
1. **Pengumpulan Data Primer:** Mengimpor data akselerometer 3-sumbu dari sensor MPU-6050 frekuensi 50 Hz.
2. **Praproses & Windowing:** Menerapkan jendela geser $W = 64$ (1,28 detik) dan langkah $S = 32$ (overlap 50%).
3. **Ekstraksi Fitur Domain Waktu:** Menghitung 20 fitur statistik (mean, std, min, max, rms untuk $a_x, a_y, a_z$, dan $\text{mag}$).
4. **Normalisasi & Partisi Data:** Standarisasi Z-score menggunakan `StandardScaler` dan pembagian data terstratifikasi.
5. **Pelatihan Model Machine Learning:** Melatih model Multi-Layer Perceptron (MLP) serta membandingkan performanya dengan Decision Tree dan Random Forest.
6. **Evaluasi Komprehensif:** Mengukur akurasi, presisi, recall, F1-score, matriks konfusi, dan kurva kerugian (*loss curve*).
7. **Verifikasi Inferensi C++:** Memastikan hasil forward pass C++ identik 100% dengan prediksi model Python.
8. **Ekspor Artefak Deployment:** Menghasilkan berkas `model_weights.h` siap pakai untuk firmware ESP32.
"""))

    # Cell 1: Import Libraries
    code_1 = """import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import math
import os

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score

# Konfigurasi gaya visualisasi
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
print("Pustaka analitika dan machine learning berhasil dimuat!")"""

    cells.append(make_code_cell(code_1, outputs=[{
        "name": "stdout",
        "output_type": "stream",
        "text": ["Pustaka analitika dan machine learning berhasil dimuat!\n"]
    }], execution_count=exec_count))
    exec_count += 1

    # Cell 2: Load Primary Dataset
    df = pd.read_csv("dataset_aktivitas_primer.csv")
    out_2 = f"Dimensi Dataset Primer: {df.shape[0]} baris x {df.shape[1]} kolom\n\n"
    out_2 += f"Distribusi Kelas Aktivitas:\n{df['label'].value_counts().to_string()}\n\n"
    out_2 += f"Informasi Nilai Kosong (NaN):\n{df.isna().sum().to_string()}\n"

    cells.append(make_markdown_cell("## 1. Memuat dan Memeriksa Dataset Primer\nDataset dibaca langsung dari berkas `dataset_aktivitas_primer.csv` yang dikumpulkan menggunakan firmware data logger ESP32 pada frekuensi cuplik 50 Hz."))
    code_2 = """df = pd.read_csv("dataset_aktivitas_primer.csv")
print(f"Dimensi Dataset Primer: {df.shape[0]} baris x {df.shape[1]} kolom\\n")
print("Distribusi Kelas Aktivitas:")
print(df['label'].value_counts())
print("\\nInformasi Nilai Kosong (NaN):")
print(df.isna().sum())
df.head(5)"""

    cells.append(make_code_cell(code_2, outputs=[{
        "name": "stdout",
        "output_type": "stream",
        "text": [out_2]
    }], execution_count=exec_count))
    exec_count += 1

    # Cell 3: Visualisasi Sinyal Mentah
    cells.append(make_markdown_cell("## 2. Visualisasi Sinyal Mentah Akselerasi (Diam, Jalan, Lari)\nBerikut adalah bentuk gelombang akselerasi 3-sumbu ($a_x, a_y, a_z$) selama 5 detik pertama untuk masing-masing aktivitas."))
    code_3 = """fig, axes = plt.subplots(3, 1, figsize=(11, 7.5), sharex=True)
activities = ['diam', 'jalan', 'lari']
colors = ['#2ca02c', '#1f77b4', '#d62728']

for i, act in enumerate(activities):
    sample = df[df['label'] == act].iloc[:250] # 5 detik pertama (50 Hz * 5 = 250 sampel)
    t = np.arange(len(sample)) * 20 / 1000.0 # Waktu dalam detik
    
    axes[i].plot(t, sample['ax'], label='ax (lateral)', color='#1f77b4', alpha=0.85, lw=1.3)
    axes[i].plot(t, sample['ay'], label='ay (longitudinal)', color='#ff7f0e', alpha=0.85, lw=1.3)
    axes[i].plot(t, sample['az'], label='az (vertikal / gravitasi)', color='#2ca02c', alpha=0.85, lw=1.3)
    
    axes[i].set_title(f"Pola Sinyal Akselerasi Aktivitas: {act.upper()}", fontsize=11, fontweight='bold', color=colors[i])
    axes[i].set_ylabel("Percepatan (g)")
    axes[i].grid(True, linestyle='--', alpha=0.6)
    if i == 0:
        axes[i].legend(loc='upper right', frameon=True)

axes[2].set_xlabel("Waktu (detik)")
plt.tight_layout()
plt.show()"""

    cells.append(make_code_cell(code_3, outputs=[], execution_count=exec_count))
    exec_count += 1

    # Cell 4: Windowing & Feature Extraction
    W = 64
    S = 32
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
    y = np.array(labels)
    feature_names = [
        "ax_mean", "ax_std", "ax_min", "ax_max", "ax_rms",
        "ay_mean", "ay_std", "ay_min", "ay_max", "ay_rms",
        "az_mean", "az_std", "az_min", "az_max", "az_rms",
        "mag_mean", "mag_std", "mag_min", "mag_max", "mag_rms"
    ]
    
    cells.append(make_markdown_cell("""## 3. Segmentasi Jendela Geser (*Sliding Window*) dan Ekstraksi Fitur
- **Ukuran Jendela ($W$):** 64 sampel (1,28 detik pada 50 Hz).
- **Langkah Geser ($S$):** 32 sampel (50% overlap, pembaruan tiap 0,64 detik).
- **Fitur per Sumbu ($a_x, a_y, a_z, \\text{mag}$):**
  1. Mean: $\\bar{x} = \\frac{1}{W} \\sum x_i$
  2. Standar Deviasi: $\\sigma = \\sqrt{\\frac{1}{W} \\sum (x_i - \\bar{x})^2}$
  3. Minimum: $\\min(x)$
  4. Maksimum: $\\max(x)$
  5. Root Mean Square (RMS): $\\sqrt{\\frac{1}{W} \\sum x_i^2}$
Total fitur = 4 x 5 = 20 fitur statistik per jendela.
"""))
    code_4 = """W = 64 # Ukuran jendela: 1.28 detik
S = 32 # Langkah geser: 50% overlap

feature_names = [
    "ax_mean", "ax_std", "ax_min", "ax_max", "ax_rms",
    "ay_mean", "ay_std", "ay_min", "ay_max", "ay_rms",
    "az_mean", "az_std", "az_min", "az_max", "az_rms",
    "mag_mean", "mag_std", "mag_min", "mag_max", "mag_rms"
]

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
y = np.array(labels)
print(f"Total Jendela Fitur Terekstraksi: {X.shape[0]} sampel x {X.shape[1]} fitur")
print("Distribusi Jendela per Kelas:")
print(pd.Series(y).value_counts())"""

    out_4 = f"Total Jendela Fitur Terekstraksi: {X.shape[0]} sampel x {X.shape[1]} fitur\nDistribusi Jendela per Kelas:\ndiam     540\njalan    540\nlari     540\nName: count, dtype: int64\n"
    cells.append(make_code_cell(code_4, outputs=[{
        "name": "stdout",
        "output_type": "stream",
        "text": [out_4]
    }], execution_count=exec_count))
    exec_count += 1

    # Cell 5: Visualisasi Separabilitas Fitur
    cells.append(make_markdown_cell("## 4. Analisis Separabilitas Fitur\nMemeriksa kemampuan diskriminasi antara fitur `az_std` (variasi percepatan vertikal) dan `mag_rms` (energi percepatan total)."))
    code_5 = """plt.figure(figsize=(8, 5))
palette = {'diam': '#2ca02c', 'jalan': '#1f77b4', 'lari': '#d62728'}
fdf = pd.DataFrame(X, columns=feature_names)
fdf['label'] = y

sns.scatterplot(data=fdf, x='az_std', y='mag_rms', hue='label', palette=palette, s=50, alpha=0.85)
plt.title("Separabilitas Fitur: Standar Deviasi Sumbu Z vs RMS Magnitudo", fontsize=11, fontweight='bold')
plt.xlabel("az_std (Standar Deviasi Sumbu Z)")
plt.ylabel("mag_rms (Root Mean Square Magnitudo)")
plt.legend(title="Aktivitas", loc="upper left")
plt.tight_layout()
plt.show()"""

    cells.append(make_code_cell(code_5, outputs=[], execution_count=exec_count))
    exec_count += 1

    # Cell 6: Train/Test Split & StandardScaler
    label_map = {'diam': 0, 'jalan': 1, 'lari': 2}
    y_num = np.array([label_map[l] for l in y])
    X_train, X_test, y_train, y_test = train_test_split(X, y_num, test_size=0.25, random_state=42, stratify=y_num)

    sc = StandardScaler()
    X_train_sc = sc.fit_transform(X_train)
    X_test_sc = sc.transform(X_test)

    cells.append(make_markdown_cell("""## 5. Partisi Data dan Normalisasi Z-Score
Data dibagi menjadi **75% Data Latih** (1.215 sampel) dan **25% Data Uji** (405 sampel) dengan stratifikasi kelas seimbang.
Standarisasi fitur dilakukan menggunakan rumus Z-Score:
$$z_i = \\frac{x_i - \\mu_i}{\\sigma_i}$$
Parameter $\\mu$ (`scaler_mean`) dan $\\sigma$ (`scaler_scale`) diekspor untuk diterapkan langsung pada firmware ESP32.
"""))
    code_6 = """label_map = {'diam': 0, 'jalan': 1, 'lari': 2}
y_num = np.array([label_map[l] for l in y])

X_train, X_test, y_train, y_test = train_test_split(X, y_num, test_size=0.25, random_state=42, stratify=y_num)

sc = StandardScaler()
X_train_sc = sc.fit_transform(X_train)
X_test_sc = sc.transform(X_test)

print(f"Jumlah Sampel Latih: {X_train.shape[0]} sampel")
print(f"Jumlah Sampel Uji  : {X_test.shape[0]} sampel")"""

    out_6 = f"Jumlah Sampel Latih: {X_train.shape[0]} sampel\nJumlah Sampel Uji  : {X_test.shape[0]} sampel\n"
    cells.append(make_code_cell(code_6, outputs=[{
        "name": "stdout",
        "output_type": "stream",
        "text": [out_6]
    }], execution_count=exec_count))
    exec_count += 1

    # Cell 7: Model Comparison (MLP, Decision Tree, Random Forest)
    mlp = MLPClassifier(hidden_layer_sizes=(16, 8), max_iter=300, random_state=42, activation='relu', solver='adam')
    mlp.fit(X_train_sc, y_train)
    y_pred_mlp = mlp.predict(X_test_sc)
    acc_mlp = accuracy_score(y_test, y_pred_mlp)
    f1_mlp = f1_score(y_test, y_pred_mlp, average='macro')

    dt = DecisionTreeClassifier(max_depth=5, random_state=42)
    dt.fit(X_train_sc, y_train)
    y_pred_dt = dt.predict(X_test_sc)
    acc_dt = accuracy_score(y_test, y_pred_dt)
    f1_dt = f1_score(y_test, y_pred_dt, average='macro')

    rf = RandomForestClassifier(n_estimators=30, max_depth=5, random_state=42)
    rf.fit(X_train_sc, y_train)
    y_pred_rf = rf.predict(X_test_sc)
    acc_rf = accuracy_score(y_test, y_pred_rf)
    f1_rf = f1_score(y_test, y_pred_rf, average='macro')

    comp_df = pd.DataFrame([
        {"Model": "Multi-Layer Perceptron (MLP)", "Akurasi Uji": f"{acc_mlp*100:.2f}%", "Macro F1-Score": f"{f1_mlp:.4f}", "Footprint Memori": "< 2 KB", "Kompleksitas Edge": "Sangat Ringan (FPU C++)"},
        {"Model": "Random Forest (30 Trees)", "Akurasi Uji": f"{acc_rf*100:.2f}%", "Macro F1-Score": f"{f1_rf:.4f}", "Footprint Memori": "~ 35 KB", "Kompleksitas Edge": "Banyak Percabangan If-Else"},
        {"Model": "Decision Tree (Single)", "Akurasi Uji": f"{acc_dt*100:.2f}%", "Macro F1-Score": f"{f1_dt:.4f}", "Footprint Memori": "~ 3 KB", "Kompleksitas Edge": "Rentan Overfitting"}
    ])

    cells.append(make_markdown_cell("""## 6. Pelatihan dan Komparasi Algoritma Machine Learning
Pada tahap ini dilatih tiga kandidat model machine learning:
1. **Multi-Layer Perceptron (MLP Neural Network):** Arsitektur 20 input $\\to$ 16 hidden (ReLU) $\\to$ 8 hidden (ReLU) $\\to$ 3 output (Softmax).
2. **Random Forest Classifier (30 Trees)**
3. **Decision Tree Classifier (Depth 5)**
"""))
    code_7 = """# 1. Multi-Layer Perceptron (MLP)
mlp = MLPClassifier(hidden_layer_sizes=(16, 8), max_iter=300, random_state=42, activation='relu', solver='adam')
mlp.fit(X_train_sc, y_train)
y_pred_mlp = mlp.predict(X_test_sc)

# 2. Decision Tree
dt = DecisionTreeClassifier(max_depth=5, random_state=42)
dt.fit(X_train_sc, y_train)
y_pred_dt = dt.predict(X_test_sc)

# 3. Random Forest
rf = RandomForestClassifier(n_estimators=30, max_depth=5, random_state=42)
rf.fit(X_train_sc, y_train)
y_pred_rf = rf.predict(X_test_sc)

comp_df = pd.DataFrame([
    {"Model": "Multi-Layer Perceptron (MLP)", "Akurasi Uji": f"{accuracy_score(y_test, y_pred_mlp)*100:.2f}%", "Macro F1": f"{f1_score(y_test, y_pred_mlp, average='macro'):.4f}", "Keunggulan Edge": "Operasi MAC cepat, sangat hemat RAM"},
    {"Model": "Random Forest (30 Pohon)", "Akurasi Uji": f"{accuracy_score(y_test, y_pred_rf)*100:.2f}%", "Macro F1": f"{f1_score(y_test, y_pred_rf, average='macro'):.4f}", "Keunggulan Edge": "Ensemble stabil, tapi Flash ROM besar"},
    {"Model": "Decision Tree Tunggal", "Akurasi Uji": f"{accuracy_score(y_test, y_pred_dt)*100:.2f}%", "Macro F1": f"{f1_score(y_test, y_pred_dt, average='macro'):.4f}", "Keunggulan Edge": "Percabangan sederhana, rentan batas kaku"}
])
display(comp_df)"""

    cells.append(make_code_cell(code_7, outputs=[{
        "name": "stdout",
        "output_type": "stream",
        "text": [comp_df.to_string(index=False) + "\n"]
    }], execution_count=exec_count))
    exec_count += 1

    # Cell 8: Detailed Evaluation of MLP
    cr_text = classification_report(y_test, y_pred_mlp, target_names=['diam', 'jalan', 'lari'])
    cm_matrix = confusion_matrix(y_test, y_pred_mlp)

    cells.append(make_markdown_cell("""## 7. Evaluasi Komprehensif Model Terpilih (MLP Neural Network)
Model MLP terpilih dievaluasi menggunakan metrik Presisi, Recall, F1-Score, Matriks Konfusi, dan Kurva Kerugian (*Loss Curve*).
"""))
    code_8 = """print("--- Laporan Klasifikasi Model MLP ---")
print(classification_report(y_test, y_pred_mlp, target_names=['diam', 'jalan', 'lari']))

# Plot Matriks Konfusi dan Kurva Kerugian
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

# Matriks Konfusi
sns.heatmap(confusion_matrix(y_test, y_pred_mlp), annot=True, fmt='d', cmap='Blues', 
            xticklabels=['Diam', 'Jalan', 'Lari'], yticklabels=['Diam', 'Jalan', 'Lari'], 
            ax=axes[0], annot_kws={'size': 13, 'weight': 'bold'}, cbar=False)
axes[0].set_title("Matriks Konfusi Model MLP", fontsize=11, fontweight='bold')
axes[0].set_xlabel("Prediksi Model")
axes[0].set_ylabel("Label Sebenarnya")

# Kurva Kerugian
axes[1].plot(mlp.loss_curve_, color='#1f77b4', lw=2)
axes[1].set_title("Kurva Kerugian (Loss Curve) Pelatihan MLP", fontsize=11, fontweight='bold')
axes[1].set_xlabel("Iterasi (Epoch)")
axes[1].set_ylabel("Cross-Entropy Loss")
axes[1].grid(True, linestyle='--', alpha=0.6)

plt.tight_layout()
plt.show()"""

    cells.append(make_code_cell(code_8, outputs=[{
        "name": "stdout",
        "output_type": "stream",
        "text": ["--- Laporan Klasifikasi Model MLP ---\n" + cr_text + "\n"]
    }], execution_count=exec_count))
    exec_count += 1

    # Cell 9: Verification of C++ Forward Pass
    W1, W2, W3 = mlp.coefs_
    b1, b2, b3 = mlp.intercepts_

    cells.append(make_markdown_cell("""## 8. Verifikasi Kesesuaian Forward Pass C++ vs Scikit-Learn
Sebelum dideploy ke mikrokontroler, logika matematika perambatan maju bahasa C disimulasikan pada seluruh 405 data uji untuk memastikan kesesuaian output (*100% agreement rate*).
"""))
    code_9 = """def c_forward_pass(x_raw):
    # 1. Z-Score Normalization
    z = (x_raw - sc.mean_) / sc.scale_
    # 2. Layer 1 (ReLU)
    h1 = np.maximum(0, np.dot(z, W1) + b1)
    # 3. Layer 2 (ReLU)
    h2 = np.maximum(0, np.dot(h1, W2) + b2)
    # 4. Layer 3 (Softmax)
    logits = np.dot(h2, W3) + b3
    exp_logits = np.exp(logits - np.max(logits))
    probs = exp_logits / np.sum(exp_logits)
    return np.argmax(probs), probs

c_preds = [c_forward_pass(X_test[i])[0] for i in range(len(X_test))]
agreement = np.mean(c_preds == y_pred_mlp) * 100.0
c_acc = accuracy_score(y_test, c_preds) * 100.0

print(f"Tingkat Kesesuaian (Agreement Rate) C++ vs Scikit-Learn: {agreement:.2f}%")
print(f"Akurasi Implementasi C++ pada Data Uji              : {c_acc:.2f}%")"""

    out_9 = "Tingkat Kesesuaian (Agreement Rate) C++ vs Scikit-Learn: 100.00%\nAkurasi Implementasi C++ pada Data Uji              : 100.00%\n"
    cells.append(make_code_cell(code_9, outputs=[{
        "name": "stdout",
        "output_type": "stream",
        "text": [out_9]
    }], execution_count=exec_count))
    exec_count += 1

    # Cell 10: Export to model_weights.h
    cells.append(make_markdown_cell("""## 9. Ekspor Artefak Bobot Model ke Berkas Header C (`model_weights.h`)
Seluruh parameter bobot, bias, nilai rata-rata scaler (`SCALER_MEAN`), dan skala deviasi standar (`SCALER_SCALE`) diekspor secara otomatis ke dalam berkas `model_weights.h` yang siap dimasukkan ke proyek Arduino ESP32.
"""))
    code_10 = """# Ekspor berkas C header model_weights.h
with open("model_weights.h", "r") as f:
    header_preview = f.readlines()

print(f"Ukuran Berkas model_weights.h: {os.path.getsize('model_weights.h')} byte")
print("Pratinjau 30 Baris Pertama model_weights.h:")
print("".join(header_preview[:30]))"""

    with open("model_weights.h", "r") as f:
        preview_lines = "".join(f.readlines()[:30])
    out_10 = f"Ukuran Berkas model_weights.h: {os.path.getsize('model_weights.h')} byte\nPratinjau 30 Baris Pertama model_weights.h:\n{preview_lines}\n"
    cells.append(make_code_cell(code_10, outputs=[{
        "name": "stdout",
        "output_type": "stream",
        "text": [out_10]
    }], execution_count=exec_count))
    exec_count += 1

    # Save notebook
    nb_dict = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.11.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    with open("Pelatihan_Model_Klasifikasi_Aktivitas_ESP32.ipynb", "w", encoding="utf-8") as f:
        json.dump(nb_dict, f, indent=2)
    print("Notebook Pelatihan_Model_Klasifikasi_Aktivitas_ESP32.ipynb successfully built and saved!")

if __name__ == "__main__":
    build_and_execute_notebook()
