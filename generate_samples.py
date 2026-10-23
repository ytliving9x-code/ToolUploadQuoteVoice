import os
import sys
from pathlib import Path

# Đảm bảo import được module trong thư mục hiện tại
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_voice import generate_voice

# Đảm bảo in tiếng Việt mượt mà trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SAMPLE_QUOTE = "Hành trình vạn dặm luôn bắt đầu bằng một bước chân đầu tiên."

VOICES_TO_TEST = [
    ("Charon", "samples/01_Charon_Nam_TramDay.wav", "Nam trầm dày, uy lực, phát thanh viên"),
    ("Kore",   "samples/02_Kore_Nu_TramAm.wav",    "Nữ trầm ấm, sâu lắng, truyền cảm"),
    ("Aoede",  "samples/03_Aoede_Nu_NheNhang.wav", "Nữ nhẹ nhàng, trong trẻo, thư thái"),
    ("Fenrir", "samples/04_Fenrir_Nam_HaoSang.wav", "Nam hào sảng, mạnh mẽ, tạo động lực"),
    ("Puck",   "samples/05_Puck_Nam_TuoiSang.wav",  "Nam tươi trẻ, hoạt bát, hiện đại"),
]

def main():
    os.makedirs("samples", exist_ok=True)
    print("=" * 60)
    print("🎯 BẮT ĐẦU TẠO CÁC MẪU GIỌNG ĐỌC ĐỂ BẠN LỰA CHỌN")
    print(f"📝 Câu trích dẫn: \"{SAMPLE_QUOTE}\"")
    print("=" * 60)

    for voice_name, output_path, desc in VOICES_TO_TEST:
        print(f"\n▶ Đang tạo: Giọng {voice_name} ({desc})...")
        success = generate_voice(
            text=SAMPLE_QUOTE,
            output_path=output_path,
            voice_name=voice_name,
            play_audio=False # tạo xong rồi sẽ phát lần lượt
        )
        if success:
            print(f"  ✔ Hoàn thành: {output_path}")

    print("\n" + "=" * 60)
    print("🎉 ĐÃ TẠO XONG TẤT CẢ CÁC MẪU GIỌNG!")
    print("=" * 60)

if __name__ == "__main__":
    main()
