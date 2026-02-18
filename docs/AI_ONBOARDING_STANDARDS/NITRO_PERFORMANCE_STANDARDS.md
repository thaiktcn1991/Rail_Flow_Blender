# NITRO Performance Standards (Blender Edition)

Tài liệu này quy chuẩn các nguyên tắc tối ưu hóa hiệu năng cực hạn (Nitro) cho Rail Flow Blender, đặc biệt là các thao tác tương tác thời gian thực (Modal Operators).

## 1. Nguyên tắc "Zero bpy.ops" trong vòng lặp (Modal)
Khi người dùng đang di chuột (MOUSEMOVE modal), **TUYỆT ĐỐI KHÔNG** sử dụng `bpy.ops` (Operators).
- `bpy.ops` kích hoạt toàn bộ Dependency Graph update → Lag tung máy (< 10 FPS).
- **Thay thế**: Dùng `bpy.data` hoặc `bmesh` để thao tác dữ liệu trực tiếp.

## 2. Bulk Vertex Update (`foreach_set`)
Để đạt tốc độ "Liquid" trong Blender Python, hạn chế vòng lặp `for` của Python.
Sử dụng `foreach_get` và `foreach_set` của Blender API (hoặc `numpy` nếu có thể).

```python
# CHẬM (Python Loop):
for v in mesh.vertices:
    v.co.z += 1.0

# NHANH (Internal C Loop):
# Chuẩn bị array phẳng (flat list/array)
coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
mesh.vertices.foreach_get("co", coords)
coords[2::3] += 1.0 # Tăng Z
mesh.vertices.foreach_set("co", coords)
mesh.update()
```

## 3. Quản lý BMesh (Edit Mode vs Object Mode)
- **Object Mode**: Dùng `mesh.vertices` nhanh hơn cho các biến đổi đơn giản.
- **Edit Mode**: Bắt buộc dùng `bmesh.from_edit_mesh(me)`.
    - **Lưu ý**: `bmesh` tốn bộ nhớ hơn. Luôn `bm.free()` nếu tạo bmesh mới (không phải từ edit mesh).
    - Hạn chế `bm.faces.ensure_lookup_table()` liên tục trong loop. Gọi 1 lần trước loop.

## 4. Spatial Cache (KDTree / BVHTree)
Không dùng `obj.closest_point_on_mesh` (chậm nếu gọi nghìn lần).
-   Dùng `mathutils.kdtree.KDTree` (cho tìm điểm gần nhất).
-   Dùng `mathutils.bvhtree.BVHTree` (cho Raycast).
-   **Blender 4.2+**: BVHTree vẫn là giải pháp tốt nhất cho Raycast hiệu năng cao.

## 5. Tạm đình chỉ (Suspend) Updates
Trong quá trình modal:
-   Tránh gọi `bpy.context.view_layer.update()` trừ khi bắt buộc.
-   Nếu thay đổi topo (thêm/bớt mặt), `mesh.update()` là bắt buộc, nhưng hãy gom nhóm thay đổi (Batch Update) rồi mới gọi update 1 lần cuối frame.

---
*Lưu ý: Python trong Blender chậm hơn C++. Tối ưu hóa memory layout và giảm call overhead là chìa khóa.*
