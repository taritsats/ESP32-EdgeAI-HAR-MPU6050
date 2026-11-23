import os
from PIL import Image, ImageDraw, ImageFont

# Load the original uploaded image
src_path = r'C:/Users/LUTHFI/.gemini/antigravity/brain/d3f79c01-ae61-46d8-a34a-b5564be1faa2/.user_uploaded/media_1795425644996_d058a8ed.jpg'
img = Image.open(src_path).convert('RGB')
draw = ImageDraw.Draw(img)

# Dimensions: 1024 x 768
# Let's draw clear visual guides:

# 1. Box around MPU-6050
# MPU-6050 is around x: 535-680, y: 410-520
draw.rectangle([535, 410, 680, 520], outline='#00FF00', width=4)
draw.text((540, 390), "SENSOR MPU-6050 (ONBOARD)", fill='#00FF00')

# 2. Box around JP 6050 (The key missing jumper!)
# JP 6050 is around x: 550-630, y: 550-620
draw.rectangle([545, 545, 635, 620], outline='#FF0000', width=5)
draw.text((430, 530), ">>> INI KUNCINYA (JP 6050) <<<", fill='#FF0000')

# 3. Box around JP OLED (Example of working jumpers)
# JP OLED is around x: 475-520, y: 280-350
draw.rectangle([475, 280, 520, 350], outline='#00FF00', width=4)
draw.text((360, 260), "JP OLED (Sudah Benar Ada Jumper Hitam)", fill='#00FF00')

# 4. Box around spare jumpers (JP BMP180 or JP MICROSD)
# JP BMP180 is around x: 695-750, y: 550-620
draw.rectangle([695, 550, 750, 620], outline='#FFA500', width=4)
draw.text((640, 630), "JP BMP180 (Bisa pinjam 2 jumper hitam di sini)", fill='#FFA500')

# Save annotated image
os.makedirs('TUGAS BESAR/images', exist_ok=True)
img.save('TUGAS BESAR/images/panduan_kabel_shield.png')
print('Annotated image saved: TUGAS BESAR/images/panduan_kabel_shield.png')
