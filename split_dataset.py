import os
import pandas as pd
import numpy as np

# Folder target
TARGET_DIRS = [
    r"E:\SMT 7\Edge Intelligent and Computing\ESP32-EdgeAI-HAR-MPU6050",
    r"E:\SMT 7\Edge Intelligent and Computing\TUGAS BESAR"
]

source_csv = os.path.join(TARGET_DIRS[0], "dataset_aktivitas_primer.csv")
df = pd.read_csv(source_csv)

print("=== MEMPROSES PEMISAHAN DATASET (TRAIN & TEST) ===")
print(f"Total baris data awal: {len(df):,} baris")

# Rasio pemisahan: 80% Train (48 detik pertama), 20% Test (12 detik terakhir) per sesi
# Pendekatan Continuous Temporal Block Split mencegah data leakage autokorelasi 50 Hz
TRAIN_RATIO = 0.80

train_rows = []
test_rows = []

# Group by subjek, sesi, posisi, label
grouped = df.groupby(["subjek", "sesi", "posisi", "label"], sort=False)

for (subj, sesi, pos, act), group in grouped:
    n = len(group)
    n_train = int(n * TRAIN_RATIO)  # 2400 baris (48 detik)
    
    # 80% awal untuk train
    train_part = group.iloc[:n_train].copy()
    # 20% akhir untuk test
    test_part = group.iloc[n_train:].copy()
    
    train_rows.append(train_part)
    test_rows.append(test_part)

df_train = pd.concat(train_rows, ignore_index=True)
df_test = pd.concat(test_rows, ignore_index=True)

print(f"\n--- HASIL PEMISAHAN ---")
print(f"Data Train : {len(df_train):,} baris ({len(df_train)/len(df)*100:.1f}%)")
print(f"Data Test  : {len(df_test):,} baris ({len(df_test)/len(df)*100:.1f}%)")

print("\nDistribusi Label Data Train:")
print(df_train["label"].value_counts())

print("\nDistribusi Label Data Test:")
print(df_test["label"].value_counts())

print("\nDistribusi Subjek & Sesi pada Data Train:")
print(df_train.groupby(["subjek", "sesi", "label"]).size().unstack())

print("\nDistribusi Subjek & Sesi pada Data Test:")
print(df_test.groupby(["subjek", "sesi", "label"]).size().unstack())

# Simpan ke masing-masing folder
for target_dir in TARGET_DIRS:
    if not os.path.exists(target_dir):
        continue
    
    train_csv = os.path.join(target_dir, "dataset_train.csv")
    test_csv = os.path.join(target_dir, "dataset_test.csv")
    train_xlsx = os.path.join(target_dir, "dataset_train.xlsx")
    test_xlsx = os.path.join(target_dir, "dataset_test.xlsx")
    
    print(f"\nMenyimpan berkas di: {target_dir}")
    df_train.to_csv(train_csv, index=False)
    df_test.to_csv(test_csv, index=False)
    print("  -> CSV tersimpan: dataset_train.csv & dataset_test.csv")
    
    df_train.to_excel(train_xlsx, index=False, engine="openpyxl")
    df_test.to_excel(test_xlsx, index=False, engine="openpyxl")
    print("  -> XLSX tersimpan: dataset_train.xlsx & dataset_test.xlsx")

print("\nSemua berkas train dan test berhasil dibuat dan disimpan!")
