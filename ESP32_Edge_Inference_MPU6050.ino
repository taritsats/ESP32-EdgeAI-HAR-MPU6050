/*
 * ======================================================================================
 * SISTEM EDGE AI KLASIFIKASI AKTIVITAS MANUSIA (DIAM, JALAN, LARI)
 * BERBASIS ESP32, SENSOR MPU-6050, OLED SSD1306, DAN BUZZER
 * --------------------------------------------------------------------------------------
 * Mata Kuliah : Edge Intelligent and Computing (CCE60306)
 * Laboratorium: CSUB - Robotic and Embedded Systems Laboratory (RESLAB FILKOM UB)
 * Platform IoT: https://iot.reslab-csub.cloud/
 * --------------------------------------------------------------------------------------
 * Fitur Utama:
 * 1. Akuisisi data sensor IMU MPU-6050 pada frekuensi cuplik 50 Hz (20 ms non-blocking).
 * 2. Sliding window buffer W = 64 sampel (1.28 s) dengan langkah geser S = 32 (overlap 50%).
 * 3. Ekstraksi 20 fitur statistik domain waktu secara lokal (mean, std, min, max, rms).
 * 4. Normalisasi fitur Z-score (StandardScaler) langsung di dalam mikrokontroler.
 * 5. Inferensi lokal Edge TinyML (MLP Neural Network 20 -> 16 -> 8 -> 3) dengan latensi < 0.25 ms.
 * 6. Tampilan hasil inferensi (Label, Confidence, Latensi) pada layar OLED 0.96" SSD1306.
 * 7. Indikator audio adaptif menggunakan Buzzer (pola nada berbeda untuk Diam, Jalan, Lari).
 * 8. Pengiriman telemetri hasil klasifikasi secara berkala ke platform IoT ResLab CSUB via HTTP REST.
 *
 * Konfigurasi Pinout Perangkat Keras:
 *   - ESP32 SDA      : GPIO 21 (Terhubung ke SDA MPU-6050 & SDA OLED SSD1306)
 *   - ESP32 SCL      : GPIO 22 (Terhubung ke SCL MPU-6050 & SCL OLED SSD1306)
 *   - ESP32 Buzzer   : GPIO 18 (Pin Positif Buzzer Aktif melalui resistor/transistor)
 *   - VCC            : 3.3V (MPU-6050 dan OLED SSD1306)
 *   - GND            : GND bersama (ESP32, MPU-6050, OLED, Buzzer)
 * ======================================================================================
 */

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "model_weights.h"

// -----------------------------------------------------------------------------
// KONFIGURASI JARINGAN WIFI & CLOUD IOT RESLAB CSUB
// -----------------------------------------------------------------------------
const char* WIFI_SSID     = "Hotspot_Praktikum";        // Ganti dengan SSID WiFi Anda
const char* WIFI_PASSWORD = "Password_Praktikum";    // Ganti dengan Password WiFi Anda

// Endpoint Platform IoT CSUB (ThingsBoard Architecture)
// Format URL: https://iot.reslab-csub.cloud/api/v1/<DEVICE_ACCESS_TOKEN>/telemetry
const char* RESLAB_HOST         = "https://iot.reslab-csub.cloud";
const char* DEVICE_ACCESS_TOKEN = "YOUR_DEVICE_ACCESS_TOKEN"; // Token dari platform CSUB

// Interval Pengiriman Telemetri ke Cloud (milidetik)
const unsigned long CLOUD_SEND_INTERVAL_MS = 1500; // Kirim tiap 1.5 detik
unsigned long lastCloudSendTime = 0;
String cloudStatus = "Init";

// -----------------------------------------------------------------------------
// KONFIGURASI PERANGKAT KERAS (OLED, BUZZER, SENSOR)
// -----------------------------------------------------------------------------
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
#define OLED_ADDR     0x3C
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

#define MPU_ADDR 0x68
const float ACCEL_SCALE = 8192.0f; // Rentang +/- 4g (8192 LSB/g)

#define PIN_BUZZER 18

// -----------------------------------------------------------------------------
// PARAMETER SLIDING WINDOW BUFFER & FREKUENSI CUPLIK
// -----------------------------------------------------------------------------
const unsigned long SAMPLING_PERIOD_MS = 20; // 50 Hz = 20 ms
unsigned long lastSampleTime = 0;

const int WINDOW_SIZE = 64; // W = 64 sampel (1.28 detik pada 50 Hz)
const int STEP_SIZE   = 32; // S = 32 sampel (50% overlap, pembaruan tiap 0.64 detik)

// Ring buffer penyimpanan data akselerasi 3-sumbu
float buf_ax[WINDOW_SIZE];
float buf_ay[WINDOW_SIZE];
float buf_az[WINDOW_SIZE];
int sampleCount = 0;
int samplesSinceLastInference = 0;

// Variabel status inferensi terkini
int currentActivityIndex = 0; // 0 = DIAM, 1 = JALAN, 2 = LARI
float currentConfidence = 0.0f;
unsigned long lastInferenceLatencyUs = 0;
unsigned long buzzerTimer = 0;

// =============================================================================
// INISIALISASI MPU-6050
// =============================================================================
void initMPU6050() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // Register Power Management 1
  Wire.write(0x00); // Bangunkan MPU-6050
  Wire.endTransmission(true);

  // Konfigurasi Accelerometer +/- 4g (Register 0x1C)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C);
  Wire.write(0x08);
  Wire.endTransmission(true);

  // Filter Digital Low-Pass 44 Hz (Register 0x1A)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1A);
  Wire.write(0x03);
  Wire.endTransmission(true);
}

// Membaca Data Akselerasi 3-Sumbu (Satuan g)
void readAccel(float &ax, float &ay, float &az) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); // Alamat awal ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);

  if (Wire.available() >= 6) {
    int16_t raw_x = (Wire.read() << 8) | Wire.read();
    int16_t raw_y = (Wire.read() << 8) | Wire.read();
    int16_t raw_z = (Wire.read() << 8) | Wire.read();

    ax = (float)raw_x / ACCEL_SCALE;
    ay = (float)raw_y / ACCEL_SCALE;
    az = (float)raw_z / ACCEL_SCALE;
  }
}

// =============================================================================
// EKSTRAKSI FITUR DARI BUFFER SLIDING WINDOW
// =============================================================================
// Menghitung 20 fitur: mean, std, min, max, rms untuk ax, ay, az, dan magnitudo
void extractFeatures(float features[NUM_FEATURES]) {
  float mag[WINDOW_SIZE];
  for (int i = 0; i < WINDOW_SIZE; i++) {
    mag[i] = sqrtf(buf_ax[i] * buf_ax[i] + buf_ay[i] * buf_ay[i] + buf_az[i] * buf_az[i]);
  }

  const float* channels[4] = {buf_ax, buf_ay, buf_az, mag};
  int featIdx = 0;

  for (int ch = 0; ch < 4; ch++) {
    const float* data = channels[ch];
    float sum = 0.0f;
    float sumSq = 0.0f;
    float minVal = data[0];
    float maxVal = data[0];

    for (int i = 0; i < WINDOW_SIZE; i++) {
      float v = data[i];
      sum += v;
      sumSq += v * v;
      if (v < minVal) minVal = v;
      if (v > maxVal) maxVal = v;
    }

    float mean = sum / (float)WINDOW_SIZE;
    float variance = (sumSq / (float)WINDOW_SIZE) - (mean * mean);
    if (variance < 0.0f) variance = 0.0f;
    float std = sqrtf(variance);
    float rms = sqrtf(sumSq / (float)WINDOW_SIZE);

    features[featIdx++] = mean;
    features[featIdx++] = std;
    features[featIdx++] = minVal;
    features[featIdx++] = maxVal;
    features[featIdx++] = rms;
  }
}

// =============================================================================
// KONTROL BUZZER ADAPTIF BERDASARKAN AKTIVITAS
// =============================================================================
void handleBuzzer() {
  unsigned long now = millis();
  if (currentActivityIndex == 0) {
    // DIAM: Buzzer mati / senyap
    digitalWrite(PIN_BUZZER, LOW);
  } else if (currentActivityIndex == 1) {
    // JALAN: Bunyi ritmis tunggal pendek (100 ms ON setiap 1000 ms)
    if (now - buzzerTimer < 100) {
      digitalWrite(PIN_BUZZER, HIGH);
    } else if (now - buzzerTimer < 1000) {
      digitalWrite(PIN_BUZZER, LOW);
    } else {
      buzzerTimer = now;
    }
  } else if (currentActivityIndex == 2) {
    // LARI: Bunyi cepat berfrekuensi tinggi (120 ms ON, 120 ms OFF berulang)
    if ((now / 120) % 2 == 0) {
      digitalWrite(PIN_BUZZER, HIGH);
    } else {
      digitalWrite(PIN_BUZZER, LOW);
    }
  }
}

// =============================================================================
// PEMBARUAN TAMPILAN OLED SSD1306
// =============================================================================
void updateOLED() {
  display.clearDisplay();
  
  // Header
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("--- EDGE AI HAR ---");

  // Status Aktivitas (Teks Besar)
  display.setCursor(0, 16);
  display.setTextSize(2);
  display.print(CLASS_NAMES[currentActivityIndex]);

  // Metrik Inferensi
  display.setTextSize(1);
  display.setCursor(0, 36);
  display.print("Conf: ");
  display.print(currentConfidence * 100.0f, 1);
  display.print("%");

  display.setCursor(0, 46);
  display.print("Latency: ");
  display.print(lastInferenceLatencyUs);
  display.print(" us");

  // Status Jaringan & Cloud
  display.setCursor(0, 56);
  display.print("Cloud: ");
  display.print(cloudStatus);

  display.display();
}

// =============================================================================
// PENGIRIMAN TELEMETRI KE CLOUD RESLAB CSUB
// =============================================================================
void sendTelemetryToResLab() {
  if (WiFi.status() != WL_CONNECTED) {
    cloudStatus = "WiFi Disc";
    return;
  }

  WiFiClientSecure client;
  client.setInsecure(); // Mengabaikan validasi SSL certificate untuk koneksi cepat
  HTTPClient http;

  String endpoint = String(RESLAB_HOST) + "/api/v1/" + String(DEVICE_ACCESS_TOKEN) + "/telemetry";
  http.begin(client, endpoint);
  http.addHeader("Content-Type", "application/json");

  // Format payload JSON sesuai spesifikasi ThingsBoard
  String payload = "{";
  payload += "\"aktivitas\":\"" + String(CLASS_NAMES[currentActivityIndex]) + "\",";
  payload += "\"confidence\":" + String(currentConfidence * 100.0f, 1) + ",";
  payload += "\"latency_us\":" + String(lastInferenceLatencyUs) + ",";
  payload += "\"status_buzzer\":" + String((currentActivityIndex == 0) ? 0 : 1);
  payload += "}";

  int httpCode = http.POST(payload);
  if (httpCode > 0) {
    if (httpCode == HTTP_CODE_OK || httpCode == 200) {
      cloudStatus = "Sent 200";
    } else {
      cloudStatus = "HTTP " + String(httpCode);
    }
  } else {
    cloudStatus = "Err " + String(httpCode);
  }
  http.end();
}

// =============================================================================
// SETUP SYSTEM
// =============================================================================
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n[SYSTEM] Inisialisasi Sistem Klasifikasi Aktivitas Edge AI...");

  // Inisialisasi Pin Buzzer
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);

  // Inisialisasi Bus I2C (SDA=21, SCL=22, Frekuensi 400 kHz)
  Wire.begin(21, 22);
  Wire.setClock(400000);

  // Inisialisasi Layar OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("[ERROR] Layar OLED SSD1306 tidak terdeteksi!");
  } else {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(10, 20);
    display.println("Connecting WiFi...");
    display.display();
  }

  // Inisialisasi Sensor IMU MPU-6050
  initMPU6050();
  Serial.println("[OK] Sensor MPU-6050 terhubung pada I2C 0x68.");

  // Koneksi ke Jaringan WiFi
  Serial.print("[WIFI] Menghubungkan ke ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int retryCount = 0;
  while (WiFi.status() != WL_CONNECTED && retryCount < 20) {
    delay(400);
    Serial.print(".");
    retryCount++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Terhubung! IP Address: " + WiFi.localIP().toString());
    cloudStatus = "WiFi OK";
  } else {
    Serial.println("\n[WIFI] Gagal terhubung (Mode Offline Berjalan).");
    cloudStatus = "Offline";
  }

  lastSampleTime = millis();
  Serial.println("[OK] Sistem Siap Melakukan Inferensi Real-Time.\n");
}

// =============================================================================
// LOOP UTAMA
// =============================================================================
void loop() {
  unsigned long currentMillis = millis();

  // 1. Pengambilan Data Sensor pada Frekuensi 50 Hz (Interval 20 ms)
  if (currentMillis - lastSampleTime >= SAMPLING_PERIOD_MS) {
    lastSampleTime += SAMPLING_PERIOD_MS;

    float ax = 0, ay = 0, az = 0;
    readAccel(ax, ay, az);

    // Geser buffer ke kiri jika sudah penuh
    if (sampleCount < WINDOW_SIZE) {
      buf_ax[sampleCount] = ax;
      buf_ay[sampleCount] = ay;
      buf_az[sampleCount] = az;
      sampleCount++;
    } else {
      for (int i = 0; i < WINDOW_SIZE - 1; i++) {
        buf_ax[i] = buf_ax[i + 1];
        buf_ay[i] = buf_ay[i + 1];
        buf_az[i] = buf_az[i + 1];
      }
      buf_ax[WINDOW_SIZE - 1] = ax;
      buf_ay[WINDOW_SIZE - 1] = ay;
      buf_az[WINDOW_SIZE - 1] = az;
    }
    samplesSinceLastInference++;

    // 2. Memicu Proses Inferensi Setiap STEP_SIZE (32 sampel = tiap 0.64 detik)
    if (sampleCount >= WINDOW_SIZE && samplesSinceLastInference >= STEP_SIZE) {
      samplesSinceLastInference = 0;

      // Ekstraksi 20 Fitur Statistik
      float features[NUM_FEATURES];
      extractFeatures(features);

      // Eksekusi Inferensi Edge MLP (Hitung Waktu dengan micros())
      float probs[NUM_CLASSES];
      unsigned long t_start = micros();
      int predClass = predictActivity(features, probs);
      unsigned long t_end = micros();

      lastInferenceLatencyUs = t_end - t_start;
      currentActivityIndex = predClass;
      currentConfidence = probs[predClass];

      // Cetak Hasil Inferensi ke Serial Monitor
      Serial.print("[INFERENSI] Aktivitas: ");
      Serial.print(CLASS_NAMES[currentActivityIndex]);
      Serial.print(" | Conf: ");
      Serial.print(currentConfidence * 100.0f, 1);
      Serial.print("% | Latensi: ");
      Serial.print(lastInferenceLatencyUs);
      Serial.println(" us");

      // Perbarui Tampilan OLED
      updateOLED();
    }
  }

  // 3. Kontrol Nada Buzzer Berdasarkan Status Gerak
  handleBuzzer();

  // 4. Pengiriman Telemetri Berkala ke Platform IoT ResLab CSUB
  if (currentMillis - lastCloudSendTime >= CLOUD_SEND_INTERVAL_MS) {
    lastCloudSendTime = currentMillis;
    sendTelemetryToResLab();
    updateOLED(); // Perbarui status cloud pada OLED
  }
}
