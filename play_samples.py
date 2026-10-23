import os
import sys
import time
import winsound
from pathlib import Path

# Đảm bảo in tiếng Việt trên console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

samples = [
    ("Charon", "samples/01_Charon_Nam_TramDay.wav", "1. Giọng NAM TRẦM DÀY (Charon) - Lãnh đạo, triết lý kinh doanh"),
    ("Kore",   "samples/02_Kore_Nu_TramAm.wav",    "2. Giọng NỮ TRẦM ẤM (Kore) - Sâu lắng, truyền cảm, tâm sự"),
    ("Aoede",  "samples/03_Aoede_Nu_NheNhang.wav", "3. Giọng NỮ NHẸ NHÀNG (Aoede) - Thơ ca, chữa lành, bình yên"),
    ("Fenrir", "samples/04_Fenrir_Nam_HaoSang.wav", "4. Giọng NAM HÀO SẢNG (Fenrir) - Động lực, thể thao, ý chí"),
    ("Puck",   "samples/05_Puck_Nam_TuoiSang.wav",  "5. Giọng NAM TƯƠI SÁNG (Puck) - Trẻ trung, đời thường, vui vẻ")
]

print("=" * 60)
print("🎧 ĐANG PHÁT LẦN LƯỢT 5 GIỌNG ĐỌC MẪU QUA LOA CỦA BẠN")
print("📝 Câu: 'Hành trình vạn dặm luôn bắt đầu bằng một bước chân đầu tiên.'")
print("=" * 60)

for voice_name, file_path, desc in samples:
    path = Path(file_path).resolve()
    if path.exists():
        print(f"\n🔊 >>> ĐANG PHÁT: {desc}")
        winsound.PlaySound(str(path), winsound.SND_FILENAME)
        time.sleep(1.2) # Khoảng nghỉ ngắn giữa các giọng
    else:
        print(f"❌ Không tìm thấy file: {file_path}")

print("\n" + "=" * 60)
print("✅ ĐÃ PHÁT XONG TẤT CẢ 5 MẪU GIỌNG!")
print("👉 Bạn thấy giọng nào hợp với kênh video Quote của mình nhất?")
print("=" * 60)
