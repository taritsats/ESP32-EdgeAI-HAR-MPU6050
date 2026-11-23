# Panduan Eksperimen Klasifikasi Aktivitas dengan ESP32
## SISTEM EDGE AI KLASIFIKASI AKTIVITAS MANUSIA (DIAM, JALAN, LARI) MENGGUNAKAN ESP32, SENSOR MPU-6050, OLED SSD1306, BUZZER, DAN CLOUD IOT RESLAB CSUB

---

**Mata Kuliah:** Edge Intelligent and Computing (CCE60306)  
**Dosen Pengampu:** Agung Setia Budi, S.T., M.T., M.Eng., Ph.D.  
**Laboratorium:** Robotic and Embedded Systems Laboratory (RESLAB - CSUB FILKOM UB)  
**Dokumen Acuan:** Penugasan Tugas Besar Edge AI HAR  

---

## DAFTAR ISI SESUAI KETENTUAN TUGAS:
1. **Langkah 1:** Pengambilan Data Primer Secara Mandiri
2. **Langkah 2:** Pelatihan Model Machine Learning di Python (.ipynb)
3. **Langkah 3:** Implementasi Inferensi di Edge Device (ESP32)
4. **Langkah 4:** Menampilkan Hasil Inferensi di OLED dan Buzzer
5. **Langkah 5:** Pengiriman Hasil Telemetri ke Platform IoT ResLab CSUB
6. **Langkah 6:** Konfigurasi Notifikasi Pengguna di Platform Cloud
7. **Langkah 7:** Panduan Pengerjaan Kelompok & Pengiriman Individu
8. **Langkah 8:** Checklist Material Pengumpulan (Upload File Terpisah)

---

### LANGKAH 1: Pengambilan Data Primer Secara Mandiri
> **Ketentuan:** *Dataset yang digunakan harus merupakan data primer yang diambil sendiri.*

* **Tujuan:** Mengakuisisi sinyal akselerasi fisik 3-sumbu ($a_x, a_y, a_z$) secara mandiri langsung dari pergerakan tubuh subjek menggunakan sensor MPU-6050 pada frekuensi 50 Hz (interval 20 ms).
* **Alat yang Digunakan:** ESP32, sensor MPU-6050, kabel jumper, kabel USB, dan solasi/strap pengikat.
* **Prosedur Pelaksanaan:**
  1. Pasang kabel I2C antara MPU-6050 dan ESP32:
     - `VCC` -> `3V3`
     - `GND` -> `GND`
     - `SDA` -> `GPIO 21`
     - `SCL` -> `GPIO 22`
  2. Buka dan upload firmware data logger: [`ESP32_Data_Logger_MPU6050.ino`](ESP32_Data_Logger_MPU6050/ESP32_Data_Logger_MPU6050.ino).
  3. Genggam modul ESP32 di telapak tangan (*handheld*) dengan layar OLED menghadap ke atas secara wajar dan rileks.
  4. Jalankan script perekam otomatis di Command Prompt / Terminal:
     ```bash
     python record_dataset.py
     ```
  5. Masukkan ID samaran yang konsisten per peserta, ID sesi, posisi, jenis aktivitas, dan durasi. Gunakan ID berbeda untuk setiap peserta.
  6. **SOP Gerakan Fisik:**
     - **DIAM:** Duduk santai di kursi atau berdiri tenang tanpa gerakan ($a_x, a_y \approx 0g, a_z \approx 0.98g$).
     - **JALAN:** Berjalan kaki santai dengan irama langkah normal 1.6 - 2.0 Hz di koridor ($\pm 0.4g$ s.d. $\pm 0.8g$).
     - **LARI:** Melakukan jogging atau lari santai 2.8 - 3.5 Hz dengan hentakan kaki dinamis ($\pm 2.0g$ s.d. $\pm 3.5g$).
  7. Rekaman tersimpan secara lokal di `data_local/rekaman_aktivitas.csv` dan, jika pustaka Excel tersedia, dalam format XLSX. CSV bawaan proyek berisi contoh sintetis.

---

### LANGKAH 2: Pelatihan Model Machine Learning di Python (.ipynb)
> **Ketentuan:** *Sistem dapat mengklasifikasikan aktifitas diam, jalan, dan berlari menggunakan salah satu algoritma mesin learning.*

* **Tujuan:** Melatih model cerdas ringan yang mampu mengenali pola temporal akselerasi dan mengekspor bobotnya ke format C header.
* **Prosedur Pelaksanaan:**
  1. Buka notebook: [`Pelatihan_Model_Klasifikasi_Aktivitas_ESP32.ipynb`](Pelatihan_Model_Klasifikasi_Aktivitas_ESP32.ipynb).
     Ubah `DATASET` menjadi `data_local/rekaman_aktivitas.csv` untuk eksperimen fisik.
  2. **Pemisahan subjek:** Tahan seluruh rekaman satu subjek di setiap fold sebelum membentuk jendela di set latih dan uji. Terapkan panjang jendela $W = 64$ sampel (1.28 detik pada 50 Hz) dengan langkah pergeseran $S = 32$ sampel (overlap 50%).
  3. **Ekstraksi 20 Fitur Statistik:** Hitung 5 metrik statistik untuk $a_x, a_y, a_z$, dan $\text{mag} = \sqrt{a_x^2 + a_y^2 + a_z^2}$:
     - Mean ($\mu$), Standard Deviation ($\sigma$), Minimum ($\min$), Maximum ($\max$), dan Root Mean Square (RMS).
  4. **Normalisasi:** Fit StandardScaler pada set latih setiap fold dan gunakan scaler tersebut pada set uji.
  5. **Pelatihan MLP Neural Network:**
     - Arsitektur: 20 input $\to$ Hidden 1 (16 ReLU) $\to$ Hidden 2 (8 ReLU) $\to$ Output (3 Softmax).
     - Optimizer: Adam, Loss: Cross-Entropy.
  6. **Evaluasi:** Catat metrik per fold, akurasi gabungan, dan matriks konfusi. Uji fisik akhir memakai peserta baru yang seluruh datanya disisihkan sejak awal.
  7. **Ekspor C Header:** Jalankan `python train_and_export.py --dataset data_local/rekaman_aktivitas.csv`. Skrip melatih model ekspor dari seluruh input dan menyimpan `model_weights.h` di `data_local/training/`.

---

### LANGKAH 3: Implementasi Inferensi di Edge Device (ESP32)
> **Ketentuan:** *Proses Inferensi dilakukan di dalam edge device (dalam kasus ini adalah ESP32).*

* **Tujuan:** Menjalankan model machine learning secara on-device di mikrokontroler tanpa ketergantungan internet/cloud.
* **Prosedur Pelaksanaan:**
  1. Buka proyek firmware: [`ESP32_Edge_Inference_MPU6050.ino`](ESP32_Edge_Inference_MPU6050/ESP32_Edge_Inference_MPU6050.ino).
  2. Untuk uji fisik, gunakan `model_weights.h` dari `data_local/training/` dalam salinan lokal folder firmware.
  3. Mekanisme Komputasi Edge pada Firmware:
     - Sensor dicuplik setiap 20 ms menggunakan timer non-blocking `millis()`.
     - Data ditampung pada circular ring buffer berukuran 64 sampel ($W=64$).
     - Setiap 32 sampel baru ($S=32$), fungsi `extractFeatures()` menghitung 20 fitur secara lokal .
     - Fungsi `predictActivity()` menjalankan forward pass MLP deterministik pada FPU 240 MHz ESP32.
  4. **Pengukuran perangkat:** Catat latensi dari serial dan penggunaan memori dari keluaran kompilasi. Tambahkan hasil pengukuran ke laporan pengujian.

---

### LANGKAH 4: Menampilkan Hasil Inferensi di OLED dan Buzzer
> **Ketentuan:** *Hasil dari proses inferensi ditunjukkan di edge device dengan menggunakan LCD OLED atau buzzer.*

* **Tujuan:** Memberikan antarmuka visual grafis dan audio langsung kepada pengguna pada perangkat portabel.
* **Pengkabelan Antarmuka Lokal:**
  - **OLED SSD1306 (0.96 inci I2C):** VCC -> 3V3, GND -> GND, SDA -> GPIO 21, SCL -> GPIO 22.
  - **Buzzer Aktif:** Pin (+) -> GPIO 18, Pin (-) -> GND.
* **Tampilan yang diperiksa saat pengujian:**
  1. **Tampilan Layar OLED:**
     - Judul: `--- EDGE AI HAR ---`
     - Status Aktivitas: Huruf besar jelas (`DIAM`, `JALAN`, atau `LARI`).
     - Metrik Inferensi: Nilai keyakinan (`Conf: 99.2%`) dan durasi latensi (`Latency: 215 us`).
     - Status Jaringan: `Cloud: Sent 200` atau `WiFi OK`.
  2. **Umpan Balik Audio Buzzer:**
     - **DIAM:** Senyap / tidak berbunyi (logika LOW) agar nyaman saat diam.
     - **JALAN:** Bunyi ketukan ritmis pendek 1 Hz (1 kali beep tiap 1 detik mengikuti ayunan langkah).
     - **LARI:** Alarm cepat berfrekuensi tinggi 4 Hz (bunyi cepat berulang) sebagai sinyal pergerakan cepat.

---

### LANGKAH 5: Pengiriman Hasil Telemetri ke Platform IoT ResLab CSUB
> **Ketentuan:** *Hasil dari proses inferensi juga dikirimkan ke platform (https://iot.reslab-csub.cloud/).*

* **Tujuan:** Menyimpan riwayat aktivitas secara nirkabel dan memvisualisasikan data pada platform ThingsBoard laboratorium.
* **Prosedur Pelaksanaan:**
  1. Login ke portal cloud: **`https://iot.reslab-csub.cloud/`**.
  2. Buka menu **Device Management > Devices**, klik **Add Device**, beri nama (misal: `ESP32-HAR-01`).
  3. Salin **Device Access Token** pada menu credentials perangkat.
  4. Isi `WIFI_SSID`, `WIFI_PASSWORD`, dan `DEVICE_ACCESS_TOKEN` di `ESP32_Edge_Inference_MPU6050.ino`.
  5. Upload firmware. ESP32 mencoba mengirim telemetri melalui HTTPS setiap 1,5 detik.
     `https://iot.reslab-csub.cloud/api/v1/<TOKEN>/telemetry`
     ```json
     {
       "aktivitas": "LARI",
       "confidence": 99.2,
       "latency_us": 215,
       "status_buzzer": 1
     }
     ```
  6. Periksa tab **Latest Telemetry** di platform ResLab CSUB, pastikan data berhasil masuk dengan kode respon **HTTP 200**.

---

### LANGKAH 6: Konfigurasi Notifikasi Pengguna di Platform Cloud
> **Ketentuan:** *Platform dapat memberikan notifikasi ke pengguna tentang aktifitas yang dilakukan.*

* **Tujuan:** Memberikan peringatan otomatis langsung ke gawai pengguna (smartphone) saat terdeteksi pergerakan lari atau transisi aktivitas.
* **Prosedur Pelaksanaan di ThingsBoard (ResLab CSUB):**
  1. Buka menu **Rule Chains > Root Rule Chain**.
  2. Tambahkan node **Filter - Script** dengan kode logika JavaScript:
     ```javascript
     return msg.aktivitas === 'LARI';
     ```
  3. Hubungkan cabang `True` ke node **Create Alarm** (Severity: `WARNING`, Alarm Type: `Aktivitas Lari Terdeteksi`).
  4. Hubungkan ke node **External - REST API Call** (mengarah ke Telegram Bot API):
     - URL: `https://api.telegram.org/bot<TOKEN_BOT>/sendMessage`
     - Method: `POST`
     - Body:
       ```json
       {
         "chat_id": "<CHAT_ID_PENGGUNA>",
         "text": "⚠️ RESLAB ALERT: Aktivitas LARI Terdeteksi pada ESP32!\nConfidence: " + msg.confidence + "%\nWaktu: " + new Date().toLocaleTimeString()
       }
       ```
  5. Saat pengguna berlari, bot Telegram akan langsung mengirimkan pesan push notification ke HP pengguna secara real-time.

---

### LANGKAH 7: Panduan Pengerjaan Kelompok & Pengiriman Individu
> **Ketentuan:** *Tugas dikerjakan berkelompok, tetapi pengiriman tugas harus individu.*

* **Pembagian Tugas Kelompok yang Efektif:**
  - **Anggota 1:** Merakit hardware (ESP32, MPU-6050, OLED, Buzzer) dan menjadi Subjek Uji S01.
  - **Anggota 2:** Menjalankan pengambilan data primer (`record_dataset.py`) untuk Subjek S02 dan melatih model di notebook `.ipynb`.
  - **Anggota 3:** Menjadi Subjek Uji S03, menyambungkan koneksi telemetri ke `iot.reslab-csub.cloud`, dan mengonfigurasi Rule Chain notifikasi Telegram.
* **Aturan Pengiriman:**
  - Meskipun pengujian dan perakitan alat dilakukan secara tim, setiap anggota **wajib mengunggah berkas secara mandiri melalui akun LMS masing-masing**.
  - Pada halaman sampul laporan, cantumkan Nama dan NIM Anda sendiri serta nama anggota kelompok Anda.

---

### LANGKAH 8: Checklist Material Pengumpulan (Upload File Terpisah)
> **Ketentuan:** *Material yang dikumpulkan meliputi 4 kategori dan diupload satu-satu (tidak di-zip dalam 1 folder).*

Unggah empat kategori berikut secara terpisah pada portal tugas.

| Material | Berkas |
| :--- | :--- |
| **1. Dataset** | `rekaman_aktivitas.csv` atau `rekaman_aktivitas.xlsx` dari `data_local/`. |
| **2. Notebook dan modul** | [Notebook pelatihan](Pelatihan_Model_Klasifikasi_Aktivitas_ESP32.ipynb) dan [`har_pipeline.py`](har_pipeline.py). |
| **3. Program ESP32** | [Sketch inferensi](ESP32_Edge_Inference_MPU6050/ESP32_Edge_Inference_MPU6050.ino) dan `model_weights.h` yang dipakai saat pengujian. |
| **4. Laporan pengujian** | [Laporan PDF](Laporan_Pengujian_Klasifikasi_Aktivitas_ESP32.pdf) atau [versi Word](Laporan_Pengujian_Klasifikasi_Aktivitas_ESP32.docx), dilengkapi hasil pengukuran perangkat. |

> ⚠️ **Peringatan Penting:** Dilarang mengompres berkas ke dalam format `.zip` atau `.rar`. Unggah setiap berkas di atas satu per satu pada slot pengumpulan tugas LMS Anda.
