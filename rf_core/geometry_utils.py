"""
Geometry Utilities for Rail Flow Blender
Contains: Vector math, RMF (Rotation Minimizing Frame) algorithm

Ported from Maya version with minimal changes.
Uses mathutils instead of maya.api.OpenMaya
"""

import math
from mathutils import Vector, Matrix


def normalize(v):
    """Normalize a vector, return zero vector if length is 0"""
    length = v.length
    if length < 1e-10:
        return Vector((0, 0, 0))
    return v / length


def cross(a, b):
    """Cross product of two vectors"""
    return a.cross(b)


def dot(a, b):
    """Dot product of two vectors"""
    return a.dot(b)


def lerp(a, b, t):
    """Linear interpolation between two vectors"""
    return a + (b - a) * t


def compute_rmf_frames(points, initial_up=None):
    """
    Compute Rotation Minimizing Frames along a curve.

    RMF provides stable orientation frames that minimize twist,
    essential for tube/ribbon generation.

    Args:
        points: List of Vector positions along curve
        initial_up: Initial up vector (default: Z-up or auto-detect)

    Returns:
        List of frames, each frame = (tangent, normal, binormal)
    """
    if len(points) < 2:
        return []

    frames = []

    # Initial frame
    tangent = normalize(Vector(points[1]) - Vector(points[0]))

    if initial_up is None:
        # Auto-detect: use world Z if not parallel to tangent
        world_up = Vector((0, 0, 1))
        if abs(dot(tangent, world_up)) > 0.99:
            world_up = Vector((0, 1, 0))
        initial_up = world_up

    # Compute initial normal and binormal
    binormal = normalize(cross(tangent, initial_up))
    normal = normalize(cross(binormal, tangent))

    frames.append((tangent.copy(), normal.copy(), binormal.copy()))

    # Propagate frames using double reflection method (RMF)
    for i in range(1, len(points) - 1):
        # Current and next tangent
        t0 = tangent
        t1 = normalize(Vector(points[i + 1]) - Vector(points[i]))

        # Reflection vector
        v1 = Vector(points[i]) - Vector(points[i - 1])
        c1 = dot(v1, v1)

        if c1 < 1e-10:
            # Points too close, reuse previous frame
            frames.append((t1.copy(), normal.copy(), binormal.copy()))
            tangent = t1
            continue

        # First reflection (over v1)
        r_normal = normal - (2 / c1) * dot(v1, normal) * v1
        r_tangent = t0 - (2 / c1) * dot(v1, t0) * v1

        # Second reflection (over t1 - r_tangent)
        v2 = t1 - r_tangent
        c2 = dot(v2, v2)

        if c2 < 1e-10:
            normal = r_normal
        else:
            normal = r_normal - (2 / c2) * dot(v2, r_normal) * v2

        normal = normalize(normal)
        binormal = normalize(cross(t1, normal))
        tangent = t1

        frames.append((tangent.copy(), normal.copy(), binormal.copy()))

    # Last frame (copy from previous)
    if len(points) > 1:
        frames.append(frames[-1])

    return frames


def resample_curve(points, num_samples):
    """
    Resample a curve to have evenly spaced points.

    Args:
        points: Original curve points
        num_samples: Desired number of output points

    Returns:
        List of resampled Vector positions
    """
    if len(points) < 2 or num_samples < 2:
        return points

    # Calculate total curve length
    lengths = [0.0]
    for i in range(1, len(points)):
        segment_len = (Vector(points[i]) - Vector(points[i-1])).length
        lengths.append(lengths[-1] + segment_len)

    total_length = lengths[-1]
    if total_length < 1e-10:
        return [points[0]] * num_samples

    # Resample at even intervals
    resampled = []
    for i in range(num_samples):
        target_length = (i / (num_samples - 1)) * total_length

        # Find segment containing target length
        for j in range(1, len(lengths)):
            if lengths[j] >= target_length:
                # Interpolate within segment
                segment_start = lengths[j-1]
                segment_end = lengths[j]
                segment_len = segment_end - segment_start

                if segment_len < 1e-10:
                    t = 0.0
                else:
                    t = (target_length - segment_start) / segment_len

                point = lerp(Vector(points[j-1]), Vector(points[j]), t)
                resampled.append(point)
                break

    return resampled


def closest_point_on_line(point, line_start, line_end):
    """Find closest point on a line segment to a given point"""
    line_vec = Vector(line_end) - Vector(line_start)
    point_vec = Vector(point) - Vector(line_start)

    line_len_sq = line_vec.length_squared
    if line_len_sq < 1e-10:
        return Vector(line_start)

    t = max(0, min(1, dot(point_vec, line_vec) / line_len_sq))
    return Vector(line_start) + t * line_vec
