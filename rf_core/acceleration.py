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


def hybrid_cpom_snap(obj, point, projection_normal=None, max_distance=2.0):
    """
    HYBRID CPOM SNAP (Ported from Maya V23.50-V23.53)

    Kết hợp Raycast và Closest Point on Mesh (CPOM) để khắc phục:
    - Convex Silhouette: Raycast trượt ra ngoài ở mép lồi
    - Back-Face Snap: Vertex bị hút vào mặt sau
    - Concave Distortion: Lưới bị co cụm vào đáy hố lõm

    Algorithm:
    1. CPOM: Tìm điểm gần nhất (fallback chắc chắn)
    2. Raycast: Thử chiếu theo projection_normal
    3. Normal Consistency: Kiểm tra dot product để tránh back-face
    4. Projective Preservation: Ưu tiên raycast nếu hợp lệ

    Args:
        obj: Blender mesh object
        point: Query point in WORLD space
        projection_normal: Hướng chiếu (nếu None, dùng surface normal từ CPOM)
        max_distance: Khoảng cách tối đa cho snap

    Returns:
        (location, normal, face_index, distance) or None
    """
    if obj is None or obj.type != 'MESH':
        return None

    origin = Vector(point)

    # ========================================================================
    # STEP 1: CPOM - Closest Point on Mesh (Fallback chắc chắn)
    # ========================================================================
    cpom_result = closest_point_on_mesh(obj, origin)

    if cpom_result is None:
        return None

    cpom_loc, cpom_normal, cpom_idx, cpom_dist = cpom_result

    # Convert local location to world space for comparison
    cpom_world = obj.matrix_world @ cpom_loc
    # Transform normal to world space
    cpom_normal_world = (obj.matrix_world.to_3x3() @ cpom_normal).normalized()

    # Nếu không có projection_normal, dùng surface normal từ CPOM
    if projection_normal is None:
        proj_dir = cpom_normal_world
    else:
        proj_dir = Vector(projection_normal).normalized()

    # ========================================================================
    # STEP 2: RAYCAST - Thử chiếu theo hướng projection
    # ========================================================================
    candidates = []

    # Candidate 1: CPOM result (baseline - luôn có)
    candidates.append({
        'location': cpom_loc,
        'normal': cpom_normal,
        'index': cpom_idx,
        'distance': cpom_dist,
        'world_loc': cpom_world,
        'world_normal': cpom_normal_world,
        'type': 'CPOM',
        'score': cpom_dist  # Lower is better
    })

    # Candidate 2: Forward raycast (từ trên xuống)
    bias = 0.5
    ray_origin = origin + proj_dir * bias
    forward_hit = raycast_mesh(obj, ray_origin, -proj_dir, max_distance=max_distance + bias)

    if forward_hit:
        fwd_loc, fwd_norm, fwd_idx, fwd_dist = forward_hit
        fwd_world = obj.matrix_world @ fwd_loc
        fwd_norm_world = (obj.matrix_world.to_3x3() @ fwd_norm).normalized()

        candidates.append({
            'location': fwd_loc,
            'normal': fwd_norm,
            'index': fwd_idx,
            'distance': (fwd_world - origin).length,
            'world_loc': fwd_world,
            'world_normal': fwd_norm_world,
            'type': 'FORWARD_RAY',
            'score': (fwd_world - origin).length
        })

    # Candidate 3: Backward raycast (từ dưới lên)
    ray_origin = origin - proj_dir * bias
    backward_hit = raycast_mesh(obj, ray_origin, proj_dir, max_distance=max_distance + bias)

    if backward_hit:
        bwd_loc, bwd_norm, bwd_idx, bwd_dist = backward_hit
        bwd_world = obj.matrix_world @ bwd_loc
        bwd_norm_world = (obj.matrix_world.to_3x3() @ bwd_norm).normalized()

        candidates.append({
            'location': bwd_loc,
            'normal': bwd_norm,
            'index': bwd_idx,
            'distance': (bwd_world - origin).length,
            'world_loc': bwd_world,
            'world_normal': bwd_norm_world,
            'type': 'BACKWARD_RAY',
            'score': (bwd_world - origin).length
        })

    # ========================================================================
    # STEP 3: NORMAL CONSISTENCY - Check dot product để tránh back-face
    # ========================================================================
    BACKFACE_PENALTY = 1000.0  # Phạt nặng nếu snap vào mặt sau
    RAYCAST_BONUS = -0.1      # Ưu tiên raycast result (Projective Preservation)

    for c in candidates:
        # Check if normal is facing towards us (dot > 0 = front face)
        # We use projection direction as "view direction"
        dot = c['world_normal'].dot(proj_dir)

        if dot < 0:
            # Back-face detected! Apply penalty (V23.51 Normal Consistency)
            c['score'] += BACKFACE_PENALTY

        # Projective Preservation (V23.52): Bonus cho raycast results
        if c['type'] in ['FORWARD_RAY', 'BACKWARD_RAY']:
            c['score'] += RAYCAST_BONUS

    # ========================================================================
    # STEP 4: SELECT BEST CANDIDATE
    # ========================================================================
    # Sort by score (lower is better)
    candidates.sort(key=lambda x: x['score'])
    best = candidates[0]

    # Filter out back-face results if we have front-face options
    front_face_candidates = [c for c in candidates if c['score'] < BACKFACE_PENALTY]
    if front_face_candidates:
        best = front_face_candidates[0]

    # Distance sanity check - không snap nếu quá xa
    if best['distance'] > max_distance:
        return None

    return (best['location'], best['normal'], best['index'], best['distance'])
