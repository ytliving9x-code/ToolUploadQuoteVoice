import hashlib
import io
import logging
import os
import struct
import sys
import wave
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger("quote_voice.voice_service")

# Danh mục các giọng đọc tiếng Việt chuyên nghiệp cho Video Quote
AVAILABLE_VOICES: Dict[str, Dict[str, str]] = {
    "NamMinh": {
        "engine": "edge_tts",
        "voice_id": "vi-VN-NamMinhNeural",
        "gender": "Nam",
        "title": "Nam Minh (Nam Trầm Ấm - Chuẩn Quote)",
        "tag": "⭐ Khuyên dùng #1 cho Quote TikTok",
        "desc": "Trầm ấm, đĩnh đạc, truyền cảm hứng, chuẩn mực video triết lý.",
        "prompt_style": "chất giọng nam trầm ấm, đĩnh đạc, truyền cảm hứng và ngắt nghỉ sâu lắng"
    },
    "Charon": {
        "engine": "gemini",
        "voice_id": "Charon",
        "gender": "Nam",
        "title": "Charon (Nam Trầm Dày - Gemini AI)",
        "tag": "Triết lý / Lãnh đạo",
        "desc": "Trầm ấm, uy lực, phong thái phát thanh viên đĩnh đạc.",
        "prompt_style": "chất giọng nam trầm, phong thái đĩnh đạc, đằm thắm, truyền cảm hứng và uy quyền"
    },
    "Orus": {
        "engine": "gemini",
        "voice_id": "Orus",
        "gender": "Nam",
        "title": "Orus (Nam Điềm Đạm - Gemini AI)",
        "tag": "Chiêm nghiệm & Sâu sắc",
        "desc": "Điềm đạm, sâu sắc, ngữ điệu tự nhiên, truyền cảm.",
        "prompt_style": "chất giọng nam điềm đạm, sâu lắng, ngữ điệu tự nhiên"
    },
    "Fenrir": {
        "engine": "gemini",
        "voice_id": "Fenrir",
        "gender": "Nam",
        "title": "Fenrir (Nam Hào Sảng - Gemini AI)",
        "tag": "Động lực & Ý chí",
        "desc": "Mạnh mẽ, dứt khoát, hào sảng, tràn đầy năng lượng bứt phá.",
        "prompt_style": "chất giọng nam mạnh mẽ, hào sảng, dứt khoát, truyền động lực và uy lực"
    },
    "HoaiMy": {
        "engine": "edge_tts",
        "voice_id": "vi-VN-HoaiMyNeural",
        "gender": "Nữ",
        "title": "Hoài My (Nữ Sâu Lắng - Chuẩn Quote)",
        "tag": "⭐ Khuyên dùng cho Giọng Nữ",
        "desc": "Sâu lắng, truyền cảm, ngắt nghỉ tự nhiên, thích hợp chữa lành.",
        "prompt_style": "chất giọng nữ sâu lắng, truyền cảm và ngắt nghỉ tự nhiên"
    },
    "Kore": {
        "engine": "gemini",
        "voice_id": "Kore",
        "gender": "Nữ",
        "title": "Kore (Nữ Trầm Ấm - Gemini AI)",
        "tag": "Tâm sự",
        "desc": "Trầm ấm, sâu lắng, ngắt nghỉ tự nhiên như người thật tâm sự.",
        "prompt_style": "chất giọng nữ trầm ấm, sâu lắng, truyền cảm, rõ ràng và ngắt nghỉ tự nhiên"
    },
    "Puck": {
        "engine": "gemini",
        "voice_id": "Puck",
        "gender": "Nam",
        "title": "Puck (Nam Tươi Trẻ - Gemini AI)",
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
def save_clean_pcm_wav(audio_bytes: bytes, target_path: Path | str) -> float:
    """
    Xử lý dữ liệu âm thanh trả về từ Gemini TTS:
    - Nếu API trả về container WAV (bắt đầu bằng RIFF), trích xuất CHÍNH XÁC các sample PCM
      của data chunk, loại bỏ toàn bộ phần metadata/IPTC ở đuôi (nguyên nhân gây tiếng xẹt xẹt / rè ở cuối audio).
    - Áp dụng soft fade-out nhẹ (35ms) ở cuối để âm thanh dứt êm ái, hoàn toàn không có tiếng bụp/xẹt.
    - Ghi lại chuẩn WAV sạch 16-bit Mono 24kHz.
    """
    p = Path(target_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    channels, sampwidth, framerate = 1, 2, 24000
    raw_pcm = b""

    if audio_bytes.startswith(b"RIFF"):
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                raw_pcm = wf.readframes(wf.getnframes())
        except Exception:
            idx = audio_bytes.find(b"data")
            if idx != -1:
                data_size = int.from_bytes(audio_bytes[idx + 4:idx + 8], byteorder="little")
                raw_pcm = audio_bytes[idx + 8:idx + 8 + data_size]
            else:
                raw_pcm = audio_bytes
    else:
        raw_pcm = audio_bytes

    # Áp dụng soft fade-out 35ms ở cuối để dứt âm êm ái
    if sampwidth == 2 and len(raw_pcm) >= 2:
        fade_samples = int(framerate * 0.035)
        num_samples = len(raw_pcm) // 2
        if num_samples > fade_samples:
            samples = list(struct.unpack(f"<{num_samples}h", raw_pcm))
            start_fade = num_samples - fade_samples
            for i in range(fade_samples):
                factor = 1.0 - (i / float(fade_samples))
                samples[start_fade + i] = int(samples[start_fade + i] * factor)
            raw_pcm = struct.pack(f"<{num_samples}h", *samples)

    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        wf.writeframes(raw_pcm)

    return get_audio_duration(p)


def _synthesize_edge_tts(text: str, voice_id: str, out_wav: Path) -> float:
    """Sinh giọng đọc bằng Edge-TTS và chuyển đổi sang chuẩn 24kHz Mono WAV sạch."""
    import asyncio
    import subprocess
    import edge_tts
    from modules.video_composer import FFMPEG_EXE

    mp3_tmp = out_wav.parent / f"tmp_{out_wav.stem}.mp3"
    
    async def _run():
        comm = edge_tts.Communicate(text, voice_id, rate="-2%")
        await comm.save(str(mp3_tmp))

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(asyncio.run, _run()).result()
    else:
        asyncio.run(_run())

    # Chuyển đổi MP3 sang WAV 24000Hz mono
    cmd = [FFMPEG_EXE, "-y", "-i", str(mp3_tmp), "-ar", "24000", "-ac", "1", str(out_wav)]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if mp3_tmp.exists():
        try:
            mp3_tmp.unlink()
        except Exception:
            pass

    return get_audio_duration(out_wav)


def synthesize_voice(
    text: str,
    voice_name: str = "NamMinh",
    output_path: Optional[Path | str] = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.8-flash-tts",
    use_cache: bool = True
) -> Tuple[Path, float]:
    """
    Sinh file giọng đọc (Nam Minh / Hoài My qua Edge-TTS hoặc Gemini 3.8 Flash TTS).
    Trả về: (Path_tới_file_wav, thời_lượng_giây)
    """
    clean_text = " ".join(text.strip().split())
    if not clean_text:
        raise ValueError("Văn bản câu quote không được để trống!")

    voice_meta = AVAILABLE_VOICES.get(voice_name, AVAILABLE_VOICES["NamMinh"])
    engine = voice_meta.get("engine", "gemini")

    # Tạo cache key (kèm version để xóa bỏ các cache cũ có chứa câu lệnh)
    cache_dir = Path("temp/voice_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_ver = "v4_clean_tts"
    hash_str = hashlib.sha256(f"{cache_ver}:{voice_name}:{clean_text}".encode("utf-8")).hexdigest()[:16]
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

    # 1. Nếu là động cơ Edge-TTS (Nam Minh, Hoài My)
    if engine == "edge_tts":
        voice_id = voice_meta.get("voice_id", "vi-VN-NamMinhNeural")
        dur = _synthesize_edge_tts(clean_text, voice_id, cached_file)
        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            if out_p.resolve() != cached_file.resolve():
                import shutil
                shutil.copyfile(cached_file, out_p)
            return out_p, dur
        return cached_file, dur

    # 2. Nếu là động cơ Gemini TTS
    key = get_gemini_api_key(api_key)
    if not key:
        # Nếu chưa cấu hình Gemini API key, tự động chuyển sang Edge-TTS Nam Minh
        logger.warning("Chưa có Gemini API Key, tự động chuyển sang giọng Nam Minh (Edge-TTS)!")
        return synthesize_voice(clean_text, voice_name="NamMinh", output_path=output_path, use_cache=use_cache)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)

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
            raise RuntimeError("Gemini API không trả về dữ liệu âm thanh.")

        dur = save_clean_pcm_wav(audio_bytes, cached_file)

    except Exception as ex:
        err_msg = str(ex).lower()
        if "quota" in err_msg or "429" in err_msg or "resource_exhausted" in err_msg:
            logger.warning("Gemini API hết quota miễn phí trong ngày, tự động dùng giọng Nam Minh chuẩn Quote TikTok!")
            return synthesize_voice(clean_text, voice_name="NamMinh", output_path=output_path, use_cache=use_cache)
        else:
            logger.warning(f"Lỗi Gemini TTS ({ex}), chuyển dự phòng sang Nam Minh!")
            return synthesize_voice(clean_text, voice_name="NamMinh", output_path=output_path, use_cache=use_cache)

    # Nếu có output_path cụ thể, sao chép sang
    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        if out_p.resolve() != cached_file.resolve():
            import shutil
            shutil.copyfile(cached_file, out_p)
        return out_p, dur

    return cached_file, dur
