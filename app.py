from __future__ import annotations

import io
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Đảm bảo thư mục gốc nằm đầu sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
try:
    os.chdir(PROJECT_ROOT)
except Exception:
    pass

import streamlit as st
from PIL import Image, ImageEnhance

from modules.voice_service import AVAILABLE_VOICES, synthesize_voice, get_audio_duration
from modules.typography_engine import create_quote_overlay, get_vietnamese_font
from modules.video_composer import compose_quote_video

# Cấu hình giao diện Streamlit
st.set_page_config(
    page_title="TikTok Quote Studio with AI Voice",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QuoteStudioVoice")

# Tự động tạo các thư mục lưu trữ nếu chưa có (cần thiết trên Streamlit Cloud)
for dir_name in ["temp", "temp/voice_cache", "output", "assets/backgrounds", "assets/bgm"]:
    Path(dir_name).mkdir(parents=True, exist_ok=True)

# ==============================================================================
# ULTRA-PREMIUM AESTHETIC CSS (GLASSMORPHISM & PHONE MOCKUP)
# ==============================================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #070B12 !important;
        background-image: 
            radial-gradient(circle at 12% 12%, rgba(56, 189, 248, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 88% 18%, rgba(168, 85, 247, 0.08) 0%, transparent 45%),
            radial-gradient(circle at 50% 90%, rgba(14, 165, 233, 0.06) 0%, transparent 50%) !important;
        background-attachment: fixed !important;
        color: #F1F5F9;
    }

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1400px !important;
    }

    /* Hero Badge */
    .hero-top-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(14, 165, 233, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.35);
        color: #38BDF8;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 900;
        letter-spacing: -0.7px;
        background: linear-gradient(135deg, #FFFFFF 20%, #7DD3FC 60%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }

    .subtitle-text {
        font-size: 0.95rem;
        color: #94A3B8;
        margin-bottom: 1.5rem;
    }

    /* Card Panels */
    .glass-panel {
        background: rgba(15, 23, 42, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 1rem;
        backdrop-filter: blur(12px);
    }

    .step-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 0.8rem;
    }

    .step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        background: linear-gradient(135deg, #0284C7 0%, #38BDF8 100%);
        color: #FFFFFF;
        font-size: 0.82rem;
        font-weight: 800;
        border-radius: 8px;
    }

    .step-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #F8FAFC;
    }

    /* Phone Mockup Frame */
    .phone-mockup-wrapper {
        background: #000000;
        border: 2.5px solid rgba(255, 255, 255, 0.12);
        border-radius: 28px;
        padding: 10px;
        box-shadow: 
            0 0 0 1px rgba(0, 0, 0, 0.8),
            0 25px 60px -15px rgba(0, 0, 0, 0.9),
            0 0 35px -5px rgba(56, 189, 248, 0.2);
        position: relative;
        max-width: 440px;
        margin: 0 auto;
    }

    .phone-notch {
        width: 90px;
        height: 14px;
        background: #0F172A;
        border-radius: 0 0 10px 10px;
        margin: 0 auto 8px auto;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
    }

    .phone-mockup-wrapper video,
    .phone-mockup-wrapper .stImage img {
        border-radius: 18px !important;
        max-height: 520px !important;
        width: auto !important;
        margin: 0 auto !important;
        display: block !important;
        object-fit: cover !important;
    }

    /* Hero Button */
    .btn-hero button {
        background: linear-gradient(135deg, #0284C7 0%, #2563EB 50%, #7C3AED 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        min-height: 54px !important;
        border-radius: 14px !important;
        box-shadow: 0 10px 25px -4px rgba(37, 99, 235, 0.5) !important;
        transition: all 0.2s ease !important;
    }
    .btn-hero button:hover {
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 14px 35px -4px rgba(56, 189, 248, 0.7) !important;
    }

    .meta-box {
        display: flex;
        justify-content: space-around;
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.75rem;
        margin-top: 0.8rem;
        margin-bottom: 1rem;
        text-align: center;
    }
    .meta-val {
        font-size: 0.92rem;
        font-weight: 800;
        color: #38BDF8;
        font-family: 'JetBrains Mono', monospace;
    }
    .meta-lbl {
        font-size: 0.72rem;
        color: #94A3B8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# KHỞI TẠO SESSION STATE
# ==============================================================================
if "quote_text" not in st.session_state:
    st.session_state.quote_text = "Hành trình vạn dặm luôn bắt đầu bằng một bước chân đầu tiên."
if "selected_voice" not in st.session_state:
    st.session_state.selected_voice = "Charon"
if "bg_media" not in st.session_state:
    st.session_state.bg_media = "assets/backgrounds/default_night.jpg"
if "signature" not in st.session_state:
    st.session_state.signature = "@quote_channel"
if "duration_mode" not in st.session_state:
    st.session_state.duration_mode = "dynamic"
if "enable_bgm" not in st.session_state:
    st.session_state.enable_bgm = True
if "rendered_video" not in st.session_state:
    st.session_state.rendered_video = None
if "cached_voice_file" not in st.session_state:
    st.session_state.cached_voice_file = None
if "cached_voice_dur" not in st.session_state:
    st.session_state.cached_voice_dur = 0.0

# ==============================================================================
# HEADER
# ==============================================================================
st.markdown(
    """
    <div class="hero-top-badge">🎙️ Gemini AI Voice • TikTok 9:16 Video Engine</div>
    <div class="main-title">TikTok Quote Studio with Voice</div>
    <div class="subtitle-text">Tự động sản xuất video Quote kèm giọng đọc tiếng Việt chân thật (Gemini TTS) chuẩn khung hình TikTok.</div>
    """,
    unsafe_allow_html=True,
)

col_controls, col_preview = st.columns([1.25, 1.0], gap="large")

# ==============================================================================
# CỘT TRÁI: BỘ ĐIỀU KHIỂN 4 BƯỚC
# ==============================================================================
with col_controls:
    # ---------------- BƯỚC 1: NỘI DUNG QUOTE ----------------
    with st.container():
        st.markdown(
            """
            <div class="step-header">
                <span class="step-num">1</span>
                <span class="step-title">Nhập Nội Dung Câu Quote</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        quote_input = st.text_area(
            "Nhập câu trích dẫn bạn muốn làm video:",
            value=st.session_state.quote_text,
            height=110,
            placeholder="Dán hoặc gõ nội dung câu quote của bạn vào đây...",
            label_visibility="collapsed"
        )
        if quote_input != st.session_state.quote_text:
            st.session_state.quote_text = quote_input
            st.session_state.rendered_video = None
            st.session_state.cached_voice_file = None

        col_w, col_clear = st.columns([2.5, 1.0])
        with col_w:
            word_count = len(st.session_state.quote_text.strip().split()) if st.session_state.quote_text.strip() else 0
            char_count = len(st.session_state.quote_text.strip())
            st.caption(f"📝 **{word_count} từ** ({char_count} ký tự) • Gợi ý độ dài lý tưởng cho video ngắn là 12 - 30 từ.")
        with col_clear:
            if st.button("🗑️ Xóa chữ", use_container_width=True):
                st.session_state.quote_text = ""
                st.session_state.rendered_video = None
                st.session_state.cached_voice_file = None
                st.rerun()

    st.write("")

    # ---------------- BƯỚC 2: GIỌNG ĐỌC AI (VOICE) ----------------
    with st.container():
        st.markdown(
            """
            <div class="step-header">
                <span class="step-num">2</span>
                <span class="step-title">Giọng Đọc AI (Gemini 3.8 Flash TTS)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        voice_options = list(AVAILABLE_VOICES.keys())
        voice_labels = [
            f"{name} ({AVAILABLE_VOICES[name]['gender']}) - {AVAILABLE_VOICES[name]['desc'][:32]}..."
            for name in voice_options
        ]

        curr_idx = voice_options.index(st.session_state.selected_voice) if st.session_state.selected_voice in voice_options else 0
        selected_idx = st.selectbox(
            "Chọn chất giọng đọc:",
            range(len(voice_options)),
            format_func=lambda i: voice_labels[i],
            index=curr_idx,
            label_visibility="collapsed"
        )
        chosen_voice = voice_options[selected_idx]

        if chosen_voice != st.session_state.selected_voice:
            st.session_state.selected_voice = chosen_voice
            st.session_state.rendered_video = None
            st.session_state.cached_voice_file = None

        v_meta = AVAILABLE_VOICES[chosen_voice]
        st.markdown(
            f"<div style='font-size:0.85rem; color:#94A3B8; margin-top:-4px; margin-bottom:8px;'>"
            f"<span style='color:#38BDF8; font-weight:700;'>{v_meta['title']}</span>: {v_meta['desc']} ({v_meta['tag']})"
            f"</div>",
            unsafe_allow_html=True
        )

        col_v_btn, col_v_audio = st.columns([1.0, 1.8])
        with col_v_btn:
            btn_test_voice = st.button("🔊 Nghe Thử Voice", use_container_width=True)

        if btn_test_voice:
            if not st.session_state.quote_text.strip():
                st.warning("Vui lòng nhập câu quote trước khi nghe thử!")
            else:
                with st.spinner(f"Đang sinh giọng {chosen_voice}..."):
                    try:
                        v_file, v_dur = synthesize_voice(
                            text=st.session_state.quote_text,
                            voice_name=chosen_voice,
                            output_path=f"temp/preview_voice_{chosen_voice}.wav"
                        )
                        st.session_state.cached_voice_file = str(v_file)
                        st.session_state.cached_voice_dur = v_dur
                    except Exception as ex:
                        st.error(f"Lỗi: {ex}")

        with col_v_audio:
            if st.session_state.cached_voice_file and Path(st.session_state.cached_voice_file).exists():
                st.audio(st.session_state.cached_voice_file, format="audio/wav")
                st.caption(f"⏱️ Thời lượng câu đọc: **{st.session_state.cached_voice_dur:.1f}s**")

    st.write("")

    # ---------------- BƯỚC 3: NỀN VIDEO / ẢNH ----------------
    with st.container():
        st.markdown(
            """
            <div class="step-header">
                <span class="step-num">3</span>
                <span class="step-title">Nền Video / Ảnh (Dọc 9:16)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded_media = st.file_uploader(
            "Tải ảnh hoặc video nền từ máy tính (JPG, PNG, MP4, MOV):",
            type=["jpg", "jpeg", "png", "mp4", "mov", "webm"],
            help="Hệ thống sẽ tự động crop căn giữa về tỷ lệ dọc 1080x1920 không viền đen.",
            label_visibility="collapsed"
        )

        if uploaded_media:
            # Lưu tạm vào thư mục temp
            temp_dir = Path("temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            saved_bg_path = temp_dir / f"uploaded_bg_{uploaded_media.name}"
            with open(saved_bg_path, "wb") as f:
                f.write(uploaded_media.getbuffer())
            st.session_state.bg_media = str(saved_bg_path)
            st.session_state.rendered_video = None
            st.success(f"Đã tải lên: {uploaded_media.name}")

    st.write("")

    # ---------------- BƯỚC 4: THỜI LƯỢNG & XUẤT VIDEO ----------------
    with st.container():
        st.markdown(
            """
            <div class="step-header">
                <span class="step-num">4</span>
                <span class="step-title">Tùy Chỉnh & Xuất Video</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_sig, col_dur = st.columns([1.0, 1.2])
        with col_sig:
            sig_input = st.text_input(
                "Chữ ký video (Signature):",
                value=st.session_state.signature,
                placeholder="@kenh_cua_ban"
            )
            if sig_input != st.session_state.signature:
                st.session_state.signature = sig_input
                st.session_state.rendered_video = None

        with col_dur:
            mode_options = ["⚡ Khớp theo Voice (+1.8s lắng đọng)", "⏱️ Cố định 18 giây TikTok"]
            mode_val = 0 if st.session_state.duration_mode == "dynamic" else 1
            sel_mode = st.radio(
                "Thời lượng video:",
                mode_options,
                index=mode_val,
                horizontal=False,
            )
            st.session_state.duration_mode = "dynamic" if "Khớp" in sel_mode else "fixed_18s"

        st.session_state.enable_bgm = st.checkbox(
            "🎵 Hòa âm thêm nhạc nền Ambient Lofi nhẹ nhàng (14% âm lượng, fadeout cuối)",
            value=st.session_state.enable_bgm
        )

        st.markdown('<div class="btn-hero">', unsafe_allow_html=True)
        btn_render = st.button("🚀 XUẤT VIDEO TIKTOK CÓ GIỌNG ĐỌC", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if btn_render:
            bg_target = st.session_state.bg_media
            if not bg_target or not Path(bg_target).exists():
                st.error("Chưa có nền! Vui lòng tải một file ảnh hoặc video ở Bước 3.")
            elif not st.session_state.quote_text.strip():
                st.error("Câu quote đang trống! Vui lòng nhập quote ở Bước 1.")
            else:
                out_folder = Path("output")
                out_folder.mkdir(parents=True, exist_ok=True)
                timestamp = int(time.time())
                out_vid = out_folder / f"quote_voice_{st.session_state.selected_voice.lower()}_{timestamp}.mp4"

                with st.spinner("Đang xử lý: Tạo giọng đọc Gemini -> Ghép typography chống lóa -> Hòa âm FFmpeg..."):
                    try:
                        # 1. Đảm bảo có file giọng đọc
                        voice_file, voice_dur = synthesize_voice(
                            text=st.session_state.quote_text,
                            voice_name=st.session_state.selected_voice,
                            output_path=f"temp/voice_for_video_{timestamp}.wav"
                        )

                        # 2. Nhạc nền nếu bật
                        bgm_file = "assets/bgm/lofi_ambient.m4a" if st.session_state.enable_bgm and Path("assets/bgm/lofi_ambient.m4a").exists() else None

                        # 3. Dựng video hoàn chỉnh
                        compose_quote_video(
                            bg_media_path=bg_target,
                            quote=st.session_state.quote_text,
                            voice_wav_path=voice_file,
                            output_path=out_vid,
                            duration_mode=st.session_state.duration_mode,
                            signature=st.session_state.signature,
                            bgm_path=bgm_file,
                            bgm_volume=0.14,
                        )

                        st.session_state.rendered_video = str(out_vid)
                        st.toast("Tạo video thành công 100%!", icon="🎉")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Lỗi khi dựng video: {err}")


# ==============================================================================
# CỘT PHẢI: KHUNG ĐIỆN THOẠI XEM TRƯỚC (LIVE PHONE MOCKUP) & TẢI XUỐNG
# ==============================================================================
with col_preview:
    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
            <div class="step-title" style="font-size: 1.1rem;">Khung Xem Trước Trực Quan</div>
            <div style="font-size: 0.78rem; font-weight: 700; color: #38BDF8; background: rgba(15,23,42,0.85); border: 1px solid rgba(56,189,248,0.3); padding: 3px 10px; border-radius: 20px;">
                ● LIVE 9:16
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    rendered_vid = st.session_state.rendered_video
    bg_target = st.session_state.bg_media
    quote_ready = bool(st.session_state.quote_text.strip())

    # Khung điện thoại
    if rendered_vid and Path(rendered_vid).exists():
        st.markdown(
            """
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); color: #34D399; padding: 6px 14px; border-radius: 10px; font-size: 0.82rem; font-weight: 700; margin-bottom: 10px; text-align: center;">
                ▶️ Video đã tạo xong! Bấm nút Play bên dưới để xem & nghe thử trước khi tải về máy
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div class="phone-mockup-wrapper">
            <div class="phone-notch">
                <div style="width:6px; height:6px; background:#1E293B; border-radius:50%;"></div>
                <div style="width:28px; height:3px; background:#334155; border-radius:3px;"></div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Hiển thị Video thành phẩm (nếu đã render) HOẶC Realtime Live Composite Preview
    if rendered_vid and Path(rendered_vid).exists():
        st.video(str(rendered_vid))
    elif bg_target and Path(bg_target).exists():
        is_video = Path(bg_target).suffix.lower() in [".mp4", ".mov", ".webm"]
        if is_video:
            st.video(str(bg_target))
            st.caption("ℹ️ Đây là video footage nền gốc. Bấm 'Xuất Video' để phủ typography và lồng giọng đọc.")
        else:
            try:
                with Image.open(bg_target) as raw_bg:
                    bg_rgba = raw_bg.convert("RGBA")
                    if bg_rgba.size != (1080, 1920):
                        bg_rgba = bg_rgba.resize((1080, 1920), Image.Resampling.LANCZOS)

                    bg_rgb = bg_rgba.convert("RGB")
                    enhancer = ImageEnhance.Brightness(bg_rgb)
                    bg_graded = enhancer.enhance(0.88).convert("RGBA")

                    text_overlay = create_quote_overlay(
                        quote=st.session_state.quote_text,
                        signature=st.session_state.signature or "@quote_channel",
                        enable_gradient_scrim=True,
                    )
                    preview_composite = Image.alpha_composite(bg_graded, text_overlay)
                    st.image(preview_composite.convert("RGB"), use_container_width=True)
            except Exception as ex:
                logger.warning(f"Preview error: {ex}")
                st.image(bg_target, use_container_width=True)
    else:
        st.info("Chưa có ảnh/video nền. Tải ở Bước 3 để hiển thị xem trước.")

    st.markdown("</div>", unsafe_allow_html=True)  # Kết thúc phone-mockup-wrapper

    # 2. DASHBOARD THÔNG SỐ VÀ NÚT TẢI XUỐNG
    if rendered_vid and Path(rendered_vid).exists():
        from modules.video_composer import probe_media_duration
        dur = probe_media_duration(rendered_vid)
        file_size_mb = Path(rendered_vid).stat().st_size / (1024 * 1024)

        st.markdown(
            f"""
            <div class="meta-box">
                <div>
                    <div class="meta-val">1080×1920</div>
                    <div class="meta-lbl">Độ phân giải</div>
                </div>
                <div>
                    <div class="meta-val">{dur:.1f}s</div>
                    <div class="meta-lbl">Thời lượng</div>
                </div>
                <div>
                    <div class="meta-val">{st.session_state.selected_voice}</div>
                    <div class="meta-lbl">Giọng đọc</div>
                </div>
                <div>
                    <div class="meta-val">{file_size_mb:.1f} MB</div>
                    <div class="meta-lbl">Dung lượng</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with open(rendered_vid, "rb") as vf:
            st.download_button(
                label="⬇️ TẢI VIDEO XUỐNG (.MP4)",
                data=vf.read(),
                file_name=f"tiktok_quote_voice_{int(time.time())}.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True,
            )
        st.caption(f"📁 File đã lưu tại: `{rendered_vid}`")
    else:
        st.markdown(
            """
            <div style="text-align: center; color: #64748B; font-size: 0.82rem; margin-top: 0.8rem;">
                💡 Chữ trên khung điện thoại được cập nhật theo thời gian thực (Realtime Safe Zone).
            </div>
            """,
            unsafe_allow_html=True,
        )
