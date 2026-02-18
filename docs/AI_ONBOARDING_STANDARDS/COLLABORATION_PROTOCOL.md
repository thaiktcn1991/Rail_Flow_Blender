# Collaboration Protocol: Antigravity AI & User (Blender)

Quy trình này thiết lập các tiêu chuẩn cộng tác giữa AI và người dùng cho dự án Rail Flow Blender.

> [!CAUTION]
> ## 🧠 AI Memory Safeguards (Bảo vệ Trí nhớ AI)
> 
> **VẤN ĐỀ**: AI thường quên context khi session kéo dài.
> 
> **GIẢI PHÁP - AI PHẢI LÀM SAU MỖI LẦN FIX BUG:**
> 1. ✍️ Cập nhật `docs/notes/DAILY_DEVELOPMENT_LOG.md` (nếu có).
> 2. 🇻🇳 Kiểm tra: "Tôi đang trả lời bằng tiếng Việt 100% chưa?"
> 3. 📖 Đọc lại `SMART_DEV_HANDBOOK.md` để nhớ Architecture.

## 🛠 Quy Tắc Cơ Bản (Core Rules)

1.  **Ngôn ngữ**: **Tiếng Việt** là bắt buộc.
2.  **Atomic Edits**: Sửa nhỏ, Test ngay. Tránh sửa hàng loạt file gây loạn.
3.  **Blender Convention**: Tuân thủ PEP-8 (snake_case cho biến/hàm, PascalCase cho Class).
    - `Use`: `bpy.types.Operator`, `bpy.props`.
    - `Avoid`: `CamelCase` cho tên hàm (trừ khi override API Qt cũ nếu có).

## 🚀 Dự Án Rail Flow Blender (V1.1+)

1.  **Modularization**:
    - `rf_core`: Logic thuần túy (Geometry, Math). Không dính UI.
    - `rf_operators`: Các Modal Operators (`op_rail.py`, `op_tube.py`).
    - `rf_ui`: Panel và Menu.
    - `rf_properties`: PropertyGroups (`settings.py`).
2.  **Centralized State**:
    - Mọi setting lưu trong `Scene.railflow_settings`.
    - Không dùng biến toàn cục (Global Variables) bừa bãi.

## 📝 Quản Lý Phiên Bản (Blender 4.2+)

Khi viết code hoặc tài liệu, phải lưu ý sự khác biệt của Blender 4.2 (LTS mới):
1.  **Eevee Next**: Shadow và Transparency thay đổi API.
2.  **Extensions**: Addon structure thay đổi (dù ta vẫn hỗ trợ Legacy install).
3.  **Python 3.11**: Blender 4.0+ dùng Python 3.10/3.11. Cẩn thận các tính năng cũ bị deprecated.

## 🔍 Đánh Giá Tác Động

- Sửa `patch_generator.py`? -> Kiểm tra ngay X-Ray Visuals trên Viewport.
- Sửa `op_rail.py`? -> Kiểm tra Modal State (ESC có thoát không?).

---
*Giao thức này đảm bảo Rail Flow Blender phát triển bền vững và ổn định.*
