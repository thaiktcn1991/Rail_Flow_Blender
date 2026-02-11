"""
Patch Generator for Rail Flow Blender
Creates quad meshes from rail strokes using RMF algorithm.

Core mesh generation logic ported from Maya version.
"""

import bpy
import bmesh
from mathutils import Vector

from . import geometry_utils as geo
from . import acceleration


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
                result = acceleration.closest_point_on_mesh(source_obj, vert_pos)
                if result is not None:
                    location, normal, index, distance = result
                    if distance < width * 2:  # Only snap if close enough
                        vert_pos = location

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

    return obj


def generate_multi_rail_patch(strokes, v_divisions=8,
                               source_obj=None, snap_to_surface=True):
    """
    Generate a quad mesh patch between multiple strokes (multi-rail).

    Args:
        strokes: List of strokes (each stroke is list of points)
        v_divisions: Number of divisions along length
        source_obj: Source mesh for surface snapping
        snap_to_surface: Whether to snap vertices to source surface

    Returns:
        Created Blender mesh object
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

    u_divisions = len(resampled_strokes) - 1  # Number of strokes - 1

    # Generate vertex grid by interpolating between strokes
    vertices = []

    for i in range(v_divisions + 1):  # Along length
        for j, stroke in enumerate(resampled_strokes):  # Across strokes
            vert_pos = Vector(stroke[i])

            # Snap to surface if enabled
            if snap_to_surface and source_obj is not None:
                result = acceleration.closest_point_on_mesh(source_obj, vert_pos)
                if result is not None:
                    location, normal, index, distance = result
                    if distance < 1.0:  # Only snap if close enough
                        vert_pos = source_obj.matrix_world @ location

            vertices.append(vert_pos)

    # Generate faces (quads)
    faces = []
    num_strokes = len(resampled_strokes)

    for i in range(v_divisions):
        for j in range(num_strokes - 1):
            # Quad vertices (CCW winding)
            v0 = i * num_strokes + j
            v1 = v0 + 1
            v2 = v1 + num_strokes
            v3 = v0 + num_strokes
            faces.append((v0, v1, v2, v3))

    # Create Blender mesh
    mesh = bpy.data.meshes.new("MultiRailPatch")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    # Create object
    obj = bpy.data.objects.new("MultiRailPatch", mesh)
    bpy.context.collection.objects.link(obj)

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

    return obj
