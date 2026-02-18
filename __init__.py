# Rail Flow Blender - Retopology Tool
# Ported from Rail Flow Maya by ThaiLuong
# License: GPL-3.0

bl_info = {
    "name": "Rail Flow",
    "author": "ThaiLuong (thaiktcn1991)",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Rail Flow",
    "description": "Advanced retopology tool (Blender Edition V1.1)",
    "doc_url": "https://github.com/thaiktcn1991/Rail_Flow_Blender",
    "category": "Mesh",
}

import bpy

from . import rf_properties
from . import rf_operators
from . import rf_ui


classes = []


def register():
    rf_properties.register()
    rf_operators.register()
    rf_ui.register()
    print("Rail Flow: Registered")


def unregister():
    rf_ui.unregister()
    rf_operators.unregister()
    rf_properties.unregister()
    print("Rail Flow: Unregistered")


if __name__ == "__main__":
    register()
