from __future__ import annotations

import re
from pathlib import Path
from typing import List


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


def split_quote_into_rhythmic_phrases(text: str) -> List[str]:
    """
    Tách câu quote thành các cụm từ nhịp điệu (3 - 5 từ/cụm)
    để hiển thị kinetic typography theo từng nhịp giọng đọc.
    """
    clean_lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not clean_lines:
        return []

    raw_chunks: List[str] = []
    for line in clean_lines:
        # Tách theo các dấu ngắt câu tự nhiên: phẩy, chấm phẩy, hai chấm, gạch ngang
        parts = re.split(r"[,;:\-—–]+", line)
        for p in parts:
            p = p.strip()
            if p:
                raw_chunks.append(p)

    phrases: List[str] = []
    for chunk in raw_chunks:
        words = chunk.split()
        if len(words) <= 5:
            phrases.append(" ".join(words))
        else:
            step = 4 if len(words) >= 7 else 3
            for i in range(0, len(words), step):
                sub = " ".join(words[i:i + step])
                if sub:
                    phrases.append(sub)

    return phrases if phrases else [text.strip()]


def generate_kinetic_ass(
    quote_text: str,
    signature: str,
    voice_duration: float,
    video_duration: float,
    output_ass_path: Path | str,
    font_name: str = "Be Vietnam Pro"
) -> Path:
    """
    Tạo file phụ đề ASS động (Kinetic Pop Typography):
    - Từng cụm từ xuất hiện lớn, nổi bật ở giữa màn hình đồng bộ theo giọng đọc.
    - Cuối video (sau khi giọng đọc kết thúc): Hiển thị toàn bộ câu quote trọn vẹn để người xem suy ngẫm.
    - Chữ ký @signature hiển thị thanh lịch ở safe-zone bên dưới.
    """
    out_p = Path(output_ass_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    phrases = split_quote_into_rhythmic_phrases(quote_text)
    if not phrases:
        phrases = [quote_text]

    # Tính toán thời lượng cho từng cụm dựa trên tỷ lệ từ
    total_words = sum(max(1, len(p.split())) for p in phrases)
    dur_per_word = (voice_duration - 0.2) / max(1, total_words)

    events: List[str] = []
    curr_time = 0.0

    for i, phrase in enumerate(phrases):
        w_count = max(1, len(phrase.split()))
        p_dur = w_count * dur_per_word
        p_dur = max(0.8, p_dur)
        end_time = curr_time + p_dur

        if i == len(phrases) - 1:
            end_time = max(end_time, voice_duration + 0.2)

        start_str = format_ass_time(curr_time)
        end_str = format_ass_time(end_time)

        words = phrase.split()
        if len(words) >= 5:
            mid = len(words) // 2
            formatted_text = " ".join(words[:mid]) + "\\N" + " ".join(words[mid:])
        else:
            formatted_text = phrase

        # Hiệu ứng mờ dần nhẹ nhàng (fade in 100ms, fade out 60ms)
        events.append(
            f"Dialogue: 0,{start_str},{end_str},QuotePhrase,,0,0,0,,{{\\fad(100,60)}}{formatted_text}"
        )
        curr_time = end_time

    # Giai đoạn cuối: Hiển thị trọn vẹn câu quote lắng đọng
    full_start = max(curr_time, voice_duration + 0.2)
    if full_start < video_duration:
        full_start_str = format_ass_time(full_start)
        full_end_str = format_ass_time(video_duration)

        clean_full = " ".join(quote_text.strip().split())
        full_words = clean_full.split()
        if len(full_words) > 6:
            n = len(full_words)
            c1 = n // 3
            c2 = (n * 2) // 3
            full_multiline = " ".join(full_words[:c1]) + "\\N" + " ".join(full_words[c1:c2]) + "\\N" + " ".join(full_words[c2:])
        else:
            full_multiline = clean_full

        events.append(
            f"Dialogue: 0,{full_start_str},{full_end_str},FullQuoteStyle,,0,0,0,,{{\\fad(220,100)}}“{full_multiline}”"
        )

    # Hiển thị chữ ký video
    if signature and signature.strip():
        sig_clean = signature.strip()
        events.append(
            f"Dialogue: 0,0:00:00.00,{format_ass_time(video_duration)},SigStyle,,0,0,0,,{sig_clean}"
        )

    ass_template = f"""[Script Info]
Title: TikTok Quote Voice - Kinetic Pop Subtitle
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: QuotePhrase,{font_name},78,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,6.0,3.0,5,80,80,0,1
Style: FullQuoteStyle,{font_name},52,&H00F8FAFC,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,5.0,2.5,5,80,80,0,1
Style: SigStyle,{font_name},32,&H0038BDF8,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2.5,1.2,2,80,80,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n"

    with open(out_p, "w", encoding="utf-8") as f:
        f.write(ass_template)

    return out_p
