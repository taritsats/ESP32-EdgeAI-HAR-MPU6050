/*
 * ======================================================================================
 * PROGRAM ESP32 STANDALONE DATA LOGGER (TANPA MEMBAWA LAPTOP)
 * Menyimpan Data Sensor MPU-6050 Langsung ke Memori Internal ESP32 (SPIFFS / Flash)
 * Cukup Ditenagai Power Bank / Baterai
 * --------------------------------------------------------------------------------------
 * Cara Kerja:
 * 1. Pasang ESP32 + MPU-6050 pada tubuh (saku/pergelangan), colok ke Power Bank.
 * 2. Tombol BOOT (GPIO 0) pada ESP32 digunakan untuk berpindah mode:
 *    - Tekan 1x : Rekam DIAM (OLED menampilkan status DIAM & hitung mundur 60s)
 *    - Tekan 1x : Rekam JALAN (OLED menampilkan status JALAN & hitung mundur 60s)
 *    - Tekan 1x : Rekam LARI (OLED menampilkan status LARI & hitung mundur 60s)
 * 3. Setelah selesai, hubungkan ESP32 ke laptop:
 *    - Buka browser ke IP ESP32 (atau buka Serial Monitor dan ketik 'download'),
 *      maka file CSV dapat langsung diunduh ke laptop!
 * ======================================================================================
 */

#include <Wire.h>
#include <SPIFFS.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
bool displayReady = false;

uint8_t mpuAddress = 0;
const float ACCEL_SCALE = 8192.0f; // Rentang +/- 4g
const float GYRO_SCALE  = 65.5f;

#define PIN_BUTTON 0  // Tombol BOOT bawaan ESP32 (GPIO 0)
#define PIN_BUZZER 18 // Buzzer indikator pergantian mode

// Variabel Waktu Sampling 50 Hz (20 ms)
const unsigned long SAMPLING_PERIOD_MS = 20;
unsigned long lastSampleTime = 0;

// Status Perekaman
enum State { IDLE, RECORDING_DIAM, RECORDING_JALAN, RECORDING_LARI, COMPLETED };
State currentState = IDLE;

File dataFile;
int sampleCounter = 0;
const int TARGET_SAMPLES = 3000; // 60 detik * 50 Hz = 3000 sampel per aktivitas
unsigned long stateStartTime = 0;

// Web Server untuk unduh file CSV tanpa kabel
WebServer server(80);
const char* AP_SSID = "ESP32_DATA_LOGGER";
const char* AP_PASS = "12345678";

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
    const int value = Wire.read();
    if (value < 0) return false;
    bytes[i] = static_cast<uint8_t>(value);
  }
  return true;
}

void initMPU6050() {
  const uint8_t addresses[] = {0x68, 0x69};
  for (const uint8_t address : addresses) {
    uint8_t identity = 0;
    // WHO_AM_I tetap 0x68 pada kedua alamat I2C.
    if (!readMPURegisters(address, 0x75, &identity, 1) || identity != 0x68) continue;
    if (!writeMPURegister(address, 0x6B, 0x00) ||
        !writeMPURegister(address, 0x1C, 0x08) ||
        !writeMPURegister(address, 0x1B, 0x08) ||
        !writeMPURegister(address, 0x1A, 0x03)) continue;
    delay(50);
    mpuAddress = address;
    Serial.printf("# MPU_READY: 0x%02X\n", static_cast<unsigned int>(address));
    return;
  }
  Serial.println("# MPU_ERROR: MPU-6050 gagal diinisialisasi pada 0x68/0x69.");
}

int16_t readSignedWord(const uint8_t* bytes) {
  return static_cast<int16_t>((bytes[0] << 8) | bytes[1]);
}

// Membaca Data Akselerasi dan Rotasi Mentah
bool readMPU6050(float &ax, float &ay, float &az, float &gx, float &gy, float &gz) {
  uint8_t bytes[14];
  if (!readMPURegisters(mpuAddress, 0x3B, bytes, sizeof bytes)) return false;

  const int16_t x = readSignedWord(bytes);
  const int16_t y = readSignedWord(bytes + 2);
  const int16_t z = readSignedWord(bytes + 4);
  if (x == 0 && y == 0 && z == 0) return false;

  ax = x / ACCEL_SCALE;
  ay = y / ACCEL_SCALE;
  az = z / ACCEL_SCALE;
  gx = readSignedWord(bytes + 8) / GYRO_SCALE;
  gy = readSignedWord(bytes + 10) / GYRO_SCALE;
  gz = readSignedWord(bytes + 12) / GYRO_SCALE;
  return true;
}

void beep(int ms) {
  digitalWrite(PIN_BUZZER, HIGH);
  delay(ms);
  digitalWrite(PIN_BUZZER, LOW);
}

void updateOLED(String line1, String line2, String line3) {
  if (!displayReady) return;
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("STANDALONE LOGGER");
  display.drawLine(0, 10, 128, 10, SSD1306_WHITE);
  
  display.setCursor(0, 16);
  display.setTextSize(2);
  display.println(line1);

  display.setTextSize(1);
  display.setCursor(0, 38);
  display.println(line2);
  display.setCursor(0, 50);
  display.println(line3);
  display.display();
}

void handleRoot() {
  String html = "<html><head><title>ESP32 Data Logger</title></head><body>";
  html += "<h2>Data Primer ESP32 MPU-6050</h2>";
  html += "<p>Klik tombol di bawah untuk mengunduh berkas dataset CSV:</p>";
  html += "<a href='/download'><button style='padding:15px 25px;font-size:18px;background:#28a745;color:white;border:none;border-radius:5px;'>Unduh dataset_aktivitas_primer.csv</button></a>";
  html += "<br><br><form action='/clear' method='POST'><button style='background:#dc3545;color:white;padding:10px;'>Hapus / Format Data Lama</button></form>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

void handleDownload() {
  if (SPIFFS.exists("/dataset.csv")) {
    File f = SPIFFS.open("/dataset.csv", "r");
    server.streamFile(f, "text/csv");
    f.close();
  } else {
    server.send(404, "text/plain", "File /dataset.csv tidak ditemukan di memori SPIFFS.");
  }
}

void handleClear() {
  SPIFFS.remove("/dataset.csv");
  server.send(200, "text/html", "<h3>Memori Berhasil Dikosongkan!</h3><a href='/'>Kembali</a>");
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);

  Wire.begin(21, 22, static_cast<uint32_t>(100000));
  displayReady = display.begin(SSD1306_SWITCHCAPVCC, 0x3C, true, false);
  initMPU6050();

  if (!SPIFFS.begin(true)) {
    Serial.println("[ERROR] SPIFFS Gagal Diinisialisasi!");
  }

  // Buat Access Point WiFi agar bisa download via HP/Laptop
  WiFi.softAP(AP_SSID, AP_PASS);
  server.on("/", handleRoot);
  server.on("/download", handleDownload);
  server.on("/clear", handleClear);
  server.begin();

  beep(100);
  if (mpuAddress == 0) {
    updateOLED("IMU ERROR", "Cek kabel / I2C", "BOOT utk coba lagi");
  } else {
    updateOLED("STANDBY", "Tekan BOOT utk mulai", "WiFi: ESP32_DATA");
  }
}

void loop() {
  server.handleClient();
  // Deteksi Penekanan Tombol BOOT (GPIO 0)
  if (digitalRead(PIN_BUTTON) == LOW) {
    delay(200); // Debounce
    while (digitalRead(PIN_BUTTON) == LOW); // Tunggu lepas

    if (currentState == IDLE) {
      if (mpuAddress == 0) initMPU6050();
      if (mpuAddress == 0) {
        updateOLED("IMU ERROR", "Cek kabel / I2C", "BOOT utk coba lagi");
        return;
      }
      dataFile = SPIFFS.open("/dataset.csv", "a");
      if (!dataFile) {
        updateOLED("FILE ERROR", "CSV gagal dibuka", "Cek SPIFFS");
        return;
      }
      currentState = RECORDING_DIAM;
      sampleCounter = 0;
      if (dataFile.size() == 0) {
        dataFile.println("timestamp_ms,subjek,sesi,posisi,ax,ay,az,gx,gy,gz,label");
      }
      beep(150);
      stateStartTime = millis();
      lastSampleTime = stateStartTime;
    } else if (currentState == RECORDING_DIAM) {
      currentState = RECORDING_JALAN;
      sampleCounter = 0;
      beep(150);
      stateStartTime = millis();
      lastSampleTime = stateStartTime;
    } else if (currentState == RECORDING_JALAN) {
      currentState = RECORDING_LARI;
      sampleCounter = 0;
      beep(150);
      stateStartTime = millis();
      lastSampleTime = stateStartTime;
    } else if (currentState == RECORDING_LARI || currentState == COMPLETED) {
      currentState = IDLE;
      if (dataFile) dataFile.close();
      beep(300);
      updateOLED("SELESAI", "Buka Browser HP:", "http://192.168.4.1");
    }
  }

  // Perekaman Data 50 Hz
  const unsigned long now = millis();
  if (currentState != IDLE && currentState != COMPLETED) {
    if (now - lastSampleTime >= SAMPLING_PERIOD_MS) {
      lastSampleTime = now;
      float ax, ay, az, gx, gy, gz;
      if (!readMPU6050(ax, ay, az, gx, gy, gz)) {
        mpuAddress = 0;
        dataFile.close();
        currentState = IDLE;
        Serial.println("# MPU_ERROR: Pembacaan I2C gagal atau ketiga sumbu akselerasi nol.");
        updateOLED("IMU ERROR", "Rekaman berhenti", "BOOT utk coba lagi");
        return;
      }
      sampleCounter++;

      String lbl = (currentState == RECORDING_DIAM) ? "diam" : (currentState == RECORDING_JALAN ? "jalan" : "lari");
      unsigned long elapsed = now - stateStartTime;

      if (dataFile) {
        dataFile.printf("%lu,S01,1,saku_celana,%.4f,%.4f,%.4f,%.2f,%.2f,%.2f,%s\n",
                        elapsed, ax, ay, az, gx, gy, gz, lbl.c_str());
        if (sampleCounter % 50 == 0) dataFile.flush(); // Flush tiap 1 detik
      }

      // Update OLED tiap 250 ms
      if (sampleCounter % 12 == 0) {
        int sisaDetik = (TARGET_SAMPLES - sampleCounter) / 50;
        updateOLED(lbl, "Sampel: " + String(sampleCounter) + "/" + String(TARGET_SAMPLES), 
                   "Sisa Waktu: " + String(sisaDetik) + "s");
      }

      // Selesai 1 Aktivitas otomatis beralih atau jeda
      if (sampleCounter >= TARGET_SAMPLES) {
        beep(200); delay(100); beep(200);
        if (currentState == RECORDING_DIAM) {
          currentState = RECORDING_JALAN;
          sampleCounter = 0;
          stateStartTime = millis();
          lastSampleTime = stateStartTime;
        } else if (currentState == RECORDING_JALAN) {
          currentState = RECORDING_LARI;
          sampleCounter = 0;
          stateStartTime = millis();
          lastSampleTime = stateStartTime;
        } else {
          currentState = COMPLETED;
          if (dataFile) dataFile.close();
          beep(500);
          updateOLED("SELESAI!", "Buka Browser:", "http://192.168.4.1");
        }
      }
    }
  }
}
