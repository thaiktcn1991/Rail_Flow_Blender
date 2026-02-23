# Daily Development Log: Rail Flow Blender

> [!IMPORTANT]
> **TẠI SAO CẦN NHẬT KÝ NÀY?**
> Theo COLLABORATION_PROTOCOL.md, AI phải ghi lại tiến độ, sai lầm và bài học sau mỗi session để duy trì "bộ nhớ ngoài" cho dự án, giúp tránh lặp lại các lỗi kỹ thuật trong tương lai.

## [2026-02-18] - Porting "Pro" Safety & Maya Parity

### 0. Debug Header
- **Hệ điều hành**: Windows
- **Phiên bản Blender**: 4.0+ (LTS)
- **Mục tiêu**: Đạt mức Feature Parity 100% với bản Maya "Nitro", tập trung vào độ ổn định và an toàn dữ liệu.

### 1. Phát hiện Lỗi (The Discovery)
- **Lỗi Snapping**: Khoảng cách snap bị sai lệch khi Source Mesh có Scale không đồng nhất (Non-uniform scale). Nguyên nhân do tính toán trong Local Space.
- **Lỗi Z-Fighting**: Mesh mới tạo bị chìm vào trong bề mặt nguồn, gây khó khăn cho việc Snap và Select.
- **Lỗi UI Registration**: Sau khi thêm các logic mới, tool biến mất khỏi Sidebar do thiếu `import` thư viện `acceleration` và `patch_generator` trong `rf_ui/main_panel.py`.
- **Lỗi Normal Flip**: Khi thay đổi U/V Divisions, mesh thỉnh thoảng bị lật mặt (đen) do Blender tạo lại mesh data mà không kế thừa hướng mặt cũ.
- **Lỗi Multi-Rail U-Divisions**: Khi vẽ 3 hoặc 4 rail, thanh trượt U Divisions không hoạt động do logic code cũ chỉ hỗ trợ nội suy giữa 2 rail.
- **Lỗi Multi-Rail Crash**: Lỗi `NameError: final_cols` khi nhấn Enter để tạo mesh ở chế độ Multi-Rail.

### 2. Quá trình Vật lộn (The Struggle)
- **Attempt 1 (Snapping)**: Cố gắng dùng `Apply Scale` tự động. -> Thất bại vì User không muốn làm thay đổi dữ liệu của họ (Destructive).
- **Attempt 2 (UI)**: Thêm logic popup nhưng dùng `bpy.ops` sai context. -> Panel không đăng ký được.
- **Bế tắc**: Từng có lúc tool biến mất hoàn toàn khiến user lo lắng: "K thấy tool".

### 3. Giải pháp & Bài học (The Lesson)
- **Giải pháp**:
    1. **World Space Snapping**: Toàn bộ logic tìm điểm gần nhất và tính khoảng cách đã được chuyển sang World Space (`obj.matrix_world @ loc`).
    2. **Surface Offset**: Thêm 0.001 offset theo hướng Normal ngay sau khi snap để "nhấc" mesh lên trên mặt nguồn.
    3. **Interactive Transform Check**: Implement `RAILFLOW_OT_set_source_confirm` (Modal Popup) để cảnh báo user "Freeze Transform" giống Maya.
    4. **Orientation Persistence**: Capture `old_avg_norm` trước khi rebuild và dùng Dot Product để tự động lật mặt nếu mesh mới bị ngược hướng.
    5. **Sanitize Imports**: Luôn double-check header của file sau khi dùng `replace_file_content`.
    6. **Multi-Stroke Interpolation**: Viết lại thuật toán nội suy cho Multi-Rail, cho phép chia nhỏ (divide) không gian U giữa bất kỳ số lượng rail nào.
    7. **Forced Prop Sync**: Sửa logic trong `settings.py` để ép buộc đồng bộ mọi thông số (U, V, Radius...) vào object ngay khi slider di chuyển.
    8. **Bugfix (Multi-Rail Crash)**: Khởi tạo biến `final_cols = []` trước khi chạy vòng lặp nội suy để tránh lỗi NameError.

- **Bài học**:
    - **Context is King**: Trong Blender, việc gọi `invoke_props_dialog` yêu cầu Operator phải được đăng ký và gọi đúng cách qua `INVOKE_DEFAULT`.
    - **Don't touch Source Data**: Luôn luôn làm việc trên bản sao hoặc dùng World Space math thay vì ép User phải `Apply Scale`.
    - **Visual Style**: Maya users rất nhạy cảm với độ dày của Wireframe (`0.008`) và tính năng X-Ray. Phải đảm bảo `use_even_offset=True` cho modifier Wireframe.

### 4. Kết quả
- [x] Snapping độc lập với Scale.
- [x] X-Ray đạt chuẩn Maya (Bold black edges, cyan surface).
- [x] Hệ thống bảo mật (Transform/Polycount) đã hoạt động.
- [x] Sửa lỗi mất Tool Tab.
- [x] Multi-Rail U-Divisions hoạt động 100% với Slider.
- [x] Sửa lỗi crash (NameError) khi tạo Multi-Rail mesh.
- [x] Lưu trữ tài liệu kỹ thuật (V2 Interpolation) vào repo Maya (`docs/Futures`).
- [x] Tái cấu trúc UI theo chuẩn Maya (Contextual Settings xuất hiện dưới nút Mode khi active).
- [x] Sửa lỗi `AttributeError: generate_mesh` và kích hoạt hệ thống phát hiện lỗi Nitro (Try/Except) cấp tốc.

---

## [2026-02-23] - Hybrid CPOM Snap Revolution (V1.2)

### 0. Debug Header
- **Hệ điều hành**: Windows
- **Phiên bản Blender**: 4.2 / 5.0
- **Mục tiêu**: Port thuật toán Hybrid CPOM từ Maya V23.50-V23.53 để fix lỗi mesh không snap vào surface.

### 1. Phát hiện Lỗi (The Discovery)
- **Lỗi Snap Surface**: Single Rail mesh bay ra ngoài, không bám sát surface ở các vùng mép lồi (convex silhouette).
- **Nguyên nhân**: Logic snap cũ (`smart_raycast_snap`) chỉ dùng bidirectional raycast đơn giản, thiếu:
  - Normal Consistency check (Dot Product)
  - Hybrid fallback với CPOM
  - Projective Preservation
- **Lỗi Crash Blender 5.0**: Icon `KEYINGSET_ADD` không tồn tại trong Blender 5.0 → crash khi reload addon.

### 2. Giải pháp (The Solution)
- **Port Hybrid CPOM từ Maya**:
  1. **CPOM Fallback**: Luôn tìm closest point làm baseline
  2. **Bidirectional Raycast**: Forward + Backward rays
  3. **Normal Consistency (V23.51)**: Check dot product, phạt +1000 nếu back-face
  4. **Projective Preservation (V23.52)**: Bonus -0.1 cho raycast results

- **Files thay đổi**:
  - `rf_core/acceleration.py`: Thêm hàm `hybrid_cpom_snap()`
  - `rf_core/patch_generator.py`: Cập nhật `generate_quad_patch()`, `generate_multi_rail_patch()`, `generate_bridge_patch()` dùng hybrid snap
  - `rf_ui/main_panel.py`: Fix icon `KEYINGSET_ADD` → `PREFERENCES`
  - `rf_properties/settings.py`: Thêm `wire_thickness` property (điều chỉnh độ dày wireframe)

### 3. Bài học (The Lesson)
- **Maya Code là "Gold"**: Các thuật toán đã được tinh chỉnh qua nhiều version (V23.50-V23.53) nên port nguyên vẹn logic thay vì viết lại.
- **Blender 5.0 Breaking Changes**: Icon names có thể thay đổi giữa các version, cần dùng icon phổ biến hoặc try-except.
- **World Space vs Local Space**: Blender `ray_cast()` và `closest_point_on_mesh()` trả về local coordinates, phải transform về world space trước khi so sánh.

### 4. Kết quả
- [x] Port Hybrid CPOM snap logic
- [x] Fix crash Blender 5.0 (icon deprecated)
- [x] Thêm Wire Thickness slider (0.001 - 0.05)
- [ ] Test Single Rail trên surface phức tạp
