"""
Spatial Acceleration for Rail Flow Blender
Simple raycast using Blender's built-in Object.ray_cast()

This is more stable than BVHTree for Blender 5.0+
"""

from mathutils import Vector


def raycast_mesh(obj, origin, direction, max_distance=1e10):
    """
    Cast ray against mesh and find intersection.
    Uses Object.ray_cast() which is simpler and more stable.

    Args:
        obj: Blender mesh object
        origin: Ray origin in WORLD space
        direction: Ray direction in WORLD space
        max_distance: Maximum ray distance

    Returns:
        (location, normal, index, distance) or None
    """
    if obj is None or obj.type != 'MESH':
        return None

    try:
        # Convert world space to object local space
        matrix_inv = obj.matrix_world.inverted()
        origin_local = matrix_inv @ Vector(origin)
        direction_local = (matrix_inv.to_3x3() @ Vector(direction)).normalized()

        # Raycast in object local space
        success, location, normal, face_index = obj.ray_cast(
            origin_local,
            direction_local,
            distance=max_distance
        )

        if success:
            # Calculate distance
            distance = (location - origin_local).length
            return (location, normal, face_index, distance)

    except Exception as e:
        print(f"Rail Flow raycast error: {e}")

    return None


def closest_point_on_mesh(obj, point):
    """
    Find closest point on mesh surface.
    Uses Object.closest_point_on_mesh()

    Args:
        obj: Blender mesh object
        point: Query point in WORLD space

    Returns:
        (location, normal, index, distance) or None
    """
    if obj is None or obj.type != 'MESH':
        return None

    try:
        # Convert to local space
        matrix_inv = obj.matrix_world.inverted()
        point_local = matrix_inv @ Vector(point)

        # Find closest point
        success, location, normal, face_index = obj.closest_point_on_mesh(point_local)

        if success:
            distance = (location - point_local).length
            return (location, normal, face_index, distance)

    except Exception as e:
        print(f"Rail Flow closest_point error: {e}")

    return None
