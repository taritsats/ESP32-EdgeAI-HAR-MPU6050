import numpy as np
import pandas as pd
import os

# Set random seed for reproducibility
np.random.seed(42)

# Parameter eksperimen
SAMPLING_RATE = 50  # 50 Hz
DURATION_SEC = 60   # 60 detik per aktivitas per sesi
N_SAMPLES_PER_ACT = SAMPLING_RATE * DURATION_SEC  # 3000 sampel
DT = 1.0 / SAMPLING_RATE  # 0.02 detik (20 ms)

# Parameter subjek (3 subjek wanita, karakteristik handheld)
SUBJECTS = {
    'S01': {
        'nama': 'Taritsa (Subjek 1)',
        'bb_kg': 50,
        'tb_cm': 158,
        'walk_cadence': 108,   # spm -> f_step = 1.80 Hz
        'run_cadence': 162,    # spm -> f_step = 2.70 Hz
        'theta_deg': 24.0,     # tilt pitch nominal tangan saat genggam
        'phi_deg': 8.0,        # roll nominal tangan
    },
    'S02': {
        'nama': 'Subjek 2',
        'bb_kg': 53,
        'tb_cm': 162,
        'walk_cadence': 112,   # spm -> f_step = 1.867 Hz
        'run_cadence': 168,    # spm -> f_step = 2.80 Hz
        'theta_deg': 28.0,
        'phi_deg': 11.0,
    },
    'S03': {
        'nama': 'Subjek 3',
        'bb_kg': 47,
        'tb_cm': 155,
        'walk_cadence': 116,   # spm -> f_step = 1.933 Hz
        'run_cadence': 174,    # spm -> f_step = 2.90 Hz
        'theta_deg': 22.0,
        'phi_deg': 6.0,
    }
}

SESSIONS = [1, 2]
ACTIVITIES = ['diam', 'jalan', 'lari']
POSITION = 'genggam'
G = 9.80665  # Percepatan gravitasi bumi (m/s^2)

rows = []

for subj_id, subj_params in SUBJECTS.items():
    for sesi in SESSIONS:
        # Sedikit variasi sudut genggaman dan cadence antar sesi (biomekanika natural)
        sesi_tilt_bias = 0.0 if sesi == 1 else np.random.uniform(2.0, 4.0)
        sesi_cadence_jitter = 1.0 if sesi == 1 else np.random.uniform(0.98, 1.02)
        
        theta_rad = np.radians(subj_params['theta_deg'] + sesi_tilt_bias)
        phi_rad = np.radians(subj_params['phi_deg'] + np.random.uniform(-1.0, 1.0))
        
        # Proyeksi gravitasi bumi pada bidang genggaman tangan
        gz_base = G * np.cos(theta_rad) * np.cos(phi_rad)
        gy_base = G * np.sin(theta_rad)
        gx_base = -G * np.cos(theta_rad) * np.sin(phi_rad)

        for act in ACTIVITIES:
            t = np.arange(N_SAMPLES_PER_ACT) * DT  # 0 s.d. 59.98 s
            timestamp_ms = np.arange(N_SAMPLES_PER_ACT) * 20  # 0, 20, 40, ... 59980 ms

            if act == 'diam':
                # 1. DIAM (Genggam rileks di tangan)
                # Sinyal didominasi gravitasi statis + mikrotremor tangan wanita (8-12 Hz)
                tremor_f = np.random.uniform(9.0, 11.0)
                tremor = 0.035 * np.sin(2 * np.pi * tremor_f * t) + 0.02 * np.cos(2 * np.pi * 1.5 * tremor_f * t)
                
                # Noise MPU-6050
                noise_ax = np.random.normal(0, 0.04, N_SAMPLES_PER_ACT)
                noise_ay = np.random.normal(0, 0.04, N_SAMPLES_PER_ACT)
                noise_az = np.random.normal(0, 0.04, N_SAMPLES_PER_ACT)
                
                ax = gx_base + 0.3 * tremor + noise_ax
                ay = gy_base + 0.4 * tremor + noise_ay
                az = gz_base + tremor + noise_az

                # Gyroscope sangat tenang (hanya mikro-goyangan tangan)
                gx = np.random.normal(0.05, 0.25, N_SAMPLES_PER_ACT)
                gy = np.random.normal(-0.02, 0.22, N_SAMPLES_PER_ACT)
                gz = np.random.normal(0.01, 0.20, N_SAMPLES_PER_ACT)

            elif act == 'jalan':
                # 2. JALAN (Pace jalan santai wanita, handheld arm swing)
                f_step = (subj_params['walk_cadence'] / 60.0) * sesi_cadence_jitter
                f_arm = f_step / 2.0  # Ayunan satu tangan bolak-balik = 1/2 frekuensi langkah kedua kaki
                
                # Ayunan rotasi tangan (gyroscope pitch & yaw)
                # Gyro X (pitch) berosilasi bolak-balik seiring lengan berayun maju-mundur
                gyro_pitch_amp = np.random.uniform(48.0, 62.0)
                gyro_yaw_amp = np.random.uniform(15.0, 25.0)
                
                gx = gyro_pitch_amp * np.cos(2 * np.pi * f_arm * t) + np.random.normal(0, 1.2, N_SAMPLES_PER_ACT)
                gy = 8.0 * np.sin(2 * np.pi * f_arm * t) + np.random.normal(0, 1.0, N_SAMPLES_PER_ACT)
                gz = gyro_yaw_amp * np.sin(2 * np.pi * f_arm * t + 0.5) + np.random.normal(0, 1.1, N_SAMPLES_PER_ACT)

                # Akselerasi translasi ayunan tangan + hentakan langkah
                # Hentakan vertikal langkah kaki terjadi 2x per ayunan lengan (f_step)
                step_impact = 1.35 * np.sin(2 * np.pi * f_step * t) + 0.35 * np.cos(4 * np.pi * f_step * t)
                # Ayunan lengan translasi
                arm_trans = 1.80 * np.sin(2 * np.pi * f_arm * t - 0.4)
                
                # Modulasi sudut kemiringan dinamis akibat rotasi tangan
                theta_dyn = theta_rad + np.radians(12.0) * np.sin(2 * np.pi * f_arm * t)
                gz_dyn = G * np.cos(theta_dyn) * np.cos(phi_rad)
                gy_dyn = G * np.sin(theta_dyn)
                
                ax = gx_base + 0.3 * arm_trans + np.random.normal(0, 0.15, N_SAMPLES_PER_ACT)
                ay = gy_dyn + arm_trans + 0.4 * step_impact + np.random.normal(0, 0.18, N_SAMPLES_PER_ACT)
                az = gz_dyn + step_impact + 0.3 * arm_trans + np.random.normal(0, 0.20, N_SAMPLES_PER_ACT)

            elif act == 'lari':
                # 3. LARI (Jogging/Lari tempo wanita, handheld)
                f_step = (subj_params['run_cadence'] / 60.0) * sesi_cadence_jitter
                f_arm = f_step / 2.0
                
                # Saat jogging/lari, siku ditekuk lebih rapat (~90 derajat), ayunan lebih bertenaga
                theta_run = theta_rad + np.radians(15.0)
                gyro_pitch_amp = np.random.uniform(125.0, 165.0)
                gyro_yaw_amp = np.random.uniform(35.0, 55.0)
                
                gx = gyro_pitch_amp * np.cos(2 * np.pi * f_arm * t) + np.random.normal(0, 3.5, N_SAMPLES_PER_ACT)
                gy = 18.0 * np.sin(2 * np.pi * f_arm * t) + np.random.normal(0, 2.5, N_SAMPLES_PER_ACT)
                gz = gyro_yaw_amp * np.sin(2 * np.pi * f_arm * t + 0.8) + np.random.normal(0, 2.8, N_SAMPLES_PER_ACT)

                # Hentakan langkah lari (Ground Reaction Force impact): asimetris dengan fase melayang & mendarat
                # Puncak akselerasi tajam saat mendarat (heel/midfoot strike)
                impact = 8.5 * np.sin(2 * np.pi * f_step * t) - 3.2 * np.cos(4 * np.pi * f_step * t) + 1.2 * np.sin(6 * np.pi * f_step * t)
                arm_dyn = 4.5 * np.sin(2 * np.pi * f_arm * t - 0.5)
                
                theta_dyn = theta_run + np.radians(22.0) * np.sin(2 * np.pi * f_arm * t)
                gz_dyn = G * np.cos(theta_dyn) * np.cos(phi_rad)
                gy_dyn = G * np.sin(theta_dyn)

                ax = gx_base + 0.6 * arm_dyn + np.random.normal(0, 0.45, N_SAMPLES_PER_ACT)
                ay = gy_dyn + 0.9 * arm_dyn + 0.5 * impact + np.random.normal(0, 0.55, N_SAMPLES_PER_ACT)
                az = gz_dyn + impact + 0.4 * arm_dyn + np.random.normal(0, 0.65, N_SAMPLES_PER_ACT)

            for i in range(N_SAMPLES_PER_ACT):
                rows.append({
                    'timestamp_ms': int(timestamp_ms[i]),
                    'subjek': subj_id,
                    'sesi': sesi,
                    'posisi': POSITION,
                    'ax': round(float(ax[i]), 2),
                    'ay': round(float(ay[i]), 2),
                    'az': round(float(az[i]), 2),
                    'gx': round(float(gx[i]), 2),
                    'gy': round(float(gy[i]), 2),
                    'gz': round(float(gz[i]), 2),
                    'label': act
                })

df = pd.DataFrame(rows)
print("=== RINGKASAN DATASET BARU ===")
print(f"Total Baris Data : {len(df):,}")
print(f"Kolom            : {list(df.columns)}")
print(f"Daftar Subjek    : {df['subjek'].unique().tolist()}")
print(f"Daftar Sesi      : {df['sesi'].unique().tolist()}")
print(f"Posisi Sensor    : {df['posisi'].unique().tolist()}")
print("Distribusi Kelas per Label:")
print(df['label'].value_counts())
print("\nDistribusi Sesi & Subjek:")
print(df.groupby(['subjek', 'sesi', 'posisi', 'label']).size())

# Simpan ke CSV dan Excel
csv_path = "TUGAS BESAR/dataset_aktivitas_primer.csv"
xlsx_path = "TUGAS BESAR/dataset_aktivitas_primer.xlsx"
xlsx_natural_path = "TUGAS BESAR/dataset_aktivitas_primer_natural.xlsx"

print(f"\nMenyimpan ke CSV: {csv_path}...")
df.to_csv(csv_path, index=False)
print("Menyimpan ke Excel: dataset_aktivitas_primer.xlsx...")
df.to_excel(xlsx_path, index=False, engine='openpyxl')
print("Menyimpan ke Excel: dataset_aktivitas_primer_natural.xlsx...")
df.to_excel(xlsx_natural_path, index=False, engine='openpyxl')

print("Penyimpanan dataset berhasil tuntas 100%!")
