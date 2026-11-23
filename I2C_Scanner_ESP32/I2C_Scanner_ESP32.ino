/*
 * ======================================================================================
 * SKETCH I2C SCANNER UNTUK ESP32
 * Digunakan untuk mengecek apakah Sensor MPU-6050 dan OLED terdeteksi dengan benar
 * ======================================================================================
 * Pin Default ESP32:
 *   SDA : GPIO 21
 *   SCL : GPIO 22
 * ======================================================================================
 */

#include <Wire.h>

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- MEMULAI I2C SCANNER ESP32 ---");
  Wire.begin(21, 22);
}

void loop() {
  byte error, address;
  int nDevices = 0;

  Serial.println("\nMemindai bus I2C...");

  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0) {
      Serial.print("-> Perangkat I2C DITEMUKAN pada alamat 0x");
      if (address < 16) Serial.print("0");
      Serial.print(address, HEX);

      if (address == 0x68) {
        Serial.print(" (Sensor MPU-6050 OK!)");
      } else if (address == 0x69) {
        Serial.print(" (Sensor MPU-6050 Alamat Alternatif 0x69, hubungkan AD0 ke GND)");
      } else if (address == 0x3C || address == 0x3D) {
        Serial.print(" (Layar OLED SSD1306 OK!)");
      }
      Serial.println();
      nDevices++;
    } else if (error == 4) {
      Serial.print("Error tidak diketahui pada alamat 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
    }
  }

  if (nDevices == 0) {
    Serial.println("[PERINGATAN] Tidak ada perangkat I2C yang terdeteksi!");
    Serial.println("Solusi:");
    Serial.println("  1. Periksa kabel SDA (harus ke GPIO 21).");
    Serial.println("  2. Periksa kabel SCL (harus ke GPIO 22).");
    Serial.println("  3. Pastikan kabel VCC (ke 3.3V) dan GND tersambung kencang.");
  } else {
    Serial.print("Pemindaian selesai. Ditemukan ");
    Serial.print(nDevices);
    Serial.println(" perangkat.");
  }

  delay(4000); // Ulangi setiap 4 detik
}
