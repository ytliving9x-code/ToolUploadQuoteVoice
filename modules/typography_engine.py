import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger("quote_voice.typography")

DEFAULT_FONT = Path("assets/fonts/BeVietnamPro-Bold.ttf")


def get_vietnamese_font(font_size: int = 44, font_path: Optional[Path | str] = None) -> ImageFont.FreeTypeFont:
    """Tải font chữ tiếng Việt hỗ trợ dấu đầy đủ."""
    candidates = []
    if font_path:
        candidates.append(Path(font_path))
    candidates.extend([
        DEFAULT_FONT,
        Path("assets/fonts/BeVietnamPro-SemiBold.ttf"),
        Path("assets/fonts/Montserrat-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf")
    ])

    for target in candidates:
        if target.exists():
            try:
                return ImageFont.truetype(str(target), font_size)
            except Exception:
                pass

    return ImageFont.load_default()


def wrap_quote_to_lines(text: str, font: ImageFont.FreeTypeFont, max_width: int = 860) -> List[str]:
    """
    Tự động ngắt dòng văn bản tiếng Việt thành từng câu trọn nghĩa,
    không để từ bị ngắt giữa chừng và không vượt quá chiều rộng vùng an toàn 860px.
    """
    clean_text = " ".join(text.strip().split())
    words = clean_text.split(" ")
    lines: List[str] = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]

        if line_w <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def create_quote_overlay(
    quote: str,
    canvas_size: Tuple[int, int] = (1080, 1920),
    margin_left: int = 90,
    margin_right: int = 180,   # Tránh cụm icon thả tim/comment bên phải TikTok
    margin_bottom: int = 420,  # Cách đáy tránh thanh caption & nhạc TikTok
    line_spacing: int = 22,
    font_size: int = 42,
    signature: Optional[str] = "@quote_channel",
    signature_font_size: int = 24,
    enable_gradient_scrim: bool = True,
    scrim_max_alpha: int = 160,
    shadow_blur_radius: float = 4.5,
    stroke_width: int = 1,
    font_path: Optional[Path | str] = None,
) -> Image.Image:
    """
    Tạo ảnh PNG RGBA 1080x1920 chứa Typography chữ và chữ ký:
    - Safe Zone TikTok chuẩn 9:16.
    - Lớp màng gradient chống loá chân chữ.
    - Đổ bóng mờ (soft shadow) nhiều lớp giúp chữ luôn rõ trên nền sáng hoặc tối.
    """
    W, H = canvas_size
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    if not quote.strip():
        return overlay

    font = get_vietnamese_font(font_size=font_size, font_path=font_path)
    sig_font = get_vietnamese_font(font_size=signature_font_size, font_path=font_path)

    # Chiều rộng tối đa cho text
    max_text_width = W - margin_left - margin_right
    lines = wrap_quote_to_lines(quote, font, max_width=max_text_width)

    # Tính toán kích thước khối text
    dummy_img = Image.new("RGBA", (1, 1))
    draw_dummy = ImageDraw.Draw(dummy_img)

    line_heights = []
    line_widths = []
    for line in lines:
        bbox = draw_dummy.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    total_quote_height = sum(line_heights) + line_spacing * (len(lines) - 1)

    # Tính chiều cao chữ ký
    sig_h = 0
    if signature and signature.strip():
        sig_bbox = draw_dummy.textbbox((0, 0), signature.strip(), font=sig_font)
        sig_h = sig_bbox[3] - sig_bbox[1] + 18  # Khoảng cách phía trên chữ ký

    total_block_h = total_quote_height + sig_h

    # Tọa độ Y xuất phát (đặt chữ ở 1/3 dưới, trên vùng an toàn đáy)
    start_y = H - margin_bottom - total_block_h

    # 1. Vẽ Gradient Scrim chống loá (nếu bật)
    if enable_gradient_scrim:
        scrim_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        scrim_draw = ImageDraw.Draw(scrim_layer)
        scrim_start_y = max(0, start_y - 120)
        scrim_end_y = min(H, H - margin_bottom + 80)
        scrim_range = max(1, scrim_end_y - scrim_start_y)

        for y in range(scrim_start_y, scrim_end_y):
            progress = (y - scrim_start_y) / scrim_range
            alpha = int(scrim_max_alpha * (progress ** 1.3))
            scrim_draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))

        overlay = Image.alpha_composite(overlay, scrim_layer)

    # 2. Tạo layer bóng đổ mờ (Shadow Layer)
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)

    curr_y = start_y
    for i, line in enumerate(lines):
        # Đổ bóng chữ
        shadow_draw.text(
            (margin_left + 2, curr_y + 3),
            line,
            font=font,
            fill=(0, 0, 0, 230),
            stroke_width=stroke_width + 1,
            stroke_fill=(0, 0, 0, 230)
        )
        curr_y += line_heights[i] + line_spacing

    if signature and signature.strip():
        curr_y += 18
        shadow_draw.text(
            (margin_left + 2, curr_y + 2),
            signature.strip(),
            font=sig_font,
            fill=(0, 0, 0, 200)
        )

    # Áp dụng bộ lọc mờ (Blur) cho bóng
    if shadow_blur_radius > 0:
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(shadow_blur_radius))
    overlay = Image.alpha_composite(overlay, shadow_layer)

    # 3. Tạo layer chữ chính màu trắng sắc nét (Main Text Layer)
    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)

    curr_y = start_y
    for i, line in enumerate(lines):
        text_draw.text(
            (margin_left, curr_y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=stroke_width,
            stroke_fill=(0, 0, 0, 180)
        )
        curr_y += line_heights[i] + line_spacing

    if signature and signature.strip():
        curr_y += 18
        text_draw.text(
            (margin_left, curr_y),
            signature.strip(),
            font=sig_font,
            fill=(203, 213, 225, 230), # Màu xám bạc tinh tế
        )

    overlay = Image.alpha_composite(overlay, text_layer)
    return overlay
