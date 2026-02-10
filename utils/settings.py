"""
Settings Manager for Rail Flow Blender
Handles persistent user preferences.
"""

import bpy


def get_addon_preferences():
    """Get addon preferences"""
    addon_name = __package__.split('.')[0]
    return bpy.context.preferences.addons.get(addon_name)


class RailFlowSettings:
    """
    Centralized settings access.
    Uses Blender's addon preferences for persistence.
    """

    # Default values
    DEFAULTS = {
        'u_divisions': 4,
        'v_divisions': 8,
        'width': 0.5,
        'tube_radius': 0.1,
        'tube_segments': 8,
        'snap_to_surface': True,
        'show_preview': True,
    }

    @classmethod
    def get(cls, key, default=None):
        """Get setting value"""
        if default is None:
            default = cls.DEFAULTS.get(key)

        # Try to get from scene properties first
        scene = bpy.context.scene
        prop_name = f"railflow_{key}"

        if hasattr(scene, prop_name):
            return getattr(scene, prop_name)

        return default

    @classmethod
    def set(cls, key, value):
        """Set setting value"""
        scene = bpy.context.scene
        prop_name = f"railflow_{key}"

        if hasattr(scene, prop_name):
            setattr(scene, prop_name, value)
