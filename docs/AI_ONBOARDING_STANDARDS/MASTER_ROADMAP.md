# 🗺️ Rail Flow Blender Roadmap

Kế hoạch phát triển Rail Flow phiên bản Blender, dựa trên kiến trúc Modular và Feature Parity với Maya.

---

## 🏗️ Giai đoạn 1: Foundation (Hiện Tại - V1.1)

**Mục tiêu**: Xây dựng nền tảng vững chắc, Modular Architecture, và sửa lỗi logic cơ bản.

*   **P0 - Core Refactor (Xong):** Chia nhỏ code từ `__init__.py` và `main_panel.py` sang `rf_core`, `rf_operators`, `rf_properties` và `rf_ui`.
*   **P1 - Metadata Storage (Xong - V1.1):** Lưu trữ thông số vào object để có thể chỉnh sửa lại sau khi tạo mesh.
*   **P2 - Interactive Updates (Xong - V1.1):** Hỗ trợ chỉnh U/V bằng thanh trượt hoặc lăn chuột trong lúc vẽ.
*   **P3 - Documentation (Xong):** Port bộ tài liệu chuẩn `SMART_DEV_HANDBOOK` từ Maya sang.

---

## 🚀 Giai đoạn 2: Feature Parity (Maya -> Blender)

**Mục tiêu**: Mang các tính năng mạnh mẽ nhất của bản Maya sang Blender.

### 1. Poly Draw Mode (Enhanced)
*   **Snap Logic Revolution**: Áp dụng thuật toán Hybrid CPOM + Normal Consistency (V23.53) từ Maya sang Blender để vẽ trên mặt cong phức tạp mà không bị lỗi.
*   **Stroke Stabilization**: Làm mượt nét vẽ bằng `stroke_smooth` (tương tự Lazy Mouse).

### 2. Poly Strip Mode & Bridge Mode
*   **Port Logic**: Chuyển đổi logic sinh lưới Bridge/Strip từ Maya `rf_core` sang Blender.
*   **Geometric Check**: Áp dụng fix "Mặt Đen" (Closed Loop Normal Check V23.58) ngay từ đầu.

### 3. Tube & Pipe Mode
*   **Adaptive Radius**: Tính bán kính dựa trên độ dày vật thể (Raycast xuyên qua).
*   **Caps**: Tự động đóng nắp tube.

### 4. Mirror & Symmetry
*   **Live Mirror**: Sử dụng Modifier `Mirror` của Blender nhưng quản lý tự động bởi Operator (Auto-Apply khi cần).

---

## 💡 Giai đoạn 3: Optimization & Polish

*   **GPU Drawing**: Tối ưu hóa việc vẽ wireframe/points trong Viewport bằng `gpu` module để đạt 60FPS.
*   **Keymap Customization**: Cho phép người dùng chỉnh sửa phím tắt trong Preferences.
*   **Auto-Updater**: Tự động kiểm tra phiên bản mới từ GitHub.

---
*Roadmap updated: 18/02/2026 for Blender Edition*
