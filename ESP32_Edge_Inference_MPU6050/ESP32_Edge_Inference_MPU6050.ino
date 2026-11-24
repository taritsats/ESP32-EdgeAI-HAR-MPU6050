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

#ifndef MODEL_ACCEL_G_TO_UNIT
// Header lama untuk model yang dilatih dari keluaran logger dalam g.
#define MODEL_ACCEL_G_TO_UNIT 1.0f
#endif

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
bool displayReady = false;

constexpr float ACCEL_COUNTS_PER_G = 8192.0f; // Rentang +/- 4g
constexpr unsigned long SENSOR_RETRY_INTERVAL_MS = 1000;
uint8_t mpuAddress = 0;
unsigned long lastSensorAttempt = 0;

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
constexpr int NO_PREDICTION = -1;
int currentActivityIndex = NO_PREDICTION; // 0 = DIAM, 1 = JALAN, 2 = LARI
float currentConfidence = 0.0f;
unsigned long lastInferenceLatencyUs = 0;
unsigned long buzzerTimer = 0;

// =============================================================================
// INISIALISASI MPU-6050
// =============================================================================
bool writeMPURegister(uint8_t address, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readMPURegisters(uint8_t address, uint8_t reg, uint8_t* bytes, size_t count) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0 || Wire.requestFrom(address, count, true) != count) {
    return false;
  }
  for (size_t i = 0; i < count; ++i) {
    const int byteValue = Wire.read();
    if (byteValue < 0) return false;
    bytes[i] = static_cast<uint8_t>(byteValue);
  }
  return true;
}

void initMPU6050() {
  const uint8_t addresses[] = {0x68, 0x69};
  for (const uint8_t address : addresses) {
    uint8_t identity = 0;
    // WHO_AM_I tetap 0x68, termasuk saat AD0 memilih alamat bus 0x69.
    if (!readMPURegisters(address, 0x75, &identity, 1) || identity != 0x68) continue;
    if (!writeMPURegister(address, 0x6B, 0x00) ||
        !writeMPURegister(address, 0x1C, 0x08) ||
        !writeMPURegister(address, 0x1A, 0x03)) continue;

    delay(50);
    mpuAddress = address;
    Serial.printf("[MPU] Siap di 0x%02X\n", static_cast<unsigned int>(address));
    return;
  }
  Serial.println("[MPU] MPU-6050 gagal diinisialisasi pada 0x68/0x69. Cek kabel dan jumper.");
}

bool readAccelG(float &ax, float &ay, float &az) {
  uint8_t bytes[6];
  if (!readMPURegisters(mpuAddress, 0x3B, bytes, sizeof bytes)) return false;

  const int16_t x = static_cast<int16_t>((bytes[0] << 8) | bytes[1]);
  const int16_t y = static_cast<int16_t>((bytes[2] << 8) | bytes[3]);
  const int16_t z = static_cast<int16_t>((bytes[4] << 8) | bytes[5]);
  if (x == 0 && y == 0 && z == 0) return false;

  ax = x / ACCEL_COUNTS_PER_G;
  ay = y / ACCEL_COUNTS_PER_G;
  az = z / ACCEL_COUNTS_PER_G;
  return true;
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
  if (currentActivityIndex <= 0) {
    // DIAM atau prediksi belum tersedia.
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
  if (!displayReady) return;
  display.clearDisplay();
  
  // Header
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("--- EDGE AI HAR ---");

  // Status Aktivitas (Teks Besar)
  display.setCursor(0, 16);
  display.setTextSize(2);
  if (mpuAddress == 0) {
    display.print("IMU ERROR");
  } else if (currentActivityIndex == NO_PREDICTION) {
    display.print("MENUNGGU");
  } else {
    display.print(CLASS_NAMES[currentActivityIndex]);
  }

  // Metrik Inferensi
  display.setTextSize(1);
  display.setCursor(0, 36);
  if (mpuAddress == 0) {
    display.print("Cek kabel / I2C");
  } else if (currentActivityIndex == NO_PREDICTION) {
    display.print("Mengisi buffer");
  } else {
    display.print("Conf: ");
    display.print(currentConfidence * 100.0f, 1);
    display.print("%");
    display.setCursor(0, 46);
    display.print("Latency: ");
    display.print(lastInferenceLatencyUs);
    display.print(" us");
  }

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

  // Inisialisasi bus I2C bersama MPU-6050 dan OLED.
  Wire.begin(21, 22, static_cast<uint32_t>(100000));

  // Inisialisasi Layar OLED
  displayReady = display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR, true, false);
  if (!displayReady) {
    Serial.println("[ERROR] Layar OLED SSD1306 tidak terdeteksi!");
  }

  // Inisialisasi Sensor IMU MPU-6050
  initMPU6050();
  updateOLED();

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
  lastSensorAttempt = lastSampleTime;
  updateOLED();
}

// =============================================================================
// LOOP UTAMA
// =============================================================================
void sampleAndPredict() {
  float axG, ayG, azG;
  if (!readAccelG(axG, ayG, azG)) {
    Serial.println("[MPU] Pembacaan I2C gagal atau seluruh sumbu nol. Mencoba menghubungkan ulang.");
    mpuAddress = 0;
    lastSensorAttempt = millis();
    sampleCount = 0;
    samplesSinceLastInference = 0;
    currentActivityIndex = NO_PREDICTION;
    updateOLED();
    return;
  }

  // Geser buffer ke kiri jika sudah penuh dan gunakan satuan yang dipakai saat pelatihan.
  int index = sampleCount;
  if (sampleCount < WINDOW_SIZE) {
    sampleCount++;
  } else {
    for (int i = 0; i < WINDOW_SIZE - 1; i++) {
      buf_ax[i] = buf_ax[i + 1];
      buf_ay[i] = buf_ay[i + 1];
      buf_az[i] = buf_az[i + 1];
    }
    index = WINDOW_SIZE - 1;
  }
  buf_ax[index] = axG * MODEL_ACCEL_G_TO_UNIT;
  buf_ay[index] = ayG * MODEL_ACCEL_G_TO_UNIT;
  buf_az[index] = azG * MODEL_ACCEL_G_TO_UNIT;
  samplesSinceLastInference++;

  if (sampleCount < WINDOW_SIZE || samplesSinceLastInference < STEP_SIZE) return;
  samplesSinceLastInference = 0;

  float features[NUM_FEATURES];
  extractFeatures(features);
  float probs[NUM_CLASSES];
  const unsigned long startTime = micros();
  currentActivityIndex = predictActivity(features, probs);
  lastInferenceLatencyUs = micros() - startTime;
  currentConfidence = probs[currentActivityIndex];

  Serial.printf("[INFERENSI] %s | Conf: %.1f%% | Latensi: %lu us | ax=%.3f ay=%.3f az=%.3f g\n",
                CLASS_NAMES[currentActivityIndex], currentConfidence * 100.0f, lastInferenceLatencyUs,
                axG, ayG, azG);
  updateOLED();
}

void loop() {
  const unsigned long currentMillis = millis();

  if (mpuAddress == 0 && currentMillis - lastSensorAttempt >= SENSOR_RETRY_INTERVAL_MS) {
    lastSensorAttempt = currentMillis;
    initMPU6050();
    lastSampleTime = millis();
    updateOLED();
  } else if (mpuAddress != 0 && currentMillis - lastSampleTime >= SAMPLING_PERIOD_MS) {
    lastSampleTime = currentMillis;
    sampleAndPredict();
  }

  // 3. Kontrol Nada Buzzer Berdasarkan Status Gerak
  handleBuzzer();

  // 4. Pengiriman Telemetri Berkala ke Platform IoT ResLab CSUB
  if (currentActivityIndex != NO_PREDICTION &&
      currentMillis - lastCloudSendTime >= CLOUD_SEND_INTERVAL_MS) {
    lastCloudSendTime = currentMillis;
    sendTelemetryToResLab();
    updateOLED(); // Perbarui status cloud pada OLED
  }
}
