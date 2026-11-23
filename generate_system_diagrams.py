import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Set font and style
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10

# ==========================================
# Gambar 5: Diagram Arsitektur Edge AI End-to-End
# ==========================================
fig, ax = plt.subplots(figsize=(12, 6.5))
ax.set_xlim(0, 12)
ax.set_ylim(0, 7)
ax.axis('off')

# Styling boxes
box_kw = dict(boxstyle='round,pad=0.5', facecolor='#e8f4f8', edgecolor='#1f77b4', lw=2)
edge_kw = dict(boxstyle='round,pad=0.5', facecolor='#eafaf1', edgecolor='#2ca02c', lw=2)
cloud_kw = dict(boxstyle='round,pad=0.5', facecolor='#fef9e7', edgecolor='#f39c12', lw=2)
user_kw = dict(boxstyle='round,pad=0.5', facecolor='#fbeee6', edgecolor='#e74c3c', lw=2)

# 1. Sensing Layer
ax.text(1.6, 5.5, 'Sensing Layer\nSensor MPU-6050\n- Akselerometer 3-Sumbu\n- Sampling 50 Hz (20 ms)\n- Bus I2C (SDA:21, SCL:22)', 
        ha='center', va='center', bbox=box_kw, fontsize=9.5, fontweight='bold')

# 2. Edge Device (ESP32)
ax.text(5.2, 5.5, 'Edge Computing Layer (ESP32)\n- Ring Buffer W=64 (1.28 detik)\n- Ekstraksi 20 Fitur Statistik\n- Normalisasi Z-Score (MU, SD)\n- Inferensi MLP (20->16->8->3)\n- Latensi Inferensi: < 0.25 ms', 
        ha='center', va='center', bbox=edge_kw, fontsize=9.5, fontweight='bold')

# 3. Local Feedback
ax.text(1.6, 2.0, 'Local Feedback Layer\n- OLED 0.96 inch SSD1306 (I2C)\n  [Aktivitas, Conf %, Latensi]\n- Buzzer Aktif (GPIO 18)\n  [Pola Audio Diam/Jalan/Lari]', 
        ha='center', va='center', bbox=edge_kw, fontsize=9.5, fontweight='bold')

# 4. Cloud Platform
ax.text(8.8, 5.5, 'IoT Cloud Platform\niot.reslab-csub.cloud\n(ThingsBoard Architecture)\n- HTTP REST Telemetry API\n- Database & Timeseries Log\n- Live Telemetry Dashboard\n- Rule Engine & Alarm Chain', 
        ha='center', va='center', bbox=cloud_kw, fontsize=9.5, fontweight='bold')

# 5. User Notification
ax.text(8.8, 2.0, 'Notification Layer\nTelegram Messenger\n- Integrasi Telegram Bot API\n- Push Notification Real-Time\n- Peringatan Otomatis Aktivitas\n  Lari dan Transisi Gerak', 
        ha='center', va='center', bbox=user_kw, fontsize=9.5, fontweight='bold')

# Arrows
arrow_kw = dict(arrowstyle='->', lw=2.2, color='#333333')
# Sensing -> ESP32
ax.annotate('', xy=(3.6, 5.5), xytext=(2.8, 5.5), arrowprops=arrow_kw)
ax.text(3.2, 5.75, 'I2C Bus', fontsize=8.5, ha='center', fontweight='bold')

# ESP32 -> Local Feedback
ax.annotate('', xy=(3.1, 2.7), xytext=(4.3, 4.3), arrowprops=arrow_kw)
ax.text(3.3, 3.7, 'Display & Buzzer', fontsize=8.5, ha='center', rotation=-40, fontweight='bold')

# ESP32 -> Cloud Platform
ax.annotate('', xy=(7.3, 5.5), xytext=(6.7, 5.5), arrowprops=dict(arrowstyle='->', lw=2.2, color='#1f77b4'))
ax.text(7.0, 5.75, 'Wi-Fi / HTTPS', fontsize=8.5, ha='center', color='#1f77b4', fontweight='bold')

# Cloud Platform -> Notification
ax.annotate('', xy=(8.8, 3.3), xytext=(8.8, 4.3), arrowprops=dict(arrowstyle='->', lw=2.2, color='#e74c3c'))
ax.text(9.2, 3.8, 'Rule Chain Trigger\n(Telegram API)', fontsize=8.5, ha='left', color='#e74c3c', fontweight='bold')

plt.title('Arsitektur Sistem Klasifikasi Aktivitas Manusia Berbasis Edge-to-Cloud IoT', fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig('images/gambar5_diagram_arsitektur_edge_iot.png', dpi=300)
plt.close()
print('Gambar 5 saved successfully.')

# ==========================================
# Gambar 6: Skema Pengkabelan Hardware ESP32
# ==========================================
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.set_xlim(0, 10)
ax.set_ylim(0, 6)
ax.axis('off')

esp_box = dict(boxstyle='square,pad=0.8', facecolor='#2c3e50', edgecolor='#1a252f')
sensor_box = dict(boxstyle='round,pad=0.5', facecolor='#3498db', edgecolor='#2980b9')
oled_box = dict(boxstyle='round,pad=0.5', facecolor='#9b59b6', edgecolor='#8e44ad')
buzzer_box = dict(boxstyle='round,pad=0.5', facecolor='#e67e22', edgecolor='#d35400')

ax.text(4.5, 3.0, 'ESP32\nNodeMCU / DevKit\n(SRAM 512KB, 240MHz)\n\n- 3V3\n- GND\n- GPIO 21 (SDA)\n- GPIO 22 (SCL)\n- GPIO 18 (Buzzer)', 
        ha='center', va='center', bbox=esp_box, fontsize=10, fontweight='bold', color='white')

ax.text(1.2, 4.5, 'Sensor MPU-6050\n(IMU 6-DOF)\n- VCC -> 3V3\n- GND -> GND\n- SDA -> GPIO 21\n- SCL -> GPIO 22', 
        ha='center', va='center', bbox=sensor_box, fontsize=9.5, fontweight='bold', color='white')

ax.text(1.2, 1.5, 'OLED SSD1306\n(0.96 inch 128x64 I2C)\n- VCC -> 3V3\n- GND -> GND\n- SDA -> GPIO 21\n- SCL -> GPIO 22', 
        ha='center', va='center', bbox=oled_box, fontsize=9.5, fontweight='bold', color='white')

ax.text(8.5, 3.0, 'Buzzer Aktif\n- Pin (+) -> GPIO 18\n- Pin (-) -> GND\n(Indikator Audio Gerak)', 
        ha='center', va='center', bbox=buzzer_box, fontsize=9.5, fontweight='bold', color='white')

# Wiring annotations
ax.annotate('', xy=(3.2, 3.8), xytext=(2.3, 4.5), arrowprops=dict(arrowstyle='<->', lw=2.2, color='#2980b9'))
ax.annotate('', xy=(3.2, 2.2), xytext=(2.3, 1.5), arrowprops=dict(arrowstyle='<->', lw=2.2, color='#8e44ad'))
ax.annotate('', xy=(7.3, 3.0), xytext=(5.8, 3.0), arrowprops=dict(arrowstyle='->', lw=2.2, color='#e67e22'))

plt.title('Skema Pengkabelan Antarmuka Hardware ESP32, MPU-6050, OLED, dan Buzzer', fontsize=12, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig('images/gambar6_skema_pengkabelan_dan_hardware.png', dpi=300)
plt.close()
print('Gambar 6 saved successfully.')

# ==========================================
# Gambar 7: Ilustrasi OLED, dasbor, dan notifikasi
# ==========================================
fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.6))

# Subplot 1: Tampilan Layar OLED SSD1306
axes[0].add_patch(patches.Rectangle((0, 0), 128, 64, facecolor='#101820', edgecolor='none'))
axes[0].set_xlim(0, 128)
axes[0].set_ylim(0, 64)
axes[0].axis('off')
axes[0].text(64, 54, '--- EDGE AI HAR ---', color='yellow', ha='center', fontsize=9, fontweight='bold')
axes[0].text(64, 38, 'AKTIF: LARI', color='cyan', ha='center', fontsize=14, fontweight='bold')
axes[0].text(64, 22, 'Conf: 99.2% | Lat: 215 us', color='white', ha='center', fontsize=8)
axes[0].text(64, 8, 'WiFi: OK | Cloud: Sent 200', color='lightgreen', ha='center', fontsize=7.5)
axes[0].set_title('Antarmuka Edge (OLED SSD1306)', fontsize=11, fontweight='bold')

# Subplot 2: ThingsBoard Telemetry Widget
time_pts = np.arange(12)
act_vals = [0, 0, 0, 1, 1, 1, 2, 2, 2, 1, 0, 0] # 0=diam, 1=jalan, 2=lari
axes[1].step(time_pts, act_vals, where='post', color='#1f77b4', lw=2.5)
axes[1].set_yticks([0, 1, 2])
axes[1].set_yticklabels(['Diam', 'Jalan', 'Lari'])
axes[1].set_xlabel('Sampel Waktu Telemetri (Detik)')
axes[1].set_title('Dashboard Telemetri Cloud ResLab', fontsize=11, fontweight='bold')
axes[1].grid(True, linestyle='--', alpha=0.6)

# Subplot 3: Notifikasi Telegram
axes[2].set_facecolor('#edf2f7')
axes[2].set_xlim(0, 10)
axes[2].set_ylim(0, 10)
axes[2].axis('off')
msg_box = dict(boxstyle='round,pad=0.6', facecolor='#ffffff', edgecolor='#cbd5e0', lw=1.5)
msg_text = (
    'RESLAB IoT Bot [Alert]\n'
    '-----------------------------------\n'
    'Notifikasi Aktivitas Pengguna!\n'
    'Perangkat : ESP32-HAR-01\n'
    'Status    : LARI (Running)\n'
    'Confidence: 99.2%\n'
    'Waktu     : 07:45:12 WIB\n'
    'Catatan   : Hentakan kaki tinggi terdeteksi!'
)
axes[2].text(5, 5, msg_text, ha='center', va='center', bbox=msg_box, fontsize=8.5, family='monospace')
axes[2].set_title('Notifikasi Real-Time (Telegram Bot)', fontsize=11, fontweight='bold')

plt.suptitle('Ilustrasi OLED, Dasbor Telemetri, dan Notifikasi', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig('images/gambar7_hasil_uji_langsung_dan_dashboard.png', dpi=300)
plt.close()
print('Gambar 7 saved successfully.')
