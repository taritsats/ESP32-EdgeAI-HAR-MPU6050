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
 *   - VCC : 3.3V
 *   - GND : GND
 * ======================================================================================
 */

#include <Wire.h>

constexpr float ACCEL_SCALE = 8192.0f; // +/- 4g
constexpr float GYRO_SCALE = 65.5f; // +/- 500 deg/s
constexpr unsigned long SAMPLING_PERIOD_MS = 20;
constexpr unsigned long SENSOR_RETRY_INTERVAL_MS = 1000;
uint8_t mpuAddress = 0;
unsigned long lastSensorAttempt = 0;
unsigned long startTimestamp = 0;
unsigned long lastSampleTime = 0;
const char* currentLabel = "diam";
bool isLogging = true;

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

void setupMPU6050() {
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

void setup() {
  Serial.begin(115200);
  delay(1000);

  Wire.begin(21, 22, static_cast<uint32_t>(100000));
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
  lastSampleTime = startTimestamp;
  lastSensorAttempt = startTimestamp;
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
  if (!isLogging) return;
  if (mpuAddress == 0) {
    if (currentMillis - lastSensorAttempt >= SENSOR_RETRY_INTERVAL_MS) {
      lastSensorAttempt = currentMillis;
      setupMPU6050();
      lastSampleTime = millis();
    }
    return;
  }
  if (currentMillis - lastSampleTime < SAMPLING_PERIOD_MS) return;
  lastSampleTime = currentMillis;

  float ax, ay, az, gx, gy, gz;
  if (!readMPU6050(ax, ay, az, gx, gy, gz)) {
    mpuAddress = 0;
    lastSensorAttempt = currentMillis;
    Serial.println("# MPU_ERROR: Pembacaan I2C gagal atau ketiga sumbu akselerasi nol.");
    return;
  }
  // Metadata contoh untuk Serial Monitor. record_dataset.py memakai isian operator.
  Serial.printf("%lu,S01,1,pergelangan,%.4f,%.4f,%.4f,%.2f,%.2f,%.2f,%s\n",
                currentMillis - startTimestamp, ax, ay, az, gx, gy, gz, currentLabel);
}
