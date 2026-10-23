import random
from typing import Dict, List, Optional
from modules.voice_service import get_gemini_api_key

TOPIC_QUOTES: Dict[str, List[str]] = {
    "🌱 Triết lý & Trưởng thành": [
        "Hành trình vạn dặm luôn bắt đầu bằng một bước chân đầu tiên.",
        "Trưởng thành là khi nhận ra, sự im lặng đôi khi là câu trả lời có sức nặng nhất.",
        "Cuộc đời không phải là cuộc đua với người khác, mà là vượt qua chính mình của ngày hôm qua.",
        "Càng trải qua nhiều sóng gió, người ta càng trân quý những ngày bình dị, an yên.",
        "Không có con đường nào bằng phẳng dẫn đến những vùng đất rực rỡ.",
        "Biết đủ là giàu có, biết buông bỏ là tự do."
    ],
    "💼 Tiền bạc & Sự nghiệp": [
        "Kỷ luật là chiếc cầu nối duy nhất giữa mục tiêu và thành tựu.",
        "Đừng bao giờ đánh đổi giấc ngủ của tuổi trẻ để rồi mua lại sức khỏe lúc về già.",
        "Người thức dậy lúc bình minh chưa chắc đã giàu, nhưng người có mục tiêu rõ ràng chắc chắn sẽ về đích.",
        "Giá trị của bạn không nằm ở số tiền trong ví, mà nằm ở năng lực tạo ra giá trị cho người khác.",
        "Cơ hội thường ngụy trang dưới hình hài của sự chăm chỉ và kiên trì."
    ],
    "🔥 Bản lĩnh & Vượt khó": [
        "Cuộc sống không phải là chờ đợi cơn bão qua đi, mà là học cách nhảy múa dưới cơn mưa.",
        "Kim cương chỉ được tạo ra dưới áp lực nghìn tấn. Đừng sợ nghịch cảnh.",
        "Ngã bảy lần, đứng dậy tám lần. Kẻ bỏ cuộc không bao giờ thắng.",
        "Khi mọi thứ dường như chống lại bạn, hãy nhớ máy bay cất cánh ngược chiều gió.",
        "Nỗi đau hôm nay sẽ trở thành sức mạnh vững chắc của bạn vào ngày mai."
    ],
    "🌙 Đêm muộn & Lắng đọng": [
        "Những đêm không ngủ không phải vì mất ngủ, mà vì tâm trí vẫn mải miết đi tìm bình yên.",
        "Sau cánh cửa khép lại của một ngày dài, bạn chỉ cần thành thật với chính mình.",
        "Có những nỗi buồn không thể nói ra thành lời, chỉ biết gửi gắm vào làn gió đêm.",
        "Thành phố về đêm thật đẹp, nhưng lòng người cô đơn thì ở đâu cũng thấy chênh vênh.",
        "Cảm ơn bản thân vì sau tất cả những mệt mỏi, vẫn kiên cường đi hết một ngày dài."
    ],
    "🍃 Chữa lành & Bình yên": [
        "Bình yên đến từ bên trong, đừng bao giờ mải miết tìm kiếm nó ở thế giới bên ngoài.",
        "Hãy đối xử dịu dàng với chính mình, bạn đã làm rất tốt rồi.",
        "Mỗi ngày mới là một cơ hội để bắt đầu lại, nhẹ nhàng hơn và sâu sắc hơn.",
        "Mặt trời rồi sẽ mọc, hoa rồi sẽ nở, và bạn rồi sẽ ổn thôi.",
        "Hạnh phúc thực ra rất đơn giản: Một mái nhà để về, một tách trà ấm và lòng không bận lòng."
    ]
}


def get_random_quote(topic: Optional[str] = None) -> str:
    """Lấy ngẫu nhiên một câu quote từ danh mục chủ đề."""
    if topic and topic in TOPIC_QUOTES:
        return random.choice(TOPIC_QUOTES[topic])
    all_quotes = [q for quotes in TOPIC_QUOTES.values() for q in quotes]
    return random.choice(all_quotes)


def generate_ai_quote(topic: str = "Trưởng thành", api_key: Optional[str] = None) -> str:
    """Tạo câu quote độc bản bằng Gemini AI với fallback tự động."""
    key = get_gemini_api_key(api_key)
    if not key:
        return get_random_quote(topic)

    try:
        from google import genai
        client = genai.Client(api_key=key)

        prompt = (
            f"Hãy viết 1 câu danh ngôn hoặc câu trích dẫn ngắn (12 - 25 từ) về chủ đề: '{topic}'. "
            f"Văn phong: Độc thoại sâu sắc, đằm thắm, giàu trải nghiệm, không sáo rỗng, đọc thấm thía. "
            f"Chỉ trả về duy nhất nội dung câu trích dẫn tiếng Việt, không kèm giải thích hoặc dấu ngoặc kép."
        )

        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        quote = resp.text.strip().strip("\"'“”")
        if quote and len(quote) > 10:
            return quote
    except Exception:
        pass

    return get_random_quote(topic)
