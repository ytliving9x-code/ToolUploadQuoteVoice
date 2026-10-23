import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Đảm bảo đường dẫn module
sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.voice_service import synthesize_voice
from modules.video_composer import compose_quote_video

def test_full_pipeline():
    print("🚀 Bắt đầu kiểm thử quy trình tạo Video Quote Kèm Voice...")

    quote_text = "Hành trình vạn dặm luôn bắt đầu bằng một bước chân đầu tiên."
    voice_name = "Charon"
    bg_img = Path("assets/backgrounds/default_night.jpg")
    output_vid = Path("output/test_quote_voice.mp4")

    # 1. Tạo voice
    print("1. Đang tạo giọng đọc với Gemini TTS...")
    voice_file, voice_dur = synthesize_voice(
        text=quote_text,
        voice_name=voice_name,
        output_path="temp/test_voice.wav"
    )
    print(f"✔ Đã tạo voice: {voice_file} (Thời lượng: {voice_dur}s)")

    # 2. Ghép video hoàn chỉnh
    print("2. Đang render video với FFmpeg...")
    bgm_file = "assets/bgm/lofi_ambient.m4a" if Path("assets/bgm/lofi_ambient.m4a").exists() else None
    vid_path = compose_quote_video(
        bg_media_path=bg_img,
        quote=quote_text,
        voice_wav_path=voice_file,
        output_path=output_vid,
        duration_mode="dynamic",
        signature="@quote_channel",
        bgm_path=bgm_file,
        bgm_volume=0.14
    )

    print(f"🎉 RENDER HOÀN TẤT THÀNH CÔNG: {vid_path}")
    print(f"Dung lượng: {vid_path.stat().st_size} bytes")

if __name__ == "__main__":
    test_full_pipeline()
