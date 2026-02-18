# Smart Development Handbook: Cẩm nang Phát triển Tool Blender Thông minh

Tài liệu này tổng hợp các nguyên tắc cốt lõi giúp xây dựng Rail Flow Blender: Mạnh mẽ, Modular và chuẩn Style Blender.

> [!WARNING]
> ## 🔄 AI Mandatory Refresh Point
> 
> **STOP! Trước khi tiếp tục, AI hãy tự kiểm tra:**
> 1. 🇻🇳 Tôi đang trả lời bằng **TIẾNG VIỆT** chưa?
> 2. 🏗️ Code changes có tuân thủ **Blender Modular Architecture** bên dưới không?
> 3. 🧩 Có dùng `bmesh` cho các thao tác lưới phức tạp không?
> 
> **NẾU QUÊN** → User sẽ nhắc "đọc lại cẩm nang kỹ thuật"

---

## 🏗️ 1. Kiến trúc Modular (Blender Standard)

**QUY TẮC VÀNG: Chia nhỏ để trị.** Không đem tư duy "Monolith" (file 5000 dòng) của Maya sang Blender.

- **`rf_core/`**: Logic thuần túy (Math, Geometry, Algorithms). Không chứa code UI.
    - *Ví dụ*: `patch_generator.py`, `acceleration.py`.
- **`rf_operators/`**: Xử lý hành động (Operators). Mỗi file một nhiệm vụ.
    - *Ví dụ*: `op_rail.py` (Vẽ Rail), `op_tube.py` (Vẽ Tube).
- **`rf_ui/`**: Giao diện (Panels, Menus).
    - *Ví dụ*: `panel_main.py`, `panel_settings.py`.
- **`rf_properties/`**: Chứa Data Models (`PropertyGroup`). Nơi lưu trữ duy nhất của mọi thông số.

## ⚡ 2. Chiến lược Cập nhật Lưới (Mesh Update Strategy)

Trong Blender, việc cập nhật lưới phải cực kỳ tối ưu để đạt 60FPS:

- **Edit Mode vs Object Mode**: 
    - Tránh chuyển đổi Mode (`bpy.ops.object.mode_set`) liên tục trong vòng lặp. Nó rất chậm.
    - Ưu tiên dùng `bmesh` để chỉnh sửa lưới trực tiếp trong bộ nhớ.
- **Delta Updates**: Khi user kéo slider (Radius, Divisions), hãy tính toán vị trí mới và gán lại (`foreach_set`), đừng xóa object và tạo lại (`new`) trừ khi topology thay đổi.
- **GPU Drawing**: Sử dụng `gpu` module để vẽ preview (nét vẽ, điểm snap) thay vì tạo object tạm (Locator/Empty). Object tạm làm rác Outliner và chậm scene.

## 🚀 3. Tối ưu hiệu năng (Performance First)

- **Mathutils**: Luôn dùng `mathutils.Vector`, `Matrix` cho tính toán vector. Nó được viết bằng C, nhanh hơn Python list rất nhiều.
- **BVHTree / KDTree**: Sử dụng `mathutils.bvhtree` hoặc `kdtree` cho các tác vụ Snap/Raycast lên mesh nguồn mật độ cao. Đừng dùng `obj.ray_cast` trong vòng lặp lớn.
- **Foreach Access**: Khi thao tác với mảng lớn (Vertex coords), dùng `vertices.foreach_get` và `foreach_set` thay vì lặp Python thuần. Tốc độ chênh lệch có thể lên tới 100 lần.

## 🧹 4. Nguyên tắc "Chống mã rác" (Anti-Clutter)

- **Single Source of Truth**: Mọi thông số (Width, Divisions) phải được lưu trong `Scene.railflow_settings` (PropertyGroup). Không lưu trong biến toàn cục (Global Variable) hay biến instance rời rạc.
- **Lifecycle Management**: Blender không tự dọn dẹp biến Python khi reload script. Hãy dùng hàm `unregister()` để xóa sạch PropertyGroup, Handler và Cache.
- **Metadata Persistence**: Mesh tạo ra phải mang theo thông tin (`obj["rail_data"]`) để có thể Rebuild sau này. Đừng tạo ra "Dead Mesh" (Mesh chết, không chỉnh sửa được).

## 🛡️ 5. Quy trình Fix & Update

1.  **Audit**: Dùng `grep` tìm kiếm xem logic này có được dùng ở Operators nào khác không.
2.  **Operator Poll**: Luôn kiểm tra `context.area.type == 'VIEW_3D'` trong hàm `poll()` để tránh lỗi khi gọi từ Console hay Outliner.
3.  **Undo Safety**: Luôn thêm `bl_options = {'REGISTER', 'UNDO'}` cho Operator thay đổi dữ liệu scene.

## 🎨 6. Tôn trọng Giao diện (UI Consistency)

- **Blender Native Look**: Sử dụng Layout chuẩn của Blender (`layout.prop`, `layout.operator`). Đừng cố tạo UI "lạ" trừ khi dùng `gpu` vẽ trong Viewport.
- **N-Panel**: Tool nằm gọn trong Sidebar (N-Panel). Đừng chiếm dụng không gian không cần thiết.

## ⚠️ 7. Cảnh báo về Context (Context is King)

> [!CAUTION]
> **Context trong Blender thay đổi liên tục.**
> `bpy.context.active_object` có thể là `None` hoặc sai object nếu chuột user đang lướt qua Outliner.
> **Quy tắc**: Luôn kiểm tra Context hợp lệ trước khi chạy logic. Nếu cần chắc chắn, hãy truyền object cụ thể vào hàm thay vì dựa vào Active Object.

## 🐞 8. Kỹ thuật Debug

- **Console System**: Mở Window > Toggle System Console để xem log. Blender không hiện lỗi Python chi tiết trong Info Area.
- **Visual Debug**: Tương tự Maya, hãy dùng `gpu` module để vẽ các đường line/point màu đỏ/xanh lên Viewport để kiểm tra thuật toán Raycast.

---
*Phiên bản 1.0 - Adapted for Rail Flow Blender*

---

## 🚀 9. Blender 4.2+ Compatibility Standards (New Era)
Blender 4.2 mang đến những thay đổi lớn về Eevee (Next) và hệ thống Addon.

### A. Eevee Next & Materials
1.  **Shadow Method Removed**: Thuộc tính `shadow_method` không còn tồn tại trong Eevee Next.
    - **Fix**: Luôn dùng `try-except AttributeError` khi set `shadow_method`.
2.  **Raytracing**: Eevee Next mặc định bật Raytracing. Cần kiểm tra hiệu năng khi vẽ nhiều object trong suốt.
3.  **Jitter**: Một số hiệu ứng Overlay cũ có thể bị rung (jitter) do TAA mới.

### B. Python API Changes
1.  **Mesh Auto-Smooth**: Đã bị loại bỏ trong 4.1/4.2.
    - **Fix**: Dùng Modifier `Smooth by Angle` hoặc `mesh.shade_smooth()` kết hợp edge data đúng cách.
    - **Không dùng**: `mesh.use_auto_smooth = True` (sẽ báo lỗi).
2.  **Shader Node Tree**: Kiểm tra `mat.node_tree` tồn tại trước khi truy cập `nodes`.

### C. Extension Manifesto & Blender 5.0+
Dù Rail Flow hiện tại là Legacy Addon, hãy chuẩn bị cho tương lai (Blender 5.0+):
-   **Extensions Platform**: Blender 5.0 có thể ép buộc dùng hệ thống Extensions. Cần sẵn sàng đóng gói `manifest.toml`.
-   **GPU Module**: API vẽ `gpu` có thể thay đổi. Hạn chế dùng các hàm `gpu.shader.from_builtin` cũ.
-   **Defensive Coding**: Luôn dùng `try-except` cho các tính năng mới/bị loại bỏ (như `shadow_method` hay `auto_smooth`).
-   Không ghi hardcode path vào `Program Files`.
-   Lưu user preferences vào `addon_preferences` thay vì config file rời nếu có thể.
