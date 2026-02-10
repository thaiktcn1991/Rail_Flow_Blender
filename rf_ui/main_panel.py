"""
Main UI Panel for Rail Flow Blender
Sidebar panel with drawing mode buttons and settings.
"""

import bpy


class RAILFLOW_PT_main(bpy.types.Panel):
    """Rail Flow main panel"""
    bl_label = "Rail Flow"
    bl_idname = "RAILFLOW_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"

    def draw(self, context):
        layout = self.layout

        # Header
        box = layout.box()
        box.label(text="Rail Flow v1.0", icon='MESH_GRID')
        box.label(text="Retopology Tool")

        # Source mesh info
        if context.active_object and context.active_object.type == 'MESH':
            box.label(text=f"Source: {context.active_object.name}", icon='CHECKMARK')
        else:
            box.label(text="Select a source mesh", icon='ERROR')


class RAILFLOW_PT_drawing(bpy.types.Panel):
    """Drawing modes panel"""
    bl_label = "Drawing Modes"
    bl_idname = "RAILFLOW_PT_drawing"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"

    def draw(self, context):
        layout = self.layout

        # Drawing mode buttons
        col = layout.column(align=True)

        # Poly Draw
        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("railflow.draw", text="Poly Draw", icon='GREASEPENCIL')

        # Tube
        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("railflow.tube", text="Tube", icon='MESH_CYLINDER')

        # Placeholder for future modes
        col.separator()
        col.label(text="Coming Soon:", icon='TIME')
        col.label(text="  Bridge Mode")
        col.label(text="  Fill Hole")
        col.label(text="  Edge Loop")


class RAILFLOW_PT_settings(bpy.types.Panel):
    """Settings panel"""
    bl_label = "Settings"
    bl_idname = "RAILFLOW_PT_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Division settings (will be connected to operator properties)
        col = layout.column()
        col.label(text="Default Divisions:")

        row = col.row()
        row.label(text="U:")
        row.label(text="4")
        row.label(text="V:")
        row.label(text="8")

        col.separator()
        col.label(text="Snapping:")
        col.prop(context.scene, "railflow_snap_enabled", text="Snap to Surface")


class RAILFLOW_PT_help(bpy.types.Panel):
    """Help panel"""
    bl_label = "Help"
    bl_idname = "RAILFLOW_PT_help"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.label(text="Instructions:", icon='QUESTION')
        col.label(text="1. Select source mesh")
        col.label(text="2. Click drawing mode")
        col.label(text="3. LMB drag to draw")
        col.label(text="4. ENTER to confirm")
        col.label(text="5. ESC to cancel")

        col.separator()
        col.label(text="Shortcuts:", icon='EVENT_RETURN')
        col.label(text="  [ / ] : Adjust divisions")
        col.label(text="  RMB : Clear stroke")


classes = [
    RAILFLOW_PT_main,
    RAILFLOW_PT_drawing,
    RAILFLOW_PT_settings,
    RAILFLOW_PT_help,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Register scene properties
    bpy.types.Scene.railflow_snap_enabled = bpy.props.BoolProperty(
        name="Snap to Surface",
        default=True,
        description="Snap vertices to source mesh surface"
    )


def unregister():
    # Unregister scene properties
    del bpy.types.Scene.railflow_snap_enabled

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
