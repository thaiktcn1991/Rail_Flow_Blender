from mathutils import Vector

# Cache for spatial structures (BVH and Raycast acceleration)
_spatial_cache = {}

def clear_cache(obj=None):
    """Clear acceleration cache globally or for a specific object."""
    global _spatial_cache
    if obj:
        if obj.name in _spatial_cache:
            del _spatial_cache[obj.name]
            print(f"Rail Flow: Cleared acceleration cache for {obj.name}")
    else:
        _spatial_cache.clear()
        print("Rail Flow: Cleared all acceleration caches")

def pre_build(obj):
    """
    Pre-build acceleration structures for the object.
    In standard Blender, we don't need a heavy manual build like Maya's SpatialManager,
    but calling closest_point_on_mesh once 'warms up' the internal BVH.
    """
    if obj and obj.type == 'MESH':
        clear_cache(obj)
        # Dummy search to initialize internal BVH
        obj.closest_point_on_mesh((0,0,0))
        print(f"Rail Flow: Pre-built acceleration for {obj.name}")

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
            world_location = obj.matrix_world @ location
            distance = (world_location - Vector(origin)).length
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
            world_location = obj.matrix_world @ location
            distance = (world_location - Vector(point)).length
            return (location, normal, face_index, distance)

    except Exception as e:
        print(f"Rail Flow closest_point error: {e}")

    return None


def smart_raycast_snap(obj, point, direction, bias=1.0, max_distance=1.5):
    """
    Project point onto surface along a direction using bidirectional raycast.
    This prevents 'edge stepping' artifacts caused by closest_point snapping.

    Args:
        obj: Blender mesh object
        point: Origin point in WORLD space
        direction: Projection direction (usually Interpolated Normal) in WORLD space
        bias: Distance to offset origin to avoid self-intersection
        max_distance: Maximum search distance

    Returns:
        (location, normal, index, distance) or None
    """
    if obj is None or obj.type != 'MESH':
        return None

    dir_vec = Vector(direction).normalized()
    origin = Vector(point)

    # 1. Try Forward Ray (Project from above)
    ray_origin = origin + dir_vec * bias
    hit = raycast_mesh(obj, ray_origin, -dir_vec, max_distance=max_distance + bias)
    if hit:
        return hit

    # 2. Try Backward Ray (Project from below)
    ray_origin = origin - dir_vec * bias
    hit = raycast_mesh(obj, ray_origin, dir_vec, max_distance=max_distance + bias)
    if hit:
        return hit

    # 3. Fallback: Closest Point (Ensures we always hit SOMETHING if nearby)
    return closest_point_on_mesh(obj, point)
