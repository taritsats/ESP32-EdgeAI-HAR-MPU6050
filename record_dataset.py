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

import sys
import time
import os
import serial
import serial.tools.list_ports

def get_available_ports():
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]

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
    for i, p in enumerate(ports):
        print(f"  [{i + 1}] {p}")

    if len(ports) == 1:
        selected_port = ports[0]
        print(f"Otomatis memilih port: {selected_port}")
    else:
        choice = input(f"Pilih nomor port (1-{len(ports)}): ").strip()
        try:
            selected_port = ports[int(choice) - 1]
        except (ValueError, IndexError):
            selected_port = ports[0]
            print(f"Pilihan tidak valid, menggunakan port default: {selected_port}")

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

    target_sampel = durasi * 50  # 50 Hz -> 50 sampel per detik
    output_filename = input("\nNama file penyimpanan [default: dataset_aktivitas_primer.csv]: ").strip() or "dataset_aktivitas_primer.csv"

    # 3. Membuka Koneksi Serial ke ESP32
    print(f"\n[INFO] Menghubungkan ke {selected_port} pada baudrate 115200...")
    try:
        ser = serial.Serial(selected_port, 115200, timeout=1)
        time.sleep(2)  # Tunggu ESP32 reset/stabil
        ser.reset_input_buffer()
    except Exception as e:
        print(f"[ERROR] Gagal membuka port serial: {e}")
        return

    # Kirim perintah label ke ESP32
    ser.write(command_char.encode('utf-8'))
    time.sleep(0.1)

    # 4. Hitung Mundur Persiapan Pengguna
    print("\n" + "=" * 50)
    print(f"SIAP-SIAP! Mulai melakukan aktivitas: [{label_aktivitas.upper()}]")
    print(f"Sensor dipasang di: [{posisi.upper()}], Subjek: [{subjek}]")
    print("=" * 50)
    for i in range(3, 0, -1):
        print(f"Perekaman dimulai dalam... {i}")
        time.sleep(1)
    print(">>> PEREKAMAN DIMULAI! LAKUKAN GERAKAN SEKARANG! <<<\n")

    # Buka file CSV (mode append jika file sudah ada, atau buat baru dengan header)
    file_exists = os.path.exists(output_filename)
    csv_file = open(output_filename, "a", encoding="utf-8")
    if not file_exists or os.path.getsize(output_filename) == 0:
        csv_file.write("timestamp_ms,subjek,sesi,posisi,ax,ay,az,gx,gy,gz,label\n")

    recorded_count = 0
    start_time = time.time()

    try:
        while recorded_count < target_sampel:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                # Abaikan baris komentar atau pesan inisialisasi ESP32
                if not line or line.startswith("#") or line.startswith("=") or line.startswith("-") or "timestamp" in line:
                    continue
                
                parts = line.split(",")
                if len(parts) >= 8:
                    # Pastikan format data valid
                    try:
                        t_ms = parts[0]
                        ax, ay, az = float(parts[4]), float(parts[5]), float(parts[6])
                        
                        # Cek apakah sensor terbaca nol semua
                        if ax == 0.0 and ay == 0.0 and az == 0.0:
                            if recorded_count % 100 == 0:
                                sys.stdout.write("\n[PERINGATAN] Nilai sensor 0.0 semua! Sensor MPU-6050 tidak terdeteksi. Periksa kabel SDA (21), SCL (22), VCC, dan GND!\n")
                        
                        # Susun baris rapi
                        row_str = f"{t_ms},{subjek},{sesi},{posisi},{parts[4]},{parts[5]},{parts[6]},{parts[7]},{parts[8]},{parts[9]},{label_aktivitas}\n"
                        csv_file.write(row_str)
                        recorded_count += 1

                        # Tampilkan progress bar interaktif di terminal
                        percent = (recorded_count / target_sampel) * 100
                        bar_len = 30
                        filled = int(bar_len * recorded_count // target_sampel)
                        bar = "█" * filled + "░" * (bar_len - filled)
                        elapsed = time.time() - start_time
                        sys.stdout.write(f"\rProg: [{bar}] {recorded_count}/{target_sampel} ({percent:.1f}%) | {elapsed:.1f}s | ax:{ax:+.2f} ay:{ay:+.2f} az:{az:+.2f}")
                        sys.stdout.flush()
                    except (ValueError, IndexError):
                        continue
    except KeyboardInterrupt:
        print("\n[PERINGATAN] Perekaman dihentikan lebih awal oleh pengguna!")
    finally:
        csv_file.close()
        ser.close()

    print("\n\n" + "=" * 65)
    print(f"[SUKSES] Berhasil merekam {recorded_count} sampel aktivitas '{label_aktivitas}'!")
    print(f"Data tersimpan di berkas: {output_filename}")
    print("=" * 65)

    # Opsi konversi ke XLSX jika ada pandas/openpyxl
    try:
        import pandas as pd
        df = pd.read_csv(output_filename)
        xlsx_name = output_filename.replace(".csv", ".xlsx")
        df.to_excel(xlsx_name, index=False)
        print(f"[INFO] Berkas Excel diperbarui: {xlsx_name}")
        print(f"Total baris saat ini di dataset: {len(df)} baris")
        print("Distribusi aktivitas saat ini:")
        print(df['label'].value_counts())
    except Exception:
        pass

if __name__ == "__main__":
    main()
