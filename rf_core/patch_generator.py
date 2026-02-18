"""
Patch Generator for Rail Flow Blender
Handles mesh creation, snapping, and style application.
"""

################################################################################
# 🛡️ AI PRE-DEBUG CHECKPOINT: BLENDER UI & LOGIC INTEGRITY
# ------------------------------------------------------------------------------
# TRƯỚC KHI SỬA BẤT KỲ LỖI NÀO, BẠN BẮT BUỘC PHẢI ĐỌC CÁC FILE CẨM NANG SAU:
# 1. [SMART_DEV_HANDBOOK.md](file:///d:/Google_AntiGravity/scratch/Rail_Flow_Blender/docs/AI_ONBOARDING_STANDARDS/SMART_DEV_HANDBOOK.md)
# 2. [COLLABORATION_PROTOCOL.md](file:///d:/Google_AntiGravity/scratch/Rail_Flow_Blender/docs/AI_ONBOARDING_STANDARDS/COLLABORATION_PROTOCOL.md)
# 3. [DAILY_DEVELOPMENT_LOG.md](file:///d:/Google_AntiGravity/scratch/Rail_Flow_Blender/docs/notes/DAILY_DEVELOPMENT_LOG.md)
# ------------------------------------------------------------------------------
# 🇻🇳 NGÔN NGỮ: TIẾNG VIỆT LÀ BẮT BUỘC.
# 🏗️ KIẾN TRÚC: TUÂN THỦ MODULAR (CORE tách biệt hoàn toàn UI).
# ################################################################################

import bpy
import bmesh
from mathutils import Vector

from . import geometry_utils as geo
from . import acceleration


def enforce_outward_normals(obj, source_obj):
    """
    Ensure mesh normals are facing away from the source mesh.
    """
    if not (obj and source_obj and obj.data.polygons):
        return

    # 1. Get average normal of the new mesh
    avg_norm = Vector((0, 0, 0))
    for f in obj.data.polygons:
        avg_norm += f.normal
    avg_norm.normalize()

    # 2. Get surface normal at the center of the mesh
    # Use bboxes center as a proxy for 'mesh center'
    bbox_center = sum((Vector(b) for b in obj.bound_box), Vector()) / 8.0
    cp = acceleration.closest_point_on_mesh(source_obj, obj.matrix_world @ bbox_center)
    
    if cp:
        loc, surf_norm, idx, dist = cp
        # If mesh normal and surface normal are opposite (dot < 0), flip!
        # Note: We want them to point in the SAME direction (both away from mesh)
        if avg_norm.dot(surf_norm) < 0:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()
            return True
    return False


def generate_quad_patch(stroke_points, u_divisions=4, v_divisions=8,
                        width=0.5, source_obj=None, snap_to_surface=True):
    """
    Generate a quad mesh patch from stroke points.

    Args:
        stroke_points: List of points defining the rail curve
        u_divisions: Number of divisions across width
        v_divisions: Number of divisions along length
        width: Width of the patch
        source_obj: Source mesh for surface snapping
        snap_to_surface: Whether to snap vertices to source surface

    Returns:
        Created Blender mesh object
    """
    if len(stroke_points) < 2:
        return None

    # Resample stroke to match v_divisions
    resampled = geo.resample_curve(stroke_points, v_divisions + 1)

    # Compute RMF frames along curve
    frames = geo.compute_rmf_frames(resampled)

    if len(frames) != len(resampled):
        print("Rail Flow: Frame count mismatch")
        return None

    # Generate vertex grid
    vertices = []
    half_width = width / 2.0

    for i, (point, frame) in enumerate(zip(resampled, frames)):
        tangent, normal, binormal = frame

        for j in range(u_divisions + 1):
            # Position across width
            t = j / u_divisions
            offset = (t - 0.5) * width
            vert_pos = Vector(point) + offset * binormal

            # Snap to surface if enabled
            if snap_to_surface and source_obj is not None:
                # Use RMF normal for projection direction to ensure smooth grid flow
                # This prevents vertices from "sliding" towards geometric edges
                result = acceleration.smart_raycast_snap(source_obj, vert_pos, normal)
                if result is not None:
                    location, hit_norm, index, distance = result
                    if distance < width * 2:  # Only snap if close enough
                        # Apply surface offset to prevent Z-fighting
                        vert_pos = location + hit_norm * 0.001

            vertices.append(vert_pos)

    # Generate faces (quads)
    faces = []
    for i in range(v_divisions):
        for j in range(u_divisions):
            # Quad vertices (CCW winding)
            v0 = i * (u_divisions + 1) + j
            v1 = v0 + 1
            v2 = v1 + (u_divisions + 1)
            v3 = v0 + (u_divisions + 1)
            faces.append((v0, v1, v2, v3))

    # Create Blender mesh
    mesh = bpy.data.meshes.new("RailPatch")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    # Create object
    obj = bpy.data.objects.new("RailPatch", mesh)
    bpy.context.collection.objects.link(obj)
    
    # NITRO SMART NORMAL FIX: Ensure it faces AWAY from source
    if snap_to_surface and source_obj:
        enforce_outward_normals(obj, source_obj)
    
    # Apply Rail Flow Style
    if hasattr(bpy.context.scene, "railflow_settings"):
        apply_style(obj, bpy.context.scene.railflow_settings.use_xray)
    else:
        apply_style(obj, True)

    # Store metadata
    store_metadata(obj, {
        "type": "SINGLE_RAIL",
        "stroke_points": stroke_points,
        "u_divisions": u_divisions,
        "v_divisions": v_divisions,
        "width": width,
        "snap_to_surface": snap_to_surface,
        "source_name": source_obj.name if source_obj else ""
    })

    return obj


def generate_multi_rail_patch(strokes, u_divisions=1, v_divisions=8,
                               source_obj=None, snap_to_surface=True, segmented=False, mesh_type="POLY_MULTI"):
    """
    Generate a quad mesh patch between multiple strokes (multi-rail).
    """
    if len(strokes) < 2:
        return None

    # Resample all strokes to same number of points
    resampled_strokes = []
    for stroke in strokes:
        if len(stroke) >= 2:
            resampled = geo.resample_curve(stroke, v_divisions + 1)
            resampled_strokes.append(resampled)

    if len(resampled_strokes) < 2:
        return None

    final_cols = []
    num_strokes = len(resampled_strokes)

    if segmented:
        # NITRO SEGMENTED (Bridge/Chain): Every stroke is an edge loop
        # We interpolate 'u_divisions' columns BETWEEN each pair of strokes
        for s_idx in range(num_strokes - 1):
            stroke_a = resampled_strokes[s_idx]
            stroke_b = resampled_strokes[s_idx + 1]
            
            # Start of segment (Stroke A)
            if s_idx == 0:
                final_cols.append(stroke_a)
            
            # Intermediate columns
            for i in range(1, u_divisions + 1):
                t = i / u_divisions
                col = []
                for j in range(v_divisions + 1):
                    p_a = Vector(stroke_a[j])
                    p_b = Vector(stroke_b[j])
                    col.append(p_a.lerp(p_b, t))
                final_cols.append(col)
    else:
        # GLOBAL LOFT (Poly Draw): Smooth interpolation across the entire width
        num_cols = max(2, u_divisions + 1)
        for i in range(num_cols):
            t_global = i / (num_cols - 1)
            t_scaled = t_global * (num_strokes - 1)
            idx_a = int(t_scaled)
            idx_b = min(idx_a + 1, num_strokes - 1)
            u = t_scaled - idx_a
            
            stroke_a = resampled_strokes[idx_a]
            stroke_b = resampled_strokes[idx_b]
            
            col_points = []
            for j in range(v_divisions + 1):
                p_a = Vector(stroke_a[j])
                p_b = Vector(stroke_b[j])
                col_points.append(p_a.lerp(p_b, u))
            final_cols.append(col_points)

    # Generate vertex grid
    vertices = []
    num_rows = v_divisions + 1
    num_cols = len(final_cols)

    for i in range(num_rows):  # Along length
        for j in range(num_cols):  # Across width
            vert_pos = final_cols[j][i]

            # Snap to surface if enabled
            if snap_to_surface and source_obj is not None:
                # For Multi-Rail, we derive a "Projection Normal" by cross-product
                # of the rail segment and the width segment (interpolation direction)
                proj_dir = Vector((0, 0, 1)) # Fallback
                try:
                    # p_a and p_b are still in scope if we organize the loop well, 
                    # but since they aren't, let's just use Z-up or Closest Point Normal as fallback
                    # In a high-quality port, we'd calculate the surface normal here.
                    
                    # For now, let's use the closest surface normal as the projection direction
                    # to refine the position without sideways sliding.
                    cp = acceleration.closest_point_on_mesh(source_obj, vert_pos)
                    if cp:
                        # Use the surface normal at the closest point for the projection ray
                        location, hit_norm, idx, dist = cp
                        result = acceleration.smart_raycast_snap(source_obj, vert_pos, hit_norm)
                        if result:
                            vert_pos = result[0] + result[1] * 0.001
                except:
                    pass

            vertices.append(vert_pos)

    # Generate faces (quads)
    faces = []

    for i in range(v_divisions):
        for j in range(num_cols - 1):
            # Quad vertices (j is col index, i is row index)
            # Layout: Row major? No, loops above: Outer i (Row), Inner j (Col).
            # So index = i * num_cols + j
            
            v0 = i * num_cols + j
            v1 = v0 + 1
            v2 = v1 + num_cols
            v3 = v0 + num_cols
            faces.append((v0, v1, v2, v3))

    # Create Blender mesh
    mesh = bpy.data.meshes.new("MultiRailPatch")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    # Create object
    obj = bpy.data.objects.new("MultiRailPatch", mesh)
    bpy.context.collection.objects.link(obj)
    
    # NITRO SMART NORMAL FIX
    if snap_to_surface and source_obj:
        enforce_outward_normals(obj, source_obj)
    
    # Apply Rail Flow Style
    rf_settings = getattr(bpy.context.scene, "railflow_settings", None)
    use_xray = rf_settings.use_xray if rf_settings else True
    apply_style(obj, use_xray)

    # Store metadata
    store_metadata(obj, {
        "type": mesh_type,
        "strokes": strokes,
        "u_divisions": u_divisions, # Store U Divisions
        "v_divisions": v_divisions,
        "snap_to_surface": snap_to_surface,
        "source_name": source_obj.name if source_obj else ""
    })

    return obj


def generate_tube(stroke_points, segments=8, v_divisions=8,
                  radius=0.1, source_obj=None, adaptive_radius=False):
    """
    Generate a tube mesh along stroke points.

    Args:
        stroke_points: List of points defining the tube center
        segments: Number of segments around circumference
        v_divisions: Number of divisions along length
        radius: Tube radius (or initial radius if adaptive)
        source_obj: Source mesh for adaptive radius calculation
        adaptive_radius: Calculate radius based on surface thickness

    Returns:
        Created Blender mesh object
    """
    if len(stroke_points) < 2:
        return None

    # Resample stroke
    resampled = geo.resample_curve(stroke_points, v_divisions + 1)

    # Compute RMF frames
    frames = geo.compute_rmf_frames(resampled)

    # Generate vertices
    vertices = []
    import math

    for i, (point, frame) in enumerate(zip(resampled, frames)):
        tangent, normal, binormal = frame
        point = Vector(point)

        # Adaptive radius: raycast to find surface thickness
        current_radius = radius
        if adaptive_radius and source_obj is not None:
            # Cast ray inward to find opposite surface
            result = acceleration.raycast_mesh(source_obj, point, -normal, radius * 10)
            if result is not None:
                location, _, _, distance = result
                current_radius = distance / 2.0
                current_radius = max(radius * 0.5, min(radius * 2.0, current_radius))

        # Generate circle vertices
        for j in range(segments):
            angle = (j / segments) * math.pi * 2
            x = math.cos(angle) * current_radius
            y = math.sin(angle) * current_radius
            vert_pos = point + x * normal + y * binormal
            vertices.append(vert_pos)

    # Generate faces
    faces = []
    for i in range(v_divisions):
        for j in range(segments):
            # Quad vertices
            v0 = i * segments + j
            v1 = i * segments + (j + 1) % segments
            v2 = (i + 1) * segments + (j + 1) % segments
            v3 = (i + 1) * segments + j
            faces.append((v0, v1, v2, v3))

    # Create mesh
    mesh = bpy.data.meshes.new("RailTube")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    # Create object
    obj = bpy.data.objects.new("RailTube", mesh)
    bpy.context.collection.objects.link(obj)
    
    # Apply Rail Flow Style
    if hasattr(bpy.context.scene, "railflow_settings"):
        apply_style(obj, bpy.context.scene.railflow_settings.use_xray)
    else:
        apply_style(obj, True)

    # Store metadata for rebuilding
    store_metadata(obj, {
        "type": "TUBE",
        "stroke_points": stroke_points,
        "segments": segments,
        "v_divisions": v_divisions,
        "radius": radius,
        "adaptive_radius": adaptive_radius,
        "source_name": source_obj.name if source_obj else ""
    })

    return obj


def store_metadata(obj, data):
    """Store generation parameters as custom properties"""
    for key, value in data.items():
        # Blender custom properties handle basic types (int, float, string)
        # Lists of vectors need conversion to flat lists or generic lists
        if key in ["stroke_points", "strokes"]:
            # Convert Vector lists to plain lists for storage
            if key == "stroke_points":
                obj[key] = [list(v) for v in value]
            elif key == "strokes":
                obj[key] = [[list(v) for v in s] for s in value]
        else:
            obj[key] = value


def get_or_create_materials():
    """Get or create Surface and Wire materials"""
    # 1. Surface Material (Darker, transparent)
    mat_surf_name = "RailFlow_Surface"
    mat_surf = bpy.data.materials.get(mat_surf_name)
    if mat_surf is None:
        mat_surf = bpy.data.materials.new(name=mat_surf_name)
        mat_surf.use_nodes = True
        mat_surf.blend_method = 'BLEND'
        mat_surf.use_backface_culling = True # Reduce clutter
        try:
            mat_surf.shadow_method = 'NONE' # No shadows (Blender < 4.2)
        except AttributeError:
            pass 
            
        mat_surf.diffuse_color = (0.0, 0.85, 0.85, 0.3)  # Bright Cyan Surface (Good for Solid Mode)
        
        # Setup nodes for transparent surface
        if mat_surf.node_tree:
            nodes = mat_surf.node_tree.nodes
            links = mat_surf.node_tree.links
            nodes.clear()
            
            output = nodes.new(type='ShaderNodeOutputMaterial')
            bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
            
            # Bright Cyan Surface
            bsdf.inputs['Base Color'].default_value = (0.0, 0.85, 0.85, 1.0)
            bsdf.inputs['Alpha'].default_value = 0.30 
            bsdf.inputs['Roughness'].default_value = 1.0
            
            # Slight Emission to prevent "sinking" in shadows
            if 'Emission Color' in bsdf.inputs: # Blender 4.0+
                 bsdf.inputs['Emission Color'].default_value = (0.0, 0.2, 0.2, 1.0)
                 bsdf.inputs['Emission Strength'].default_value = 0.1
            elif 'Emission' in bsdf.inputs: # Older Blender
                 bsdf.inputs['Emission'].default_value = (0.0, 0.2, 0.2, 1.0)
            
            links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
            
    # Update existing material settings just in case
    else:
        mat_surf.blend_method = 'BLEND'
        mat_surf.use_backface_culling = True
        try:
            mat_surf.shadow_method = 'NONE'
        except AttributeError:
            pass
        mat_surf.diffuse_color = (0.0, 0.85, 0.85, 0.3)
        
        if mat_surf.node_tree:
            nodes = mat_surf.node_tree.nodes
            bsdf = next((n for n in nodes if n.type == 'ShaderNodeBsdfPrincipled'), None)
            if bsdf:
                bsdf.inputs['Base Color'].default_value = (0.0, 0.85, 0.85, 1.0)
                bsdf.inputs['Alpha'].default_value = 0.30
                if 'Emission Color' in bsdf.inputs:
                     bsdf.inputs['Emission Color'].default_value = (0.0, 0.2, 0.2, 1.0)
                     bsdf.inputs['Emission Strength'].default_value = 0.1

    # 2. Wire Material (Black Technical Lines)
    mat_wire_name = "RailFlow_Wire"
    mat_wire = bpy.data.materials.get(mat_wire_name)
    if mat_wire is None:
        mat_wire = bpy.data.materials.new(name=mat_wire_name)
        mat_wire.use_nodes = True
        mat_wire.diffuse_color = (0.0, 0.0, 0.0, 1.0)  # Black Viewport Color
        mat_wire.use_backface_culling = False # Always show wire
        try:
            mat_wire.shadow_method = 'NONE'
        except AttributeError:
             pass

        if mat_wire.node_tree:
             nodes = mat_wire.node_tree.nodes
             links = mat_wire.node_tree.links
             nodes.clear()
             
             output = nodes.new(type='ShaderNodeOutputMaterial')
             # Use Emission with Black color to create "Unlit Black"
             # (It will look like flat black regardless of lighting)
             emission = nodes.new(type='ShaderNodeEmission')
             emission.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0) # Pure Black
             emission.inputs['Strength'].default_value = 1.0 
             links.new(emission.outputs['Emission'], output.inputs['Surface'])
            
    else:
        # Enforce settings on existing material
        mat_wire.diffuse_color = (0.0, 0.0, 0.0, 1.0)
        mat_wire.use_backface_culling = False
        if mat_wire.node_tree:
             nodes = mat_wire.node_tree.nodes
             emission = next((n for n in nodes if n.type == 'ShaderNodeEmission'), None)
             if emission:
                 emission.inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)
                 emission.inputs['Strength'].default_value = 1.0
            
    return mat_surf, mat_wire


def apply_style(obj, use_xray=True):
    """
    Apply Rail Flow visual style using Wireframe Modifier for thickness.
    Stores original material to restore when disabled.
    """
    mod_name = "RailFlow_ThickWire"
    
    if use_xray:
        # 1. Store Original Material (if not already stored)
        # Verify we aren't storing our own material as "original"
        current_mat = obj.data.materials[0].name if obj.data.materials else ""
        if "rf_orig_mat" not in obj:
            if current_mat != "RailFlow_Surface" and current_mat != "RailFlow_Wire":
                obj["rf_orig_mat"] = current_mat
        
        # 2. visual settings
        obj.show_in_front = True
        obj.display_type = 'TEXTURED'
        
        # We don't need native wireframe if we use modifier
        obj.show_wire = False 
        obj.show_all_edges = False
        
        # Assign Materials
        mat_surf, mat_wire = get_or_create_materials()
        
        # Ensure 2 slots exist
        while len(obj.data.materials) < 2:
            obj.data.materials.append(None)
            
        obj.data.materials[0] = mat_surf
        obj.data.materials[1] = mat_wire
        
        # Add/Update Wireframe Modifier
        mod = obj.modifiers.get(mod_name)
        if mod is None:
            mod = obj.modifiers.new(name=mod_name, type='WIREFRAME')
            
        mod.use_replace = False  # Keep original surface
        mod.material_offset = 1  # Use 2nd material (Wire)
        # mod.thickness = 0.008    # x2 Thickness (8mm)
        mod.thickness = 0.008
        mod.use_even_offset = True 
        mod.use_boundary = True
        mod.use_relative_offset = False # Absolute thickness
            
    else:
        # Revert to standard
        obj.show_in_front = False
        obj.show_wire = False
        
        # Remove modifier
        mod = obj.modifiers.get(mod_name)
        if mod:
            obj.modifiers.remove(mod)
            
        # Restore Original Material
        # If we have a stored original material, restore it
        if "rf_orig_mat" in obj:
            orig_name = obj["rf_orig_mat"]
            
            # Reset materials
            obj.data.materials.clear()
            
            # Convert property to string just in case
            if hasattr(orig_name, "to_string"): 
                 orig_name = orig_name.to_string()
            
            if orig_name and orig_name in bpy.data.materials:
                obj.data.materials.append(bpy.data.materials[orig_name])
            
            # Clean up the property so next toggle works correctly
            del obj["rf_orig_mat"]
            
        # Fallback for old objects or if logic fails: Check if we are still using RF materials
        elif len(obj.data.materials) > 0 and obj.data.materials[0] and obj.data.materials[0].name == "RailFlow_Surface":
             obj.data.materials.clear() # Revert to default grey



def rebuild_mesh(obj):
    """Rebuild mesh using stored metadata"""
    if not obj or "type" not in obj:
        return False

    try:
        mesh_type = obj["type"]
        new_data = None

        # V1.1: Capture average normal of old mesh for orientation persistence
        old_avg_norm = Vector((0, 0, 0))
        if obj.data.polygons:
            for f in obj.data.polygons:
                old_avg_norm += f.normal
            old_avg_norm.normalize()

        # Retrieve source object if needed
        source_obj = None
        if "source_name" in obj and obj["source_name"]:
            source_obj = bpy.data.objects.get(obj["source_name"])

        if mesh_type == "SINGLE_RAIL":
            # Re-generate mesh data
            # Note: We need a temporary object or direct mesh data generation
            # Let's use a temporary object to reuse existing functions, then swap data
            temp_obj = generate_quad_patch(
                stroke_points=[Vector(v) for v in obj["stroke_points"]],
                u_divisions=obj["u_divisions"],
                v_divisions=obj["v_divisions"],
                width=obj["width"],
                source_obj=source_obj,
                snap_to_surface=obj.get("snap_to_surface", True)
            )
            if temp_obj:
                new_data = temp_obj.data
                bpy.data.objects.remove(temp_obj, do_unlink=True)

        elif mesh_type in ["MULTI_RAIL", "POLY_MULTI", "BRIDGE_CHAIN"]:
            strokes = [[Vector(v) for v in s] for s in obj["strokes"]]
            
            # Default to 1 if not present (legacy support)
            u_div = obj.get("u_divisions", 1) 
            is_segmented = (mesh_type == "BRIDGE_CHAIN")
            
            temp_obj = generate_multi_rail_patch(
                strokes=strokes,
                u_divisions=u_div,
                v_divisions=obj["v_divisions"],
                source_obj=source_obj,
                snap_to_surface=obj.get("snap_to_surface", True),
                segmented=is_segmented,
                mesh_type=mesh_type
            )
            if temp_obj:
                new_data = temp_obj.data
                bpy.data.objects.remove(temp_obj, do_unlink=True)

        elif mesh_type == "TUBE":
            temp_obj = generate_tube(
                stroke_points=[Vector(v) for v in obj["stroke_points"]],
                segments=obj["segments"],
                v_divisions=obj["v_divisions"],
                radius=obj["radius"],
                source_obj=source_obj,
                adaptive_radius=obj.get("adaptive_radius", False)
            )
            if temp_obj:
                new_data = temp_obj.data
                bpy.data.objects.remove(temp_obj, do_unlink=True)

        # Swap mesh data
        if new_data:
            # Check orientation persistence
            new_avg_norm = Vector((0, 0, 0))
            if new_data.polygons:
                for f in new_data.polygons:
                    new_avg_norm += f.normal
                new_avg_norm.normalize()
            
            # If normals are facing opposite directions (dot product < 0), flip!
            if old_avg_norm.dot(new_avg_norm) < -0.1:
                for f in new_data.polygons:
                    f.flip()
                new_data.update()
                print("Rail Flow: Normal flipped to match orientation persistence")

            old_data = obj.data
            obj.data = new_data
            if old_data.users == 0:
                bpy.data.meshes.remove(old_data)
            
            # Refresh visual style (Ensure thickness/materials are correct)
            rf_settings = getattr(bpy.context.scene, "railflow_settings", None)
            use_xray = rf_settings.use_xray if rf_settings else True
            apply_style(obj, use_xray)
            
            return True

    except Exception as e:
        print(f"Rail Flow Rebuild Error: {e}")
        import traceback
        traceback.print_exc()

    return False


def generate_bridge_patch(source_obj_name, vertex_indices, stroke_points, u_divisions=4, v_divisions=8,
                           connection_mode='AUTO', poly_along_stroke=False, source_surface_obj=None, snap_to_surface=True):
    """
    Generate a bridge mesh between selected vertices and a drawn rail.
    """
    source_obj = bpy.data.objects.get(source_obj_name)
    if not source_obj or not vertex_indices or len(stroke_points) < 2:
        return None

    # 1. Get world positions of selected vertices
    source_verts = []
    matrix_world = source_obj.matrix_world
    for idx in vertex_indices:
        if idx < len(source_obj.data.vertices):
            pos = matrix_world @ source_obj.data.vertices[idx].co
            source_verts.append(pos)
    
    if len(source_verts) < 2:
        return None

    # 2. Resample stroke points - ALWAYS match selected vertex count for topological parity
    num_v_target = len(source_verts)
    resampled_stroke = geo.resample_curve(stroke_points, num_v_target)
    
    # 3. Handle Mapping
    final_rows = []
    
    # In Bridge mode, we always want a 1:1 mapping from selected vertices to the rail points
    for i in range(num_v_target):
        p_start = source_verts[i]
        p_end = Vector(resampled_stroke[i])
        
        row = []
        for j in range(u_divisions + 1):
            t = j / u_divisions
            row.append(p_start.lerp(p_end, t))
        final_rows.append(row)
    
    actual_v_div = num_v_target - 1

    # 4. Create Mesh
    vertices = []
    for row in final_rows:
        for v in row:
            if snap_to_surface and source_surface_obj:
                # Use acceleration to snap to surface
                result = acceleration.smart_raycast_snap(source_surface_obj, v, Vector((0, 0, 1)))
                if result:
                    v = result[0] + result[1] * 0.001
            vertices.append(v)
            
    faces = []
    u_count = u_divisions + 1
    for i in range(actual_v_div):
        for j in range(u_divisions):
            v0 = i * u_count + j
            v1 = v0 + 1
            v2 = v1 + u_count
            v3 = v0 + u_count
            faces.append((v0, v1, v2, v3))

    mesh = bpy.data.meshes.new("BridgePatch")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    
    obj = bpy.data.objects.new("BridgePatch", mesh)
    bpy.context.collection.objects.link(obj)
    
    # NITRO SMART NORMAL FIX
    if snap_to_surface and source_surface_obj:
        enforce_outward_normals(obj, source_surface_obj)
    
    apply_style(obj, True)
    
    store_metadata(obj, {
        "type": "BRIDGE",
        "source_mesh_name": source_obj_name,
        "vertex_indices": vertex_indices,
        "stroke_points": stroke_points,
        "u_divisions": u_divisions,
        "v_divisions": v_divisions,
        "connection_mode": connection_mode,
        "snap_to_surface": snap_to_surface
    })
    
    return obj
