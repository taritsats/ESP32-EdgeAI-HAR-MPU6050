#!/usr/bin/env python3
"""
======================================================================================
SKRIP PEREKAM DATA PRIMER SENSOR MPU-6050 DARI ESP32 KE FILE CSV
Mata Kuliah : Edge Intelligent and Computing (CCE60306)
Laboratorium: Robotic and Embedded Systems Laboratory (RESLAB FILKOM UB)
======================================================================================
Cara Penggunaan:
1. Hubungkan ESP32 yang sudah diisi program 'ESP32_Data_Logger_MPU6050.ino' ke laptop.
2. Jalankan skrip ini di terminal:
       python record_dataset.py
3. Skrip akan mendeteksi Port COM otomatis, menanyakan Subjek, Posisi, dan Aktivitas.
4. Data akan otomatis tercatat dan tersimpan rapi ke file CSV.
======================================================================================
"""

import csv
import math
import time
from pathlib import Path
import serial
import serial.tools.list_ports

CSV_HEADER = ("timestamp_ms", "subjek", "sesi", "posisi", "ax", "ay", "az", "gx", "gy", "gz", "label")
NO_SAMPLE_TIMEOUT = 5.0


def get_available_ports():
    return [port for port in serial.tools.list_ports.comports()
            if "bluetooth" not in (port.description or "").casefold()]


def parse_sensor_sample(line, label):
    fields = line.split(",")
    if len(fields) != len(CSV_HEADER) or fields[-1].casefold() != label:
        return None
    try:
        milliseconds = int(fields[0])
        measurements = [float(value) for value in fields[4:10]]
    except ValueError:
        return None
    if (milliseconds < 0 or not all(math.isfinite(value) for value in measurements)
            or not any(measurements[:3])):
        return None
    return milliseconds, fields[4:10], measurements[:3]


def collect_samples(port, label, target):
    samples = []
    last_valid = time.monotonic()
    try:
        while len(samples) < target:
            if time.monotonic() - last_valid >= NO_SAMPLE_TIMEOUT:
                return samples, "Tidak ada sampel valid selama 5 detik. Cek port dan koneksi MPU-6050."
            line = port.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("# MPU_ERROR:"):
                return samples, line.removeprefix("# MPU_ERROR:").strip()
            sample = parse_sensor_sample(line, label)
            if sample is None:
                continue

            milliseconds, measurements, (ax, ay, az) = sample
            if samples and milliseconds <= samples[-1][0]:
                return samples, "Waktu sensor kembali ke awal. ESP32 mungkin baru saja reset."
            samples.append((milliseconds, measurements))
            last_valid = time.monotonic()
            print(f"\r{len(samples)}/{target} | ax:{ax:+.2f} ay:{ay:+.2f} az:{az:+.2f} g",
                  end="", flush=True)
    except KeyboardInterrupt:
        return samples, "Perekaman dihentikan pengguna."
    except serial.SerialException as error:
        return samples, f"Sambungan serial terputus: {error}"
    return samples, None

def main():
    print("=" * 65)
    print("      AKUISISI DATA PRIMER SENSOR MPU-6050 - ESP32 (50 HZ)")
    print("=" * 65)

    # 1. Deteksi Port Serial
    ports = get_available_ports()
    if not ports:
        print("[ERROR] Tidak ada perangkat USB Serial (ESP32) yang terdeteksi!")
        print("Pastikan kabel USB ESP32 sudah tercolok dan driver CH340 / CP210x terpasang.")
        return

    print("Daftar Port COM yang tersedia:")
    for i, port in enumerate(ports, 1):
        print(f"  [{i}] {port.device} - {port.description}")

    if len(ports) == 1:
        selected_port = ports[0].device
        print(f"Otomatis memilih port: {selected_port}")
    else:
        choice = input(f"Pilih nomor port (1-{len(ports)}): ").strip()
        try:
            index = int(choice) - 1
            if index < 0:
                raise IndexError
            selected_port = ports[index].device
        except (ValueError, IndexError):
            print("[ERROR] Pilih nomor port USB ESP32 yang benar.")
            return

    # 2. Input Metadata Eksperimen
    print("\n--- PENGATURAN METADATA PEREKAMAN ---")
    subjek = input("ID Subjek Penguji [default: S01]: ").strip().upper() or "S01"
    
    print("\nPilih Posisi Pemasangan Sensor pada Tubuh:")
    print("  [1] Pergelangan Tangan (Wrist)")
    print("  [2] Saku Celana (Pocket)")
    print("  [3] Pinggang (Waist)")
    pos_choice = input("Pilihan Posisi (1/2/3) [default: 1]: ").strip()
    pos_map = {"1": "pergelangan", "2": "saku_celana", "3": "pinggang"}
    posisi = pos_map.get(pos_choice, "pergelangan")

    sesi = input("Sesi Ke- [default: 1]: ").strip() or "1"

    print("\nPilih Aktivitas yang Ingin Direkam:")
    print("  [1] DIAM  (Stationary / Duduk / Berdiri tenang)")
    print("  [2] JALAN (Walking / Berjalan santai irama teratur)")
    print("  [3] LARI  (Running / Jogging atau lari dinamis)")
    act_choice = input("Pilihan Aktivitas (1/2/3): ").strip()
    act_map = {"1": ("diam", "d"), "2": ("jalan", "j"), "3": ("lari", "l")}
    
    if act_choice not in act_map:
        print("[ERROR] Pilihan aktivitas tidak valid! Program dibatalkan.")
        return
    
    label_aktivitas, command_char = act_map[act_choice]

    durasi_detik = input("Durasi perekaman dalam detik (misal: 30 atau 60) [default: 30]: ").strip()
    try:
        durasi = int(durasi_detik)
    except ValueError:
        durasi = 30

    if durasi <= 0:
        print("[ERROR] Durasi perekaman harus lebih dari nol.")
        return
    target_sampel = durasi * 50  # 50 Hz -> 50 sampel per detik
    root = Path(__file__).resolve().parent
    default_path = root / "data_local" / "rekaman_aktivitas.csv"
    output_name = input("\nNama file penyimpanan [default: data_local/rekaman_aktivitas.csv]: ").strip()
    output_path = Path(output_name).resolve() if output_name else default_path
    if output_path.suffix.lower() != ".csv":
        print("[ERROR] Gunakan nama berkas dengan ekstensi .csv.")
        return
    if output_path == root / "dataset_aktivitas_primer.csv":
        print("[ERROR] Pilih berkas lain agar demo sintetis dan rekaman nyata tetap terpisah.")
        return
    # 3. Membuka Koneksi Serial ke ESP32
    print(f"\n[INFO] Menghubungkan ke {selected_port} pada baudrate 115200...")
    try:
        with serial.Serial(selected_port, 115200, timeout=1) as port:
            time.sleep(2)  # Tunggu ESP32 reset/stabil.
            port.write(command_char.encode("ascii"))
            print(f"\nSiapkan aktivitas {label_aktivitas.upper()} untuk {subjek} ({posisi}).")
            for remaining in range(3, 0, -1):
                print(f"Perekaman dimulai dalam... {remaining}")
                time.sleep(1)
            port.reset_input_buffer()
            print("Mulai gerakan sekarang.")
            samples, reason = collect_samples(port, label_aktivitas, target_sampel)
    except serial.SerialException as error:
        print(f"[ERROR] Gagal berkomunikasi dengan {selected_port}: {error}")
        return

    if reason:
        print(f"\n[PERINGATAN] {reason}")
    if not samples:
        print("[ERROR] Perekaman menghasilkan 0 sampel valid.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    first_timestamp = samples[0][0]
    with output_path.open("a", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        if csv_file.tell() == 0:
            writer.writerow(CSV_HEADER)
        writer.writerows((timestamp - first_timestamp, subjek, sesi, posisi, *values, label_aktivitas)
                         for timestamp, values in samples)
    print(f"\nTersimpan {len(samples)}/{target_sampel} sampel valid di {output_path}")

    # Opsi konversi ke XLSX jika ada pandas/openpyxl
    try:
        import pandas as pd
        df = pd.read_csv(output_path)
        xlsx_name = output_path.with_suffix(".xlsx")
        df.to_excel(xlsx_name, index=False)
        print(f"[INFO] Berkas Excel diperbarui: {xlsx_name}")
        print(f"Total baris saat ini di dataset: {len(df)} baris")
        print("Distribusi aktivitas saat ini:")
        print(df['label'].value_counts())
    except Exception:
        pass

if __name__ == "__main__":
    main()
