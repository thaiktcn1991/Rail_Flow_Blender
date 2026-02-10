"""
Spatial Acceleration for Rail Flow Blender
Uses Blender's BVHTree for fast raycasting and nearest point queries.

Replaces Maya's MMeshIntersector with equivalent Blender functionality.
"""

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


class SpatialManager:
    """
    Singleton manager for spatial acceleration structures.
    Caches BVHTree instances to avoid rebuilding on every query.
    """

    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._cache = {}
        return cls._instance

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_bvh(self, obj, force_update=False):
        """
        Get or create BVHTree for an object.

        Args:
            obj: Blender mesh object
            force_update: Force rebuild of BVH tree

        Returns:
            BVHTree instance
        """
        if obj is None or obj.type != 'MESH':
            return None

        key = obj.name

        if not force_update and key in self._cache:
            return self._cache[key]

        # Build BVH from object's evaluated mesh
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()

        bvh = BVHTree.FromObject(obj, depsgraph)

        # Cache it
        self._cache[key] = bvh

        obj_eval.to_mesh_clear()

        return bvh

    def get_closest_point(self, obj, point):
        """
        Find closest point on mesh surface to given point.

        Args:
            obj: Blender mesh object
            point: Query point (Vector or tuple)

        Returns:
            (location, normal, index, distance) or None
        """
        bvh = self.get_bvh(obj)
        if bvh is None:
            return None

        point = Vector(point)
        location, normal, index, distance = bvh.find_nearest(point)

        return (location, normal, index, distance)

    def raycast(self, obj, origin, direction, max_distance=1e10):
        """
        Cast ray against mesh and find intersection.

        Args:
            obj: Blender mesh object
            origin: Ray origin (Vector or tuple)
            direction: Ray direction (Vector or tuple)
            max_distance: Maximum ray distance

        Returns:
            (location, normal, index, distance) or None
        """
        bvh = self.get_bvh(obj)
        if bvh is None:
            return None

        origin = Vector(origin)
        direction = Vector(direction).normalized()

        location, normal, index, distance = bvh.ray_cast(origin, direction, max_distance)

        if location is None:
            return None

        return (location, normal, index, distance)

    def clear_cache(self, obj_name=None):
        """
        Clear cached BVH trees.

        Args:
            obj_name: Specific object to clear, or None for all
        """
        if obj_name is None:
            self._cache.clear()
        elif obj_name in self._cache:
            del self._cache[obj_name]

    def invalidate_all(self):
        """Clear all cached data"""
        self._cache.clear()


# Convenience functions
def get_spatial_manager():
    return SpatialManager.get_instance()


def closest_point_on_mesh(obj, point):
    """Shortcut for finding closest point on mesh"""
    return get_spatial_manager().get_closest_point(obj, point)


def raycast_mesh(obj, origin, direction, max_distance=1e10):
    """Shortcut for raycasting against mesh"""
    return get_spatial_manager().raycast(obj, origin, direction, max_distance)
