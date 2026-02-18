# 📔 Blender Tool Developer Handbook: UI & Viewport Messaging

Tài liệu này ghi lại các kinh nghiệm quan trọng trong việc xử lý giao diện và hiển thị trong Blender (đặc biệt là bản 4.2+) để đảm bảo UX mượt mà.

> [!NOTE]
> ## 📋 AI Session Checkpoint
> 
> Đây là 1 trong **4 cẩm nang kỹ thuật** mà AI phải đọc khi user nhắc.
> 
> **Quick Reminder:**
> - 🇻🇳 Trả lời bằng **Tiếng Việt**
> - 📝 Fix bug xong → Cập nhật `docs/notes/DAILY_DEVELOPMENT_LOG.md`
> - 🔗 Xem thêm: [COLLABORATION_PROTOCOL](./COLLABORATION_PROTOCOL.md) | [SMART_DEV_HANDBOOK](./SMART_DEV_HANDBOOK.md)

---

## 1. 🧹 Thông báo người dùng (Status & Reports)
Khác với `inViewMessage` của Maya, Blender sử dụng hệ thống `report` và `status text`.

### Quy trình chuẩn:
1.  **Lỗi/Cảnh báo (Popup)**: Dùng `self.report({'ERROR'}, "Message")` hoặc `{'WARNING'}` trong Operator.
2.  **Thông tin (Info Bar)**: Dùng `self.report({'INFO'}, "Message")`.
3.  **Trạng thái Modal (Header)**:
    ```python
    context.workspace.status_text_set("ESC: Cancel | LEFT: Add Point")
    # Reset khi thoát
    context.workspace.status_text_set(None)
    ```

---

## 2. 🎨 UI Layout & Naming
Blender UI (bpy.types.Panel) tự động sắp xếp layout, không cần pixel-perfect như Qt.

### Nguyên tắc Layout:
1.  **Alignment**: Dùng `layout.column(align=True)` cho các nhóm nút liên quan (như Set/Clear).
2.  **Labels**: Dùng `layout.label(text="...")` thay vì tạo nút in-active.
3.  **Icons**: Luôn dùng icon chuẩn của Blender (xem Icon Viewer addon) để tạo cảm giác native.

---

## 👁️ 3. Xử lý Hiển thị Wireframe & Transparency (Eevee & Eevee Next)
Xử lý hiển thị "X-Ray" trong Blender phức tạp hơn do sự thay đổi của Eevee qua các phiên bản.

### A. Chiến thuật "Thick Wireframe" (Giả lập Maya)
Blender `show_wire` mặc định quá mỏng (1px). Để đạt chuẩn Rail Flow:
-   **Không dùng**: `obj.show_wire = True` đơn thuần.
-   **Nên dùng**: *Wireframe Modifier*.
    -   `thickness = 0.003` (tương đương 3px).
    -   `material_offset = 1` (để tô màu Cyan phát sáng).
    -   `use_replace = False` (để giữ lại bề mặt trong suốt).

### B. Transparency trong Blender 4.2+ (Eevee Next)
Blender 4.2 loại bỏ `shadow_method` và thay đổi cách xử lý Alpha.

#### Code an toàn (Cross-Version):
```python
mat.blend_method = 'BLEND' # Alpha Blend
mat.use_backface_culling = False

# Xử lý Shadow (Chỉ có trên Blender < 4.2)
try:
    mat.shadow_method = 'NONE'
except AttributeError:
    # Blender 4.2+ Eevee Next tự động xử lý shadow dựa trên setting Raytracing
    pass
```

### C. Z-Fighting & Sorting
Khi vẽ 2 mặt phẳng trùng nhau (Retopo đè lên Source):
-   Blender có `show_in_front` (X-Ray) giải quyết tốt việc này ở cấp độ Object.
-   **Lưu ý**: `show_in_front` sẽ khiến object đè lên TẤT CẢ mọi thứ, kể cả gizmo khác nếu không cẩn thận. Chỉ bật cho Retopo Mesh đang active.

---

## 4. 🛡️ Dọn dẹp GPU Shaders
Nếu sử dụng `gpu` module để vẽ custom HUD:
1.  **Draw Handler**: Luôn lưu `handler` trả về từ `bpy.types.SpaceView3D.draw_handler_add`.
2.  **Remove**: Đảm bảo gọi `bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')` khi tắt tool hoặc reload script.
3.  **Crash Risk**: Quên remove handler sẽ gây crash Blender ngay lập tức khi reload addon.

---
*Giao diện đẹp phải đi kèm với mã nguồn sạch.*
