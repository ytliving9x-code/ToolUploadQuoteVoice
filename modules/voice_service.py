import hashlib
import logging
import os
import sys
import wave
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger("quote_voice.voice_service")

# Danh mục các giọng đọc Gemini tiếng Việt tiêu chuẩn
AVAILABLE_VOICES: Dict[str, Dict[str, str]] = {
    "Charon": {
        "gender": "Nam",
        "title": "Charon (Nam Trầm Dày)",
        "tag": "⭐ Khuyên dùng cho Triết lý / Lãnh đạo",
        "desc": "Trầm ấm, uy lực, phong thái đĩnh đạc, phát thanh viên.",
        "prompt_style": "chất giọng nam trầm, phong thái đĩnh đạc, đằm thắm, truyền cảm hứng và uy quyền"
    },
    "Kore": {
        "gender": "Nữ",
        "title": "Kore (Nữ Trầm Ấm)",
        "tag": "⭐ Khuyên dùng cho Giọng Nữ",
        "desc": "Trầm ấm, sâu lắng, ngắt nghỉ tự nhiên như người thật tâm sự.",
        "prompt_style": "chất giọng nữ trầm ấm, sâu lắng, truyền cảm, rõ ràng và ngắt nghỉ tự nhiên"
    },
    "Aoede": {
        "gender": "Nữ",
        "title": "Aoede (Nữ Nhẹ Nhàng)",
        "tag": "Chữa lành & Thơ ca",
        "desc": "Trong trẻo, êm dịu, thư thái, mang lại cảm giác bình yên.",
        "prompt_style": "chất giọng nữ nhẹ nhàng, trong trẻo, êm dịu, thư thái và ngắt nghỉ tự nhiên"
    },
    "Fenrir": {
        "gender": "Nam",
        "title": "Fenrir (Nam Hào Sảng)",
        "tag": "Động lực & Ý chí",
        "desc": "Mạnh mẽ, dứt khoát, hào sảng, tràn đầy năng lượng bứt phá.",
        "prompt_style": "chất giọng nam mạnh mẽ, hào sảng, dứt khoát, truyền động lực và uy lực"
    },
    "Puck": {
        "gender": "Nam",
        "title": "Puck (Nam Tươi Trẻ)",
        "tag": "Hoạt bát & Đời thường",
        "desc": "Năng động, tươi sáng, vui vẻ, thích hợp video phong cách trẻ.",
        "prompt_style": "chất giọng nam trẻ trung, tươi sáng, hoạt bát và gần gũi"
    }
}


def get_gemini_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Tìm API Key từ tham số truyền vào, Streamlit secrets, biến môi trường hoặc file .env."""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()

    # 1. Kiểm tra Streamlit Cloud Secrets (st.secrets)
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
                return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    
    # 2. Kiểm tra biến môi trường
    key = os.environ.get("GEMINI_API_KEY")
    if key and key.strip():
        return key.strip()

    # 3. Kiểm tra file .env
    for candidate in [Path(".env"), Path("../.env"), Path("d:/ToolUploadQuoteVoice/.env")]:
        if candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY="):
                            k = line.split("=", 1)[1].strip("\"' ")
                            if k:
                                return k
            except Exception:
                pass
    return None


def get_audio_duration(file_path: Path | str) -> float:
    """Đo thời lượng chính xác của file WAV (tính bằng giây)."""
    p = Path(file_path)
    if not p.exists():
        return 0.0
    try:
        with wave.open(str(p), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return round(frames / float(rate), 2)
    except Exception as e:
        logger.warning(f"Không thể đo thời lượng WAV {p}: {e}")
        return 0.0


def synthesize_voice(
    text: str,
    voice_name: str = "Charon",
    output_path: Optional[Path | str] = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.8-flash-tts",
    use_cache: bool = True
) -> Tuple[Path, float]:
    """
    Sinh file giọng đọc từ Gemini TTS.
    Trả về: (Path_tới_file_wav, thời_lượng_giây)
    """
    clean_text = " ".join(text.strip().split())
    if not clean_text:
        raise ValueError("Văn bản câu quote không được để trống!")

    key = get_gemini_api_key(api_key)
    if not key:
        raise ValueError("Chưa tìm thấy Gemini API Key! Vui lòng cấu hình trong file .env hoặc nhập trực tiếp.")

    # Tạo cache key
    cache_dir = Path("temp/voice_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    hash_str = hashlib.sha256(f"{voice_name}:{clean_text}".encode("utf-8")).hexdigest()[:16]
    cached_file = cache_dir / f"voice_{voice_name}_{hash_str}.wav"

    if use_cache and cached_file.exists() and cached_file.stat().st_size > 1000:
        dur = get_audio_duration(cached_file)
        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            if out_p.resolve() != cached_file.resolve():
                import shutil
                shutil.copyfile(cached_file, out_p)
            return out_p, dur
        return cached_file, dur

    # Gọi Google GenAI SDK
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)

    # Cấu hình giọng đọc
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

    # Chỉ gửi trực tiếp nội dung văn bản cần đọc để Gemini TTS không phát âm thừa câu lệnh
    response = client.models.generate_content(
        model=model_name,
        contents=clean_text,
        config=config,
    )

    audio_bytes = None
    for candidate in response.candidates:
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    audio_bytes = part.inline_data.data
                    break

    if not audio_bytes:
        raise RuntimeError("Gemini API không trả về dữ liệu âm thanh. Vui lòng kiểm tra lại prompt hoặc thử lại sau.")

    # Lưu vào cached_file
    with wave.open(str(cached_file), "wb") as wf:
        wf.setnchannels(1)      # Mono
        wf.setsampwidth(2)      # 16-bit
        wf.setframerate(24000)  # Tần số chuẩn 24kHz
        wf.writeframes(audio_bytes)

    dur = get_audio_duration(cached_file)

    # Nếu có output_path cụ thể, sao chép sang
    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        if out_p.resolve() != cached_file.resolve():
            import shutil
            shutil.copyfile(cached_file, out_p)
        return out_p, dur

    return cached_file, dur
