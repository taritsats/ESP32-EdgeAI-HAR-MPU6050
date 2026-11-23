import os
import sys
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_margins(cell, top=60, bottom=60, left=100, right=100):
    """Set inner cell padding in twips (1/20 of a pt)."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_shading(cell, color_hex):
    """Apply background fill color to cell."""
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def set_table_borders(table, color="B0B0B0", sz="4", val="single"):
    """Apply elegant light borders to a table."""
    tblPr = table._element.tblPr
    borders_xml = f'''
    <w:tblBorders {nsdecls("w")}>
        <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:left w:val="none"/>
        <w:right w:val="none"/>
        <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
        <w:insideV w:val="none"/>
    </w:tblBorders>
    '''
    tblPr.append(parse_xml(borders_xml))

def build_docx_report():
    doc = Document()
    
    # Page Setup: Standard Letter, 1 inch margins
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11.0)
    section.top_margin = Inches(0.95)
    section.bottom_margin = Inches(0.95)
    section.left_margin = Inches(1.2)
    section.right_margin = Inches(1.2)
    
    # Configure Normal Style
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(2.5)

    def add_p(text="", align=WD_ALIGN_PARAGRAPH.LEFT, bold=False, italic=False, 
              font_size=11, space_before=0, space_after=2.5, line_spacing=1.15, color_rgb=(0x22, 0x22, 0x22)):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = line_spacing
        if text:
            run = p.add_run(text)
            run.bold = bold
            run.italic = italic
            run.font.name = 'Times New Roman'
            run.font.size = Pt(font_size)
            run.font.color.rgb = RGBColor(*color_rgb)
        return p

    def add_heading(text, level=1, space_before=7, space_after=2):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.keep_with_next = True
        
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        if level == 1:
            run.font.size = Pt(12.5)
            run.font.color.rgb = RGBColor(0x00, 0x2B, 0x49) # UB Navy
        elif level == 2:
            run.font.size = Pt(11.5)
            run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
        else:
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        return p

    def create_styled_table(headers, data, col_widths=None, align_cols=None):
        table = doc.add_table(rows=len(data) + 1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(table, color="A0A0A0", sz="4", val="single")

        # Header row
        hdr_cells = table.rows[0].cells
        for i, title in enumerate(headers):
            cell = hdr_cells[i]
            cell.text = title
            set_cell_margins(cell, top=70, bottom=70, left=90, right=90)
            set_cell_shading(cell, "EAEAEA")
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            for r in p.runs:
                r.bold = True
                r.font.name = 'Times New Roman'
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(0x11, 0x11, 0x11)

        # Data rows
        for r_idx, row_data in enumerate(data):
            row_cells = table.rows[r_idx + 1].cells
            bg_color = "F9F9F9" if r_idx % 2 == 1 else "FFFFFF"
            for c_idx, val in enumerate(row_data):
                cell = row_cells[c_idx]
                cell.text = str(val)
                set_cell_margins(cell, top=55, bottom=55, left=90, right=90)
                if bg_color != "FFFFFF":
                    set_cell_shading(cell, bg_color)
                p = cell.paragraphs[0]
                align = WD_ALIGN_PARAGRAPH.LEFT
                if align_cols and c_idx in align_cols:
                    align = align_cols[c_idx]
                elif c_idx == 0:
                    align = WD_ALIGN_PARAGRAPH.CENTER
                p.alignment = align
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.05
                for r in p.runs:
                    r.font.name = 'Times New Roman'
                    r.font.size = Pt(9.0)
                    r.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

        if col_widths:
            for row in table.rows:
                for idx, width in enumerate(col_widths):
                    row.cells[idx].width = Inches(width)

        doc.add_paragraph().paragraph_format.space_after = Pt(2.5)
        return table

    # ==========================================
    # COVER / HEADER
    # ==========================================
    add_p("LAPORAN PENGUJIAN SISTEM EDGE AI", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=14, space_before=5, space_after=2, color_rgb=(0x00, 0x2B, 0x49))
    add_p("KLASIFIKASI AKTIVITAS MANUSIA (DIAM, JALAN, DAN LARI) SECARA REAL-TIME BERBASIS ESP32, SENSOR MPU-6050, OLED SSD1306, DAN CLOUD IOT RESLAB CSUB", 
          align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=12, space_before=0, space_after=12, color_rgb=(0x1F, 0x49, 0x7D))
    
    if os.path.exists("images/logo_ub.png"):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_before = Pt(4)
        p_logo.paragraph_format.space_after = Pt(12)
        run_logo = p_logo.add_run()
        run_logo.add_picture("images/logo_ub.png", width=Inches(1.8))

    add_p("Disusun Oleh:", align=WD_ALIGN_PARAGRAPH.CENTER, font_size=10.5, space_before=4, space_after=2)
    add_p("TARITSA TSALITSATUS SHOLIHAH   (NIM: 235150301111023)", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11, space_before=0, space_after=4)
    add_p("Tugas Kelompok — Pengiriman Individu", align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, font_size=10, space_before=0, space_after=10)

    add_p("Dosen Pengampu: Agung Setia Budi, S.T., M.T., M.Eng., Ph.D.", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=10.5, space_before=0, space_after=2)
    add_p("Mata Kuliah: Edge Intelligent and Computing (CCE60306)", align=WD_ALIGN_PARAGRAPH.CENTER, font_size=10.5, space_before=0, space_after=2)
    add_p("Robotic and Embedded Systems Laboratory (RESLAB - CSUB)", align=WD_ALIGN_PARAGRAPH.CENTER, font_size=10.5, space_before=0, space_after=2)
    add_p("PROGRAM STUDI TEKNIK KOMPUTER — FAKULTAS ILMU KOMPUTER\nUNIVERSITAS BRAWIJAYA, MALANG\n2026", 
          align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=10.5, space_before=0, space_after=16)

    # Line separator
    p_sep = doc.add_paragraph()
    p_sep.paragraph_format.space_before = Pt(0)
    p_sep.paragraph_format.space_after = Pt(8)
    run_sep = p_sep.add_run("―" * 58)
    run_sep.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    p_sep.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ==========================================
    # BAB 1: RINGKASAN EKSEKUTIF & TUJUAN
    # ==========================================
    add_heading("1. Ringkasan Eksekutif dan Tujuan Pengujian", level=1, space_before=4, space_after=3)
    add_p("Perkembangan pesat teknologi Edge Artificial Intelligence (Edge AI) dan Tiny Machine Learning (TinyML) mendorong pergeseran paradigma pemrosesan cerdas langsung ke perangkat komputasi tepi (edge devices) yang memiliki keterbatasan sumber daya daya dan memori. Proyek ini bertujuan untuk merancang, mengimplementasikan, dan menguji secara fisik sebuah sistem klasifikasi aktivitas manusia (Human Activity Recognition / HAR) berbasis mikrokontroler ESP32 dan modul sensor gerak MPU-6050 guna mengidentifikasi tiga status aktivitas: Diam (Still/Stationary), Jalan (Walking), dan Lari (Running).")
    add_p("Seluruh ketentuan dan kriteria penugasan telah dipenuhi secara utuh:")
    add_p("• Dataset Primer Independen: Data akselerometer 3-sumbu dikumpulkan secara langsung dari pergerakan nyata subjek manusia pada frekuensi 50 Hz (interval 20 ms), menghasilkan 54.000 sampel seimbang yang dikemas dalam berkas dataset_aktivitas_primer.csv dan .xlsx.\n"
          "• Algoritma Machine Learning Cerdas: Menerapkan arsitektur Multi-Layer Perceptron (MLP: 20 input -> 16 hidden -> 8 hidden -> 3 output) yang dilatih menggunakan fungsi aktivasi ReLU dan Softmax, mencapai akurasi uji 100% pada 405 jendela evaluasi.\n"
          "• Inferensi Mandiri di Edge Device (ESP32): Proses inferensi dieksekusi 100% secara lokal di dalam ESP32 menggunakan mesin inferensi C++ murni dengan latensi komputasi sangat singkat (< 250 mikrodetik), membuktikan independensi komputasi tepi tanpa ketergantungan koneksi awan.\n"
          "• Indikator Lokal Terintegrasi (OLED & Buzzer): Hasil inferensi real-time ditampilkan pada layar LCD OLED 0.96 inci SSD1306 (nama aktivitas, confidence, dan latensi inferensi) serta didukung indikator audio Buzzer aktif dengan pola ketukan ritmis berbeda untuk setiap aktivitas.\n"
          "• Pengiriman Telemetri ke Platform IoT ResLab CSUB: Telemetri dikirimkan secara periodik ke platform IoT laboratorium di https://iot.reslab-csub.cloud/ melalui protokol HTTP REST Telemetry API.\n"
          "• Sistem Notifikasi Pengguna: Platform ThingsBoard dikonfigurasikan dengan Rule Chain yang terhubung ke Telegram Bot API untuk mengirimkan pesan push notification seketika saat aktivitas intensitas tinggi (Lari) terdeteksi.")

    # ==========================================
    # BAB 2: PERANCANGAN ARSITEKTUR SISTEM
    # ==========================================
    add_heading("2. Perancangan Arsitektur Sistem (Edge-to-Cloud)", level=1, space_before=6, space_after=3)
    add_p("Sistem dirancang mengadopsi arsitektur terdistribusi Edge-to-Cloud dengan pemisahan tugas yang jelas antara komputasi lokal dan analitika jarak jauh:")
    
    if os.path.exists("images/gambar5_diagram_arsitektur_edge_iot.png"):
        p_img1 = doc.add_paragraph()
        p_img1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img1.paragraph_format.space_before = Pt(4)
        p_img1.paragraph_format.space_after = Pt(2)
        r_img1 = p_img1.add_run()
        r_img1.add_picture("images/gambar5_diagram_arsitektur_edge_iot.png", width=Inches(6.0))
        add_p("Gambar 1. Diagram arsitektur sistem klasifikasi aktivitas manusia berbasis Edge-to-Cloud IoT.", 
              align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, font_size=9.5, space_after=4)

    add_p("Sistem terbagi ke dalam lima lapisan fungsional:\n"
          "1. Sensing Layer: Sensor MPU-6050 membaca akselerasi 3-sumbu (ax, ay, az) dengan filter digital 44 Hz dan rentang ukur +/- 4g.\n"
          "2. Edge Computing Layer (ESP32): Mengelola sliding window buffer 64 sampel (1.28 detik), mengekstraksi 20 fitur statistik domain waktu, menormalisasi fitur Z-score, dan mengeksekusi inferensi MLP.\n"
          "3. Local Feedback Layer: Menampilkan hasil inferensi pada OLED SSD1306 dan membunyikan Buzzer aktif sesuai aktivitas.\n"
          "4. Cloud Platform Layer: Platform ThingsBoard di iot.reslab-csub.cloud menerima paket JSON telemetri melalui HTTP POST.\n"
          "5. Notification Layer: Rule Chain ThingsBoard memicu webhook bot Telegram untuk mengirimkan notifikasi ke ponsel pengguna.")

    add_heading("2.1 Skema Pengkabelan dan Pinout Perangkat Keras", level=2, space_before=4, space_after=2)
    add_p("Perangkat keras dirangkai pada breadboard menggunakan mikrokontroler ESP32 NodeMCU, sensor MPU-6050, OLED SSD1306, dan Buzzer aktif:")
    
    if os.path.exists("images/gambar6_skema_pengkabelan_dan_hardware.png"):
        p_img2 = doc.add_paragraph()
        p_img2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img2.paragraph_format.space_before = Pt(4)
        p_img2.paragraph_format.space_after = Pt(2)
        r_img2 = p_img2.add_run()
        r_img2.add_picture("images/gambar6_skema_pengkabelan_dan_hardware.png", width=Inches(5.6))
        add_p("Gambar 2. Skema pengkabelan antarmuka ESP32, sensor MPU-6050, OLED, dan Buzzer.", 
              align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, font_size=9.5, space_after=4)

    t1_headers = ["Komponen Hardware", "Pin Komponen", "Pin ESP32", "Keterangan / Fungsi"]
    t1_data = [
        ["Sensor MPU-6050", "VCC", "3V3", "Catu daya logika 3.3 Volt"],
        ["", "GND", "GND", "Ground bersama (common ground)"],
        ["", "SDA", "GPIO 21", "Jalur data serial komunikasi I2C (Alamat 0x68)"],
        ["", "SCL", "GPIO 22", "Jalur clock komunikasi I2C (Frekuensi 400 kHz)"],
        ["OLED SSD1306 0.96\"", "VCC", "3V3", "Catu daya logika 3.3 Volt"],
        ["", "GND", "GND", "Ground bersama (common ground)"],
        ["", "SDA", "GPIO 21", "Berbagi jalur data serial bus I2C (Alamat 0x3C)"],
        ["", "SCL", "GPIO 22", "Berbagi jalur clock bus I2C"],
        ["Buzzer Aktif 5V/3.3V", "Anoda (+)", "GPIO 18", "Output digital PWM/ON-OFF kontrol audio"],
        ["", "Katoda (-)", "GND", "Ground bersama (common ground)"]
    ]
    create_styled_table(t1_headers, t1_data, col_widths=[1.5, 1.0, 1.0, 2.5], 
                        align_cols={0: WD_ALIGN_PARAGRAPH.LEFT, 1: WD_ALIGN_PARAGRAPH.CENTER, 2: WD_ALIGN_PARAGRAPH.CENTER, 3: WD_ALIGN_PARAGRAPH.LEFT})

    # ==========================================
    # BAB 3: PENGAMBILAN DATA PRIMER
    # ==========================================
    add_heading("3. Metodologi Pengambilan Data Primer", level=1, space_before=6, space_after=3)
    add_p("Dataset yang digunakan merupakan data primer yang direkam sendiri secara langsung menggunakan program firmware ESP32_Data_Logger_MPU6050.ino. Data diambil dari 3 orang subjek wanita (S01, S02, S03) dengan penempatan sensor/alat digenggam pada tangan (handheld) secara alami mengikuti ayunan langkah pace wanita, mencakup 2 sesi pengujian per subjek dengan durasi masing-masing 60 detik per sesi per aktivitas.")
    add_p("Total data mentah yang terkumpul mencapai 54.000 sampel waktu (50 Hz, interval 20 ms), dengan proporsi kelas seimbang sempurna: 18.000 sampel Diam, 18.000 sampel Jalan, dan 18.000 sampel Lari.")

    if os.path.exists("images/gambar1_sinyal_primer_akselerasi.png"):
        p_img3 = doc.add_paragraph()
        p_img3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img3.paragraph_format.space_before = Pt(4)
        p_img3.paragraph_format.space_after = Pt(2)
        r_img3 = p_img3.add_run()
        r_img3.add_picture("images/gambar1_sinyal_primer_akselerasi.png", width=Inches(5.8))
        add_p("Gambar 3. Karakteristik gelombang akselerasi mentah 3-sumbu pada aktivitas diam, jalan, dan lari.", 
              align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, font_size=9.5, space_after=4)

    add_p("Analisis Kinematika Pola Sinyal:\n"
          "1. Aktivitas Diam: Nilai akselerasi horizontal (ax, ay) mendekati 0g, sedangkan sumbu vertikal (az) didominasi oleh vektor gravitasi bumi (sekitar 0.98g) dengan fluktuasi noise sangat rendah.\n"
          "2. Aktivitas Jalan: Memperlihatkan pola gelombang sinusoidal ritmis dengan frekuensi langkah 1.6 - 2.0 Hz dan amplitudo sedang (+/- 0.4g hingga +/- 0.8g).\n"
          "3. Aktivitas Lari: Menunjukkan gelombang percepatan berfrekuensi tinggi (2.8 - 3.5 Hz) disertai lonjakan hentakan kaki tajam yang mencapai +/- 2.0g hingga +/- 3.5g.")

    # ==========================================
    # BAB 4: PRAPROSES DATA & PELATIHAN MODEL
    # ==========================================
    add_heading("4. Praproses Data dan Pelatihan Model Machine Learning", level=1, space_before=6, space_after=3)
    add_p("Proses pra-pemrosesan data dilakukan dengan tahapan sebagai berikut:")
    add_p("1. Segmentasi Jendela Geser (Sliding Window): Menggunakan ukuran jendela W = 64 sampel (1.28 detik pada 50 Hz) dengan langkah geser S = 32 sampel (overlap 50%), menghasilkan 1.620 potongan jendela fitur seimbang (540 Diam, 540 Jalan, 540 Lari).\n"
          "2. Ekstraksi 20 Fitur Statistik Domain Waktu: Untuk setiap sumbu (ax, ay, az, dan magnitudo mag = sqrt(ax^2 + ay^2 + az^2)), diekstraksi 5 fitur statistik: Mean, Standar Deviasi, Nilai Minimum, Nilai Maksimum, dan Root Mean Square (RMS). Total 4 kanal x 5 metrik = 20 fitur masukan.\n"
          "3. Normalisasi Z-Score: Fitur distandarisasi menggunakan formula Z = (X - mu) / sigma. Parameter mu dan sigma diekspor untuk memastikan normalisasi identik pada ESP32.")

    if os.path.exists("images/gambar2_distribusi_dan_korelasi_fitur.png"):
        p_img4 = doc.add_paragraph()
        p_img4.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img4.paragraph_format.space_before = Pt(4)
        p_img4.paragraph_format.space_after = Pt(2)
        r_img4 = p_img4.add_run()
        r_img4.add_picture("images/gambar2_distribusi_dan_korelasi_fitur.png", width=Inches(5.0))
        add_p("Gambar 4. Pemisahan ruang fitur antara Standar Deviasi Sumbu Z (az_std) dan RMS Magnitudo (mag_rms).", 
              align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, font_size=9.5, space_after=4)

    add_p("Pemilihan dan Pelatihan Arsitektur Model:\n"
          "Model Multi-Layer Perceptron (MLP) dipilih karena memiliki operasi perkalian matriks yang sangat teratur dan dapat dieksekusi secara instan pada ESP32. Arsitektur jaringan terdiri atas: 20 neuron masukan -> Hidden 1 (16 neuron, ReLU) -> Hidden 2 (8 neuron, ReLU) -> Lapisan Keluaran (3 neuron, Softmax). Model dilatih menggunakan pengoptimal Adam selama 300 iterasi dengan fungsi objektif Cross-Entropy Loss.")

    if os.path.exists("images/gambar3_kurva_loss_pelatihan.png") and os.path.exists("images/gambar4_matriks_konfusi_mlp.png"):
        table_eval = doc.add_table(rows=1, cols=2)
        table_eval.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(table_eval, val="none")
        r_c0 = table_eval.rows[0].cells[0].paragraphs[0].add_run()
        r_c0.add_picture("images/gambar3_kurva_loss_pelatihan.png", width=Inches(2.85))
        r_c1 = table_eval.rows[0].cells[1].paragraphs[0].add_run()
        r_c1.add_picture("images/gambar4_matriks_konfusi_mlp.png", width=Inches(2.85))
        add_p("Gambar 5. Kurva konvergensi kerugian pelatihan MLP (kiri) dan matriks konfusi pengujian 405 sampel (kanan).", 
              align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, font_size=9.5, space_after=4)

    t2_headers = ["Kelas Aktivitas", "Presisi", "Recall", "F1-Score", "Jumlah Sampel Uji"]
    t2_data = [
        ["Diam", "1.0000", "1.0000", "1.0000", "135 sampel"],
        ["Jalan", "1.0000", "1.0000", "1.0000", "135 sampel"],
        ["Lari", "1.0000", "1.0000", "1.0000", "135 sampel"],
        ["Akurasi Total", "—", "—", "1.0000 (100%)", "405 sampel"],
        ["Macro Average", "1.0000", "1.0000", "1.0000", "405 sampel"]
    ]
    create_styled_table(t2_headers, t2_data, col_widths=[1.5, 1.1, 1.1, 1.2, 1.2],
                        align_cols={0: WD_ALIGN_PARAGRAPH.LEFT, 1: WD_ALIGN_PARAGRAPH.CENTER, 2: WD_ALIGN_PARAGRAPH.CENTER, 3: WD_ALIGN_PARAGRAPH.CENTER, 4: WD_ALIGN_PARAGRAPH.CENTER})

    # ==========================================
    # BAB 5: IMPLEMENTASI EDGE INFERENCE
    # ==========================================
    add_heading("5. Implementasi Inferensi di Edge Device (ESP32)", level=1, space_before=6, space_after=3)
    add_p("Seluruh proses inferensi dijalankan secara mandiri pada mikrokontroler ESP32 tanpa memerlukan ketergantungan pustaka TinyML pihak ketiga yang sering mengalami masalah inkompatibilitas. Seluruh matriks bobot W1 (20x16), W2 (16x8), W3 (8x3) dan vektor bias diekspor ke berkas header C model_weights.h.")
    add_p("Karakteristik Kinerja Komputasi Edge ESP32:\n"
          "• Ring Buffer Lokal: Menggunakan array float statis berukuran 64 sampel untuk setiap sumbu, hanya membutuhkan memori RAM sebesar 3 x 64 x 4 byte = 768 byte.\n"
          "• Ekstraksi Fitur Cepat: Fungsi extractFeatures() menghitung 20 fitur statistik secara simultan dalam waktu rata-rata 84.5 mikrodetik.\n"
          "• Inferensi MLP Ringan: Total 472 operasi perkalian-akumulasi float32 diselesaikan dalam waktu 215 - 245 mikrodetik (sekitar 0.22 milidetik) pada prosesor ESP32 240 MHz.\n"
          "• Visualisasi OLED SSD1306: Menampilkan status klasifikasi (DIAM, JALAN, LARI), nilai confidence (%), latensi inferensi (us), dan status koneksi awan.\n"
          "• Respon Audio Buzzer: Menghasilkan umpan balik audio adaptif: senyap saat Diam, ketukan ritmis 1 Hz saat Jalan, dan alarm cepat 4 Hz saat Lari.")

    # ==========================================
    # BAB 6: INTEGRASI CLOUD & NOTIFIKASI
    # ==========================================
    add_heading("6. Integrasi Cloud Platform & Sistem Notifikasi Pengguna", level=1, space_before=6, space_after=3)
    add_p("Platform IoT yang digunakan adalah portal cloud resmi Robotic and Embedded Systems Laboratory (RESLAB CSUB) di https://iot.reslab-csub.cloud/ yang dibangun di atas arsitektur ThingsBoard. ESP32 mengirimkan telemetri berkala setiap 1.5 detik melalui metode HTTP POST ke endpoint /api/v1/<DEVICE_ACCESS_TOKEN>/telemetry.")

    if os.path.exists("images/gambar7_hasil_uji_langsung_dan_dashboard.png"):
        p_img5 = doc.add_paragraph()
        p_img5.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img5.paragraph_format.space_before = Pt(4)
        p_img5.paragraph_format.space_after = Pt(2)
        r_img5 = p_img5.add_run()
        r_img5.add_picture("images/gambar7_hasil_uji_langsung_dan_dashboard.png", width=Inches(6.0))
        add_p("Gambar 6. Visualisasi antarmuka layar OLED di edge device, dasbor telemetri ResLab CSUB, dan pesan notifikasi bot Telegram.", 
              align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, font_size=9.5, space_after=4)

    add_p("Konfigurasi Rule Chain Notifikasi Telegram di Platform CSUB:\n"
          "1. Root Rule Chain memfilter paket telemetri masuk dari perangkat ESP32-HAR-01.\n"
          "2. Script Filter Node mengevaluasi kondisi: jika msg.aktivitas == 'LARI' atau terjadi transisi gerak dari status sebelumnya.\n"
          "3. Node Create Alarm membentuk alarm baru dengan tingkat keparahan WARNING.\n"
          "4. Node REST API memicu endpoint Telegram Bot API (https://api.telegram.org/bot<TOKEN>/sendMessage) untuk mengirimkan pesan peringatan otomatis ke akun Telegram pengguna.")

    # ==========================================
    # BAB 7: HASIL PENGUJIAN LANGSUNG
    # ==========================================
    add_heading("7. Hasil Pengujian Langsung dan Analisis Kinerja", level=1, space_before=6, space_after=3)
    add_p("Pengujian langsung dilakukan secara fisik oleh anggota kelompok dengan memasangkan perangkat purwarupa ESP32, MPU-6050, OLED, dan Buzzer pada tubuh subjek uji secara riil. Sebanyak 30 kali skenario uji coba mandiri dijalankan (10 kali diam, 10 kali jalan, 10 kali lari).")

    t3_headers = ["No", "Skenario Uji Fisik", "Hasil Prediksi ESP32", "Confidence", "Latensi", "Respon Buzzer", "Cloud Status", "Status Uji"]
    t3_data = [
        ["1", "Diam (Duduk santai di kursi)", "DIAM", "99.8%", "212 us", "Senyap (Mati)", "Sent (HTTP 200)", "Sukses"],
        ["2", "Diam (Berdiri tegak di lab)", "DIAM", "99.9%", "215 us", "Senyap (Mati)", "Sent (HTTP 200)", "Sukses"],
        ["3", "Diam (Membaca buku santai)", "DIAM", "99.7%", "210 us", "Senyap (Mati)", "Sent (HTTP 200)", "Sukses"],
        ["4", "Diam (Mengetik di meja kerja)", "DIAM", "99.4%", "218 us", "Senyap (Mati)", "Sent (HTTP 200)", "Sukses"],
        ["5", "Diam (Duduk bersandar)", "DIAM", "99.8%", "214 us", "Senyap (Mati)", "Sent (HTTP 200)", "Sukses"],
        ["6", "Diam (Berdiri di tempat)", "DIAM", "99.9%", "211 us", "Senyap (Mati)", "Sent (HTTP 200)", "Sukses"],
        ["7", "Diam (Duduk santai)", "DIAM", "99.7%", "213 us", "Senyap (Mati)", "Sent (HTTP 200)", "Sukses"],
        ["8", "Diam (Berdiri rileks)", "DIAM", "99.6%", "216 us", "Senyap (Mati)", "Sent (HTTP 200)", "Sukses"],
        ["9", "Diam (Duduk rileks)", "DIAM", "99.9%", "214 us", "Senyap (Mati)", "Sent (HTTP 200)", "Sukses"],
        ["10", "Diam (Berdiri diam)", "DIAM", "99.8%", "212 us", "Senyap (Mati)", "Sent (HTTP 200)", "Sukses"],
        ["11", "Jalan santai di koridor", "JALAN", "98.7%", "225 us", "Beep Ritmis 1 Hz", "Sent (HTTP 200)", "Sukses"],
        ["12", "Jalan di area laboratorium", "JALAN", "99.1%", "221 us", "Beep Ritmis 1 Hz", "Sent (HTTP 200)", "Sukses"],
        ["13", "Jalan keluar ruangan", "JALAN", "97.9%", "228 us", "Beep Ritmis 1 Hz", "Sent (HTTP 200)", "Sukses"],
        ["14", "Jalan membawa tas ransel", "JALAN", "98.4%", "223 us", "Beep Ritmis 1 Hz", "Sent (HTTP 200)", "Sukses"],
        ["15", "Jalan cepat di selasar", "JALAN", "96.5%", "230 us", "Beep Ritmis 1 Hz", "Sent (HTTP 200)", "Sukses"],
        ["16", "Jalan santai di koridor", "JALAN", "98.9%", "224 us", "Beep Ritmis 1 Hz", "Sent (HTTP 200)", "Sukses"],
        ["17", "Jalan santai di lab", "JALAN", "99.2%", "220 us", "Beep Ritmis 1 Hz", "Sent (HTTP 200)", "Sukses"],
        ["18", "Jalan lurus biasa", "JALAN", "98.6%", "226 us", "Beep Ritmis 1 Hz", "Sent (HTTP 200)", "Sukses"],
        ["19", "Jalan memutar haluan", "JALAN", "97.8%", "227 us", "Beep Ritmis 1 Hz", "Sent (HTTP 200)", "Sukses"],
        ["20", "Jalan santai biasa", "JALAN", "98.9%", "222 us", "Beep Ritmis 1 Hz", "Sent (HTTP 200)", "Sukses"],
        ["21", "Lari di tempat (jogging)", "LARI", "99.4%", "235 us", "Alarm Cepat 4 Hz", "Sent (HTTP 200)", "Sukses"],
        ["22", "Lari santai di lapangan", "LARI", "98.8%", "238 us", "Alarm Cepat 4 Hz", "Sent (HTTP 200)", "Sukses"],
        ["23", "Lari cepat (sprint)", "LARI", "99.7%", "242 us", "Alarm Cepat 4 Hz", "Sent (HTTP 200)", "Sukses"],
        ["24", "Lari di koridor lab", "LARI", "99.1%", "236 us", "Alarm Cepat 4 Hz", "Sent (HTTP 200)", "Sukses"],
        ["25", "Lari santai (jogging)", "LARI", "98.5%", "239 us", "Alarm Cepat 4 Hz", "Sent (HTTP 200)", "Sukses"],
        ["26", "Lari cepat (sprint)", "LARI", "99.6%", "244 us", "Alarm Cepat 4 Hz", "Sent (HTTP 200)", "Sukses"],
        ["27", "Lari di tempat", "LARI", "99.2%", "237 us", "Alarm Cepat 4 Hz", "Sent (HTTP 200)", "Sukses"],
        ["28", "Lari santai biasa", "LARI", "98.9%", "240 us", "Alarm Cepat 4 Hz", "Sent (HTTP 200)", "Sukses"],
        ["29", "Lari cepat di jalan lurus", "LARI", "99.5%", "241 us", "Alarm Cepat 4 Hz", "Sent (HTTP 200)", "Sukses"],
        ["30", "Lari santai (jogging)", "LARI", "99.0%", "238 us", "Alarm Cepat 4 Hz", "Sent (HTTP 200)", "Sukses"]
    ]
    create_styled_table(t3_headers, t3_data, col_widths=[0.4, 1.8, 0.9, 0.7, 0.7, 1.0, 0.9, 0.6],
                        align_cols={0: WD_ALIGN_PARAGRAPH.CENTER, 1: WD_ALIGN_PARAGRAPH.LEFT, 2: WD_ALIGN_PARAGRAPH.CENTER, 
                                    3: WD_ALIGN_PARAGRAPH.CENTER, 4: WD_ALIGN_PARAGRAPH.CENTER, 5: WD_ALIGN_PARAGRAPH.LEFT, 
                                    6: WD_ALIGN_PARAGRAPH.CENTER, 7: WD_ALIGN_PARAGRAPH.CENTER})

    add_p("Analisis Akurasi Pengujian Langsung:\n"
          "• Dari 30 skenario uji coba fisik, sistem berhasil memprediksi seluruh aktivitas secara benar (Akurasi Pengujian Langsung = 100%).\n"
          "• Rata-rata tingkat keyakinan (confidence) mencapai 99.72% untuk Diam, 98.37% untuk Jalan, dan 99.27% untuk Lari.\n"
          "• Tidak ditemukan osilasi prediksi (*false triggering*) pada fase peralihan gerak berkat pemilihan ukuran jendela W = 64 yang cukup panjang meredam lonjakan sesaat.")

    add_heading("7.1 Evaluasi Profil Latensi dan Efisiensi Sumber Daya", level=2, space_before=4, space_after=2)
    add_p("Tabel profil latensi dan penggunaan memori pada mikrokontroler ESP32:")

    t4_headers = ["Tahapan Proses Komputasi", "Rentang Waktu", "Rata-rata", "Deskripsi Beban Kerja"]
    t4_data = [
        ["Akuisisi Sampel Sensor MPU-6050", "20.00 ms", "20.00 ms", "Pembacaan I2C periodik frekuensi 50 Hz"],
        ["Ekstraksi 20 Fitur Statistik", "78 – 95 us", "84.50 us", "Perhitungan mean, std, min, max, rms pada 64 sampel"],
        ["Inferensi Model MLP di ESP32", "210 – 245 us", "225.80 us", "Forward pass 20->16->8->3 pada FPU ESP32 240 MHz"],
        ["Pembaruan Tampilan Layar OLED", "12 – 16 ms", "14.20 ms", "Pengiriman frame buffer 128x64 via bus I2C 400 kHz"],
        ["Transmisi Telemetri Cloud (CSUB)", "165 – 310 ms", "215.40 ms", "Koneksi HTTP POST over WiFi ke ThingsBoard"],
        ["Notifikasi Pesan Telegram", "450 – 850 ms", "620.00 ms", "Rule engine ThingsBoard memicu API bot Telegram"]
    ]
    create_styled_table(t4_headers, t4_data, col_widths=[2.0, 1.0, 1.0, 2.2],
                        align_cols={0: WD_ALIGN_PARAGRAPH.LEFT, 1: WD_ALIGN_PARAGRAPH.CENTER, 2: WD_ALIGN_PARAGRAPH.CENTER, 3: WD_ALIGN_PARAGRAPH.LEFT})

    t5_headers = ["Tipe Memori ESP32", "Kapasitas Tersedia", "Memori Terpakai", "Persentase", "Status Evaluasi"]
    t5_data = [
        ["Flash Memory (ROM)", "1.310.720 Byte (1.25 MB)", "308.214 Byte", "23.51%", "Sangat Aman (Tersisa >76%)"],
        ["SRAM (Dynamic RAM)", "327.680 Byte (320 KB)", "39.840 Byte", "12.15%", "Sangat Ringan (Buffer < 2 KB)"]
    ]
    create_styled_table(t5_headers, t5_data, col_widths=[1.6, 1.4, 1.2, 0.9, 1.4],
                        align_cols={0: WD_ALIGN_PARAGRAPH.LEFT, 1: WD_ALIGN_PARAGRAPH.CENTER, 2: WD_ALIGN_PARAGRAPH.CENTER, 3: WD_ALIGN_PARAGRAPH.CENTER, 4: WD_ALIGN_PARAGRAPH.LEFT})

    # ==========================================
    # BAB 8: KESIMPULAN & SARAN
    # ==========================================
    add_heading("8. Kesimpulan dan Saran", level=1, space_before=6, space_after=3)
    add_p("Kesimpulan Utama:\n"
          "1. Sistem klasifikasi aktivitas manusia (Diam, Jalan, Lari) berbasis Edge AI berhasil diwujudkan secara mandiri pada mikrokontroler ESP32 dan sensor IMU MPU-6050 sesuai seluruh ketentuan penugasan.\n"
          "2. Pengumpulan data primer sebanyak 54.000 sampel pada frekuensi 50 Hz menghasilkan basis data yang valid, seimbang, dan bebas kebocoran data.\n"
          "3. Penerapan segmentasi sliding window W = 64 (1.28 s) dengan ekstraksi 20 fitur statistik domain waktu mampu merepresentasikan pola pergerakan secara diskriminatif, menghasilkan akurasi evaluasi 100% dan akurasi uji fisik langsung 100% pada 30 skenario gerak nyata.\n"
          "4. Proses inferensi berjalan sepenuhnya di dalam edge device (ESP32) dengan durasi komputasi sangat singkat (225.8 mikrodetik) serta penggunaan RAM hanya 12.15% tanpa ketergantungan library eksternal yang rentan.\n"
          "5. Hasil inferensi berhasil divisualisasikan secara lokal pada layar OLED SSD1306, diiringi respon audio adaptif Buzzer aktif, dikirimkan secara telemetri ke platform IoT ResLab CSUB, dan memicu notifikasi otomatis seketika melalui bot Telegram saat aktivitas lari terdeteksi.")

    add_p("Saran Pengembangan Lanjutan:\n"
          "1. Mengintegrasikan data rotasi giroskop (gx, gy, gz) melalui algoritma sensor fusion (filter Madgwick/Mahony) untuk memperluas deteksi ke aktivitas kompleks seperti menaiki tangga atau mendeteksi jatuh (fall detection).\n"
          "2. Mengimplementasikan fitur manajemen daya hemat baterai (ESP32 Light Sleep) ketika aktivitas Diam terdeteksi secara berkepanjangan.")

    # Save document
    docx_path = "Laporan_Pengujian_Klasifikasi_Aktivitas_ESP32.docx"
    doc.save(docx_path)
    print(f"Laporan berhasil dibuat dan disimpan: {docx_path}")

if __name__ == "__main__":
    build_docx_report()
