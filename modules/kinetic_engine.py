from __future__ import annotations

import re
import struct
import wave
from pathlib import Path
from typing import List, Optional, Tuple


def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.cc (centiseconds)."""
    if seconds < 0:
        seconds = 0.0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        secs += 1
        cs = 0
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"


def strip_emotion_markers(text: str) -> str:
    """Loại bỏ các chỉ thị cảm xúc/đạo diễn trong ngoặc đơn (thở dài), [trầm giọng] khỏi chữ hiển thị trên màn hình."""
    if not text:
        return ""
    # Xóa nội dung trong ngoặc đơn hoặc ngoặc vuông
    cleaned = re.sub(r"\([^)]*\)", "", text)
    cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
    # Dọn dẹp khoảng trắng kép
    cleaned = " ".join(cleaned.split())
    return cleaned


def get_audio_acoustic_bounds(wav_path: Path | str) -> Tuple[float, float, float]:
    """
    Phân tích sóng âm thanh WAV thật để tìm chính xác:
    - speech_start: Thời điểm giọng đọc cất tiếng (bỏ qua khoảng lặng đầu file).
    - speech_end: Thời điểm giọng đọc dứt lời (bỏ qua khoảng lặng đuôi file).
    - total_duration: Tổng độ dài file âm thanh.
    """
    p = Path(wav_path)
    if not p.exists() or p.stat().st_size < 1000:
        return 0.15, 5.0, 5.0

    try:
        with wave.open(str(p), "rb") as wf:
            rate = wf.getframerate()
            frames = wf.getnframes()
            data = wf.readframes(frames)
            
            # Chuẩn hóa về 16-bit mono để tính RMS
            sampwidth = wf.getsampwidth()
            if sampwidth == 2:
                samples = struct.unpack(f"<{frames}h", data)
            else:
                return 0.15, frames / float(rate), frames / float(rate)

        total_dur = frames / float(rate)
        if total_dur <= 0:
            return 0.15, 5.0, 5.0

        chunk_size = int(rate * 0.025)  # Cửa sổ 25ms
        threshold = 500  # Ngưỡng RMS xác định có tiếng nói

        # 1. Tìm điểm bắt đầu cất tiếng
        speech_start = 0.15
        for i in range(0, len(samples) - chunk_size, chunk_size):
            chunk = samples[i:i + chunk_size]
            rms = (sum(s * s for s in chunk) / float(len(chunk))) ** 0.5
            if rms > threshold:
                speech_start = i / float(rate)
                break

        # 2. Tìm điểm kết thúc tiếng nói
        speech_end = total_dur - 0.1
        for i in range(len(samples) - chunk_size, 0, -chunk_size):
            chunk = samples[i:i + chunk_size]
            rms = (sum(s * s for s in chunk) / float(len(chunk))) ** 0.5
            if rms > threshold:
                speech_end = (i + chunk_size) / float(rate)
                break

        speech_start = max(0.05, round(speech_start, 2))
        speech_end = min(total_dur, max(speech_start + 0.5, round(speech_end, 2)))
        return speech_start, speech_end, round(total_dur, 2)

    except Exception:
        return 0.15, 5.0, 5.0


def split_quote_into_rhythmic_phrases(text: str) -> List[Tuple[str, float]]:
    """
    Tách câu quote thành các cụm từ nhịp điệu (3 - 5 từ/cụm) kèm trọng số ngắt nghỉ tự nhiên.
    Trả về: List[(cụm_từ, độ_dài_nghỉ_sau_cụm_giây)]
    """
    clean_text = strip_emotion_markers(text)
    clean_lines = [l.strip() for l in clean_text.splitlines() if l.strip()]
    if not clean_lines:
        return []

    raw_items: List[Tuple[str, float]] = []
    for line in clean_lines:
        # Tách theo các dấu câu ngắt nhịp tự nhiên: phẩy, chấm phẩy, chấm, gạch ngang
        tokens = re.split(r"([,;:\.\!\?\-—–]+)", line)
        temp_phrase = ""
        for i in range(0, len(tokens), 2):
            text_part = tokens[i].strip()
            punct_part = tokens[i + 1] if i + 1 < len(tokens) else ""
            if not text_part:
                continue
            
            pause = 0.1
            if any(p in punct_part for p in [".", "!", "?", "…"]):
                pause = 0.45
            elif any(p in punct_part for p in [",", "—", "–", "-"]):
                pause = 0.28
            elif any(p in punct_part for p in [";", ":"]):
                pause = 0.32

            raw_items.append((text_part, pause))

    phrases: List[Tuple[str, float]] = []
    for text_part, pause in raw_items:
        words = text_part.split()
        if len(words) <= 5:
            phrases.append((" ".join(words), pause))
        else:
            step = 4 if len(words) >= 7 else 3
            for i in range(0, len(words), step):
                sub = " ".join(words[i:i + step])
                if sub:
                    sub_pause = pause if (i + step >= len(words)) else 0.08
                    phrases.append((sub, sub_pause))

    if not phrases:
        phrases = [(clean_text, 0.3)]

    return phrases


def generate_kinetic_ass(
    quote_text: str,
    signature: str,
    voice_duration: float,
    video_duration: float,
    output_ass_path: Path | str,
    font_name: str = "Be Vietnam Pro",
    voice_wav_path: Optional[Path | str] = None
) -> Path:
    """
    Tạo file phụ đề ASS động (Kinetic Pop Typography) đồng bộ chính xác với Voice:
    - Sử dụng phân tích biên độ sóng âm thanh thật (acoustic boundary analysis) để khớp chữ đúng khoảnh khắc cất giọng.
    - Từng cụm từ (3-5 từ) xuất hiện lớn, nổi bật ở giữa màn hình theo nhịp giọng đọc.
    - Cuối video: Hiển thị toàn bộ câu quote trọn vẹn để người xem suy ngẫm sâu sắc.
    - Chữ ký @signature hiển thị thanh lịch ở safe-zone bên dưới.
    """
    out_p = Path(output_ass_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    # 1. Phân tích khoảng cất giọng thật từ file âm thanh
    speech_start, speech_end, actual_dur = 0.18, max(1.0, voice_duration - 0.2), voice_duration
    if voice_wav_path and Path(voice_wav_path).exists():
        speech_start, speech_end, actual_dur = get_audio_acoustic_bounds(voice_wav_path)

    # 2. Tách cụm từ và loại bỏ các ký hiệu chỉ thị cảm xúc
    phrase_tuples = split_quote_into_rhythmic_phrases(quote_text)
    if not phrase_tuples:
        phrase_tuples = [(strip_emotion_markers(quote_text), 0.3)]

    # 3. Tính toán trọng số phát âm cho từng cụm từ dựa trên số ký tự và thời gian ngắt nghỉ
    weights = []
    for phrase, pause in phrase_tuples:
        char_weight = max(2, len(phrase.strip()))
        total_weight = char_weight + (pause * 24.0)
        weights.append(total_weight)

    sum_weights = max(1.0, sum(weights))
    spoken_window = max(1.0, speech_end - speech_start)

    events: List[str] = []
    # Điểm bắt đầu có 60ms đón đầu thị giác để mắt kịp bắt chữ đúng lúc tai nghe
    curr_time = max(0.0, speech_start - 0.06)

    for i, (phrase, pause) in enumerate(phrase_tuples):
        portion = weights[i] / sum_weights
        p_dur = portion * spoken_window
        p_dur = max(0.45, p_dur)
        end_time = curr_time + p_dur

        if i == len(phrase_tuples) - 1:
            end_time = max(end_time, speech_end + 0.15)

        start_str = format_ass_time(curr_time)
        end_str = format_ass_time(end_time)

        words = phrase.split()
        if len(words) >= 5:
            mid = len(words) // 2
            formatted_text = " ".join(words[:mid]) + "\\N" + " ".join(words[mid:])
        else:
            formatted_text = phrase

        # Hiệu ứng chuyển động chữ: Hiện mượt mà (fade in 80ms, fade out 45ms)
        events.append(
            f"Dialogue: 0,{start_str},{end_str},QuotePhrase,,0,0,0,,{{\\fad(80,45)}}{formatted_text}"
        )
        curr_time = end_time

    # 4. Giai đoạn kết: Hiển thị trọn vẹn câu quote lắng đọng (Full Quote Linger Card)
    full_start = max(curr_time, speech_end + 0.3)
    if full_start < video_duration:
        full_start_str = format_ass_time(full_start)
        full_end_str = format_ass_time(video_duration)

        clean_full = strip_emotion_markers(quote_text)
        full_words = clean_full.split()
        if len(full_words) > 6:
            n = len(full_words)
            c1 = n // 3
            c2 = (n * 2) // 3
            full_multiline = " ".join(full_words[:c1]) + "\\N" + " ".join(full_words[c1:c2]) + "\\N" + " ".join(full_words[c2:])
        else:
            full_multiline = clean_full

        events.append(
            f"Dialogue: 0,{full_start_str},{full_end_str},FullQuoteStyle,,0,0,0,,{{\\fad(200,100)}}“{full_multiline}”"
        )

    # 5. Hiển thị chữ ký video (@kênh)
    if signature and signature.strip():
        sig_clean = signature.strip()
        events.append(
            f"Dialogue: 0,0:00:00.00,{format_ass_time(video_duration)},SigStyle,,0,0,0,,{sig_clean}"
        )

    ass_template = f"""[Script Info]
Title: TikTok Quote Voice - Precise Acoustic Kinetic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: QuotePhrase,{font_name},80,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,6.5,3.2,5,80,80,0,1
Style: FullQuoteStyle,{font_name},52,&H00F8FAFC,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,5.2,2.8,5,80,80,0,1
Style: SigStyle,{font_name},32,&H0038BDF8,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2.5,1.2,2,80,80,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n"

    with open(out_p, "w", encoding="utf-8") as f:
        f.write(ass_template)

    return out_p
