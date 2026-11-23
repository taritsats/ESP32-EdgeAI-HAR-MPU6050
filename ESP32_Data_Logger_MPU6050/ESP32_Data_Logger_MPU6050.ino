/*
 * ======================================================================================
 * PROGRAM ESP32 DATA LOGGER SENSOR MPU-6050 (PENGAMBILAN DATA PRIMER)
 * Mata Kuliah : Edge Intelligent and Computing (CCE60306)
 * Laboratorium: CSUB - Robotic and Embedded Systems Laboratory (RESLAB FILKOM UB)
 * --------------------------------------------------------------------------------------
 * Deskripsi:
 * Program ini digunakan untuk mengambil data primer akselerometer dan giroskop dari sensor
 * MPU-6050 secara real-time pada frekuensi 50 Hz (interval 20 ms) menggunakan ESP32.
 * Data diformat dalam struktur CSV dan dikirimkan melalui Serial Monitor (Baudrate 115200).
 *
 * Pengguna dapat mengubah label aktivitas saat perekaman dengan mengirimkan karakter:
 *   - 'd' atau '0' : Label "diam"
 *   - 'j' atau '1' : Label "jalan"
 *   - 'l' atau '2' : Label "lari"
 *   - 's'          : Menghentikan / Menjeda streaming
 *
 * Konfigurasi Pin I2C ESP32:
 *   - SDA : GPIO 21
 *   - SCL : GPIO 22
 *   - VCC : 3.3V / 5V
 *   - GND : GND
 * ======================================================================================
 */

#include <Wire.h>

// Alamat I2C MPU-6050 (default 0x68, atau 0x69 jika AD0 HIGH)
uint8_t MPU_ADDR = 0x68;
bool sensorDetected = false;

// Inisialisasi Sensor MPU-6050
bool setupMPU6050() {
  Wire.begin(21, 22); // SDA = GPIO21, SCL = GPIO22
  Wire.setClock(400000); // Fast I2C 400 kHz

  // Cek apakah sensor ada di 0x68
  Wire.beginTransmission(0x68);
  if (Wire.endTransmission() == 0) {
    MPU_ADDR = 0x68;
    sensorDetected = true;
  } else {
    // Coba cek alamat alternatif 0x69
    Wire.beginTransmission(0x69);
    if (Wire.endTransmission() == 0) {
      MPU_ADDR = 0x69;
      sensorDetected = true;
      Serial.println("[INFO] Sensor terdeteksi di alamat alternatif 0x69!");
    } else {
      sensorDetected = false;
      Serial.println("\n**************************************************************");
      Serial.println("[ERROR FATAL] SENSOR MPU-6050 TIDAK TERDETEKSI PADA I2C!");
      Serial.println("Penyebab:");
      Serial.println("  1. Kabel SDA (GPIO 21) atau SCL (GPIO 22) kendor / terbalik.");
      Serial.println("  2. Kabel VCC (3.3V) atau GND belum terhubung.");
      Serial.println("Data akan bernilai 0.0 sampai kabel diperbaiki.");
      Serial.println("**************************************************************\n");
      return false;
    }
  }

  // Bangunkan MPU-6050 dari mode Sleep (Power Management 1)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // Register PWR_MGMT_1
  Wire.write(0x00); // Bangunkan MPU6050
  Wire.endTransmission(true);

  // Konfigurasi Accelerometer ke Rentang +/- 4g (Register ACCEL_CONFIG 0x1C)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C);
  Wire.write(0x08);
  Wire.endTransmission(true);

  // Konfigurasi Gyroscope ke Rentang +/- 500 deg/s (Register GYRO_CONFIG 0x1B)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1B);
  Wire.write(0x08);
  Wire.endTransmission(true);

  // Low Pass Filter 44 Hz (Register CONFIG 0x1A)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1A);
  Wire.write(0x03);
  Wire.endTransmission(true);

  Serial.println("[OK] Sensor MPU-6050 Berhasil Dikonfigurasi!");
  return true;
}

// Membaca Data Akselerasi dan Rotasi Mentah
void readMPU6050(float &ax, float &ay, float &az, float &gx, float &gy, float &gz) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); // Memulai pembacaan dari ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true); // Baca 14 byte register secara berurutan

  if (Wire.available() >= 14) {
    int16_t raw_ax = (Wire.read() << 8) | Wire.read();
    int16_t raw_ay = (Wire.read() << 8) | Wire.read();
    int16_t raw_az = (Wire.read() << 8) | Wire.read();
    int16_t raw_temp = (Wire.read() << 8) | Wire.read(); // Lewati temperatur
    int16_t raw_gx = (Wire.read() << 8) | Wire.read();
    int16_t raw_gy = (Wire.read() << 8) | Wire.read();
    int16_t raw_gz = (Wire.read() << 8) | Wire.read();

    // Konversi ke satuan fisik (g untuk akselerasi, deg/s untuk giroskop)
    ax = (float)raw_ax / ACCEL_SCALE;
    ay = (float)raw_ay / ACCEL_SCALE;
    az = (float)raw_az / ACCEL_SCALE;
    gx = (float)raw_gx / GYRO_SCALE;
    gy = (float)raw_gy / GYRO_SCALE;
    gz = (float)raw_gz / GYRO_SCALE;
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  setupMPU6050();

  Serial.println("\n=======================================================");
  Serial.println("ESP32 MPU-6050 PRIMARY DATA LOGGER - 50 HZ SAMPLING");
  Serial.println("=======================================================");
  Serial.println("Ketik karakter di Serial Monitor untuk ganti label:");
  Serial.println("  'd' -> Set Label 'diam'");
  Serial.println("  'j' -> Set Label 'jalan'");
  Serial.println("  'l' -> Set Label 'lari'");
  Serial.println("  's' -> Jeda / Lanjutkan perekaman");
  Serial.println("-------------------------------------------------------");
  Serial.println("timestamp_ms,subjek,sesi,posisi,ax,ay,az,gx,gy,gz,label");

  startTimestamp = millis();
  lastSampleTime = millis();
}

void loop() {
  // Cek masukan Serial untuk kontrol label interaktif
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == 'd' || cmd == '0') {
      currentLabel = "diam";
      Serial.println("# Label diubah ke: DIAM");
    } else if (cmd == 'j' || cmd == '1') {
      currentLabel = "jalan";
      Serial.println("# Label diubah ke: JALAN");
    } else if (cmd == 'l' || cmd == '2') {
      currentLabel = "lari";
      Serial.println("# Label diubah ke: LARI");
    } else if (cmd == 's') {
      isLogging = !isLogging;
      Serial.print("# Status Logging: ");
      Serial.println(isLogging ? "RUNNING" : "PAUSED");
    }
  }

  // Pengambilan data periodik dengan presisi 50 Hz (interval 20 ms)
  unsigned long currentMillis = millis();
  if (isLogging && (currentMillis - lastSampleTime >= SAMPLING_PERIOD_MS)) {
    lastSampleTime += SAMPLING_PERIOD_MS;
    unsigned long timeElapsed = currentMillis - startTimestamp;

    float ax = 0, ay = 0, az = 0;
    float gx = 0, gy = 0, gz = 0;
    readMPU6050(ax, ay, az, gx, gy, gz);

    // Cetak format CSV ke Serial Monitor
    Serial.print(timeElapsed);
    Serial.print(",");
    Serial.print(currentSubjek);
    Serial.print(",");
    Serial.print(currentSesi);
    Serial.print(",");
    Serial.print(currentPosisi);
    Serial.print(",");
    Serial.print(ax, 4);
    Serial.print(",");
    Serial.print(ay, 4);
    Serial.print(",");
    Serial.print(az, 4);
    Serial.print(",");
    Serial.print(gx, 2);
    Serial.print(",");
    Serial.print(gy, 2);
    Serial.print(",");
    Serial.print(gz, 2);
    Serial.print(",");
    Serial.println(currentLabel);
  }
}
