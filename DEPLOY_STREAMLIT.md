# 🚀 Hướng Dẫn Deploy ToolUploadQuoteVoice Lên Streamlit Cloud

Dự án đã được cấu hình chuẩn hóa 100% để triển khai lên **Streamlit Community Cloud (Miễn phí 100%)**:
- Đã có file `packages.txt` (để máy chủ Linux cài FFmpeg tự động).
- Đã có file `requirements.txt` (các thư viện Python cần thiết).
- Đã cấu hình `.streamlit/config.toml` (giao diện Dark Theme cao cấp).
- Code đã hỗ trợ tự động đọc `st.secrets["GEMINI_API_KEY"]`.

---

## BƯỚC 1: Tạo Repository Trên GitHub & Push Code

1. Truy cập [github.com/new](https://github.com/new) và tạo một repository mới:
   - **Repository name**: `ToolUploadQuoteVoice`
   - **Public / Private**: Tùy bạn chọn (Private vẫn deploy được trên Streamlit Cloud).
   - **Không tích chọn** "Add a README file" hay .gitignore (vì máy bạn đã có sẵn).
   - Nhấn **Create repository**.

2. Mở PowerShell tại thư mục `d:\ToolUploadQuoteVoice` và chạy 2 lệnh sau:
   ```powershell
   git remote add origin https://github.com/ytliving9x-code/ToolUploadQuoteVoice.git
   git push -u origin main
   ```

---

## BƯỚC 2: Triển Khai Lên Streamlit Community Cloud

1. Truy cập trang quản trị Streamlit: [share.streamlit.io](https://share.streamlit.io/) (đăng nhập bằng tài khoản GitHub của bạn).
2. Nhấn nút **"Create app"** (hoặc **"New app"**).
3. Điền các thông tin:
   - **Repository**: `ytliving9x-code/ToolUploadQuoteVoice`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. **CẤU HÌNH API KEY (Quan trọng)**:
   - Nhấp vào mục **Advanced settings** (Cài đặt nâng cao).
   - Tại ô **Secrets**, dán dòng sau vào:
     ```toml
     GEMINI_API_KEY = "your_gemini_api_key_here"
     ```
5. Nhấn nút **"Deploy!"** và đợi khoảng 1-2 phút.

---

🎉 Sau khi xong, bạn sẽ có một đường link công khai dạng:
`https://tooluploadquotevoice.streamlit.app` để truy cập và tạo video từ bất kỳ thiết bị nào (kể cả điện thoại)!
