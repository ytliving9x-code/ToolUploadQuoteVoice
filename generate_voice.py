import os
import sys
import wave
import argparse
from pathlib import Path

# Đảm bảo in tiếng Việt mượt mà trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Thử import google-genai
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ Chưa cài đặt thư viện 'google-genai'.")
    print("👉 Hãy chạy lệnh: pip install google-genai")
    sys.exit(1)


def generate_voice(
    text: str,
    output_path: str = "output_charon.wav",
    api_key: str = None,
    voice_name: str = "Charon",
    model_name: str = "gemini-3.8-flash-tts",
    play_audio: bool = True
):
    """
    Tạo file giọng đọc từ Gemini API với giọng đọc Charon (hoặc tùy chọn khác).
    """
    # Lấy API Key từ tham số, biến môi trường hoặc file .env
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key and os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip("\"'")
                    break

    if not key:
        print("❌ LỖI: Chưa có Gemini API Key!")
        print("💡 Cách khắc phục:")
        print("   1. Tạo file .env và thêm dòng: GEMINI_API_KEY=AIzaSy...")
        print("   2. Hoặc truyền trực tiếp: python generate_voice.py --key AIzaSy... \"Nội dung câu nói\"")
        print("   3. Hoặc đặt biến môi trường: set GEMINI_API_KEY=AIzaSy...")
        sys.exit(1)

    print(f"🎙️ Đang kết nối Gemini API...")
    print(f"🗣️ Giọng đọc: {voice_name} (Nam trầm, phát thanh viên)")
    print(f"📝 Nội dung: \"{text}\"")

    client = genai.Client(api_key=key)

    # Cấu hình giọng đọc và định dạng âm thanh
    config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name
                )
            )
        ),
    )

    # Tự động điều chỉnh phong cách đọc phù hợp với từng chất giọng
    voice_lower = voice_name.lower()
    if voice_lower in ["kore", "leda", "zephyr"]:
        style_desc = "chất giọng nữ trầm ấm, sâu lắng, truyền cảm, rõ ràng và ngắt nghỉ tự nhiên"
    elif voice_lower in ["aoede", "despina"]:
        style_desc = "chất giọng nữ nhẹ nhàng, trong trẻo, êm dịu, thư thái và ngắt nghỉ tự nhiên"
    elif voice_lower in ["fenrir", "orus"]:
        style_desc = "chất giọng nam mạnh mẽ, hào sảng, dứt khoát, truyền động lực và uy lực"
    elif voice_lower in ["puck"]:
        style_desc = "chất giọng nam trẻ trung, tươi sáng, hoạt bát và gần gũi"
    else:  # Charon hoặc mặc định
        style_desc = "chất giọng nam trầm, phong thái đĩnh đạc, đằm thắm, truyền cảm hứng và uy quyền"

    prompt = (
        f"Hãy đọc đoạn văn sau bằng tiếng Việt với {style_desc}: \"{text}\""
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=text,
            config=config,
        )
    except Exception as e:
        print(f"❌ Lỗi khi gọi Gemini API: {e}")
        return False

    # Trích xuất dữ liệu âm thanh
    audio_bytes = None
    for candidate in response.candidates:
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    audio_bytes = part.inline_data.data
                    break

    if not audio_bytes:
        print("❌ Không nhận được dữ liệu âm thanh từ Gemini. Vui lòng thử lại.")
        return False

    # Lưu thành file WAV chuẩn 24kHz Mono 16-bit
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)      # Mono
        wf.setsampwidth(2)      # 16-bit
        wf.setframerate(24000)  # Tần số 24000Hz chuẩn của Gemini Audio
        wf.writeframes(audio_bytes)

    abs_path = Path(output_path).resolve()
    print(f"✅ Đã tạo thành công file âm thanh!")
    print(f"📁 Vị trí lưu: {abs_path}")

    # Tự động phát âm thanh nếu được yêu cầu
    if play_audio:
        try:
            print("🔊 Đang phát âm thanh...")
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(str(abs_path), winsound.SND_FILENAME)
        except Exception as e:
            print(f"⚠️ Không thể tự phát âm thanh: {e}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tạo giọng đọc tiếng Việt từ Gemini API (Giọng Charon)")
    parser.add_argument("text", nargs="?", default="Hành trình vạn dặm luôn bắt đầu bằng một bước chân đầu tiên.", help="Câu văn/quote cần đọc")
    parser.add_argument("-o", "--output", default="output_charon.wav", help="Tên file WAV đầu ra (mặc định: output_charon.wav)")
    parser.add_argument("-k", "--key", default=None, help="Gemini API Key của bạn")
    parser.add_argument("-v", "--voice", default="Charon", help="Tên giọng đọc (mặc định: Charon)")
    parser.add_argument("--no-play", action="store_true", help="Không tự động phát âm thanh sau khi tạo")

    args = parser.parse_args()
    generate_voice(
        text=args.text,
        output_path=args.output,
        api_key=args.key,
        voice_name=args.voice,
        
        play_audio=not args.no_play
    )
