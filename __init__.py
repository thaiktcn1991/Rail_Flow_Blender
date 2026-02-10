# Rail Flow Blender - Retopology Tool
# Ported from Rail Flow Maya by ThaiLuong
# License: GPL-3.0

bl_info = {
    "name": "Rail Flow",
    "author": "ThaiLuong (thaiktcn1991)",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Rail Flow",
    "description": "Advanced retopology tool with multiple drawing modes",
    "warning": "Work in Progress",
    "doc_url": "https://github.com/thaiktcn1991/Rail_Flow_Blender",
    "category": "Mesh",
}

import bpy

from . import rf_operators
from . import rf_ui


classes = []


def register():
    rf_operators.register()
    rf_ui.register()
    print("Rail Flow: Registered")


def unregister():
    rf_ui.unregister()
    rf_operators.unregister()
    print("Rail Flow: Unregistered")


if __name__ == "__main__":
    register()
