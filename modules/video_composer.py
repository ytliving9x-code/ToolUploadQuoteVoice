import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image

from modules.typography_engine import create_quote_overlay
from modules.kinetic_engine import generate_kinetic_ass

logger = logging.getLogger("quote_voice.video_composer")

# Tìm đường dẫn FFmpeg (hỗ trợ cả hệ thống và imageio-ffmpeg)
try:
    FFMPEG_EXE = shutil.which("ffmpeg")
    if not FFMPEG_EXE:
        import imageio_ffmpeg
        FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = shutil.which("ffmpeg") or "ffmpeg"


def probe_media_duration(file_path: Path | str) -> float:
    """Đo thời lượng video hoặc audio bằng FFprobe nếu có."""
    ffprobe_exe = shutil.which("ffprobe") or "ffprobe"
    try:
        cmd = [
            ffprobe_exe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def compose_quote_video(
    bg_media_path: Path | str,
    quote: str,
    voice_wav_path: Optional[Path | str] = None,
    output_path: Path | str = Path("output/quote_video.mp4"),
    duration_mode: str = "dynamic",  # "dynamic" (theo giọng đọc) hoặc "fixed_18s" (18 giây)
    custom_duration: Optional[float] = None,
    signature: str = "@quote_channel",
    bgm_path: Optional[Path | str] = None,
    bgm_volume: float = 0.14,
    enable_antiglare: bool = True,
    scrim_max_alpha: int = 160,
    font_path: Optional[Path | str] = None,
) -> Path:
    """
    Hợp nhất Nền (Ảnh/Video) + Typography tiếng Việt + Voice Gemini + BGM thành Video TikTok 1080x1920:
    - Chuẩn 9:16 dọc không viền đen.
    - Âm thanh hòa âm chuyên nghiệp (Voice to rõ, BGM êm dịu, fadeout cuối).
    """
    media_file = Path(bg_media_path)
    if not media_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file nền: {media_file}")

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Xác định thời lượng giọng đọc
    voice_dur = 0.0
    if voice_wav_path and Path(voice_wav_path).exists():
        from modules.voice_service import get_audio_duration
        voice_dur = get_audio_duration(voice_wav_path)
        if voice_dur <= 0:
            voice_dur = probe_media_duration(voice_wav_path)

    # 2. Quyết định thời lượng video
    if custom_duration and custom_duration > 0:
        video_duration = custom_duration
    elif duration_mode == "fixed_18s":
        video_duration = 18.0
    else:  # "dynamic"
        # Thời lượng voice + 1.8 giây đọng cảm xúc ở cuối (tối thiểu 5s, tối đa 60s)
        padding = 1.8
        target_dur = (voice_dur + padding) if voice_dur > 0 else 10.0
        video_duration = max(5.0, min(target_dur, 60.0))

    # 3. Tạo file phụ đề động Kinetic Phrase Pop khớp chuẩn theo nhịp giọng đọc
    tmp_ass_path = out_file.parent / f"kinetic_{out_file.stem}.ass"
    generate_kinetic_ass(
        quote_text=quote,
        signature=signature,
        voice_duration=voice_dur,
        video_duration=video_duration,
        output_ass_path=tmp_ass_path,
        font_name="Be Vietnam Pro"
    )

    escaped_ass = str(tmp_ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    fonts_dir = str(Path("assets/fonts").resolve()).replace("\\", "/").replace(":", "\\:")

    # 4. Xác định loại nền (Ảnh hay Video)
    video_exts = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
    is_video_bg = media_file.suffix.lower() in video_exts

    try:
        # Xây dựng FFmpeg Filter Complex với chữ xuất hiện theo nhịp voice
        filter_parts = []
        if is_video_bg:
            filter_parts.append(
                f"[0:v]trim=0:{video_duration},setpts=PTS-STARTPTS,"
                f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,fps=30,"
                f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.22:t=fill,"
                f"subtitles='{escaped_ass}':fontsdir='{fonts_dir}'[outv]"
            )
        else:
            filter_parts.append(
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop=1080:1920:(in_w-1080)/2:(in_h-1920)/2,fps=30,"
                f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.20:t=fill,"
                f"subtitles='{escaped_ass}':fontsdir='{fonts_dir}'[outv]"
            )

        # Cấu hình âm thanh
        input_args = []
        if is_video_bg:
            input_args.extend(["-i", str(media_file)])
        else:
            input_args.extend(["-loop", "1", "-t", str(video_duration), "-i", str(media_file)])

        has_voice = bool(voice_wav_path and Path(voice_wav_path).exists())
        has_bgm = bool(bgm_path and Path(bgm_path).exists())

        audio_input_idx = 1
        voice_idx = None
        bgm_idx = None

        if has_voice:
            input_args.extend(["-i", str(voice_wav_path)])
            voice_idx = audio_input_idx
            audio_input_idx += 1

        if has_bgm:
            input_args.extend(["-stream_loop", "-1", "-i", str(bgm_path)])
            bgm_idx = audio_input_idx
            audio_input_idx += 1


        # Xử lý luồng âm thanh
        has_audio = False
        fade_start = max(0.1, video_duration - 1.5)

        if has_voice and has_bgm:
            # Voice 100% âm lượng + BGM ở bgm_volume, mix lại và fadeout ở cuối
            filter_parts.append(
                f"[{voice_idx}:a]aresample=48000,apad,atrim=0:{video_duration}[va];"
                f"[{bgm_idx}:a]atrim=0:{video_duration},volume={bgm_volume:.2f},afade=t=out:st={fade_start:.2f}:d=1.5,aresample=48000[ba];"
                f"[va][ba]amix=inputs=2:duration=first:dropout_transition=2[outa]"
            )
            has_audio = True
        elif has_voice:
            # Chỉ có voice: pad thêm khoảng lặng để đúng độ dài video
            filter_parts.append(
                f"[{voice_idx}:a]aresample=48000,apad,atrim=0:{video_duration},afade=t=out:st={fade_start:.2f}:d=1.2[outa]"
            )
            has_audio = True
        elif has_bgm:
            # Chỉ có BGM
            filter_parts.append(
                f"[{bgm_idx}:a]atrim=0:{video_duration},volume={bgm_volume:.2f},afade=t=out:st={fade_start:.2f}:d=1.5,aresample=48000[outa]"
            )
            has_audio = True

        filter_complex_str = ";".join(filter_parts)

        cmd = [
            FFMPEG_EXE,
            "-y",
            *input_args,
            "-filter_complex", filter_complex_str,
            "-map", "[outv]",
        ]

        if has_audio:
            cmd.extend(["-map", "[outa]", "-c:a", "aac", "-b:a", "192k"])
        else:
            cmd.append("-an")

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-t", str(video_duration),
            str(out_file)
        ])

        logger.info(f"Đang render video TikTok ({video_duration:.1f}s) -> {out_file.name}...")
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if proc.returncode != 0:
            logger.error(f"FFmpeg error: {proc.stderr}")
            raise RuntimeError(f"Lỗi FFmpeg khi ghép video: {proc.stderr[:400]}")

    finally:
        if tmp_ass_path.exists():
            try:
                tmp_ass_path.unlink()
            except Exception:
                pass

    logger.info(f"Render video thành công: {out_file} ({out_file.stat().st_size} bytes)")
    return out_file
