"""
Main UI Panel for Rail Flow Blender
Sidebar panel with drawing mode buttons and settings.
Redesigned to match Maya Rail Flow structure.
"""

import bpy


class RAILFLOW_OT_set_source(bpy.types.Operator):
    """Set active object as source mesh"""
    bl_idname = "railflow.set_source"
    bl_label = "Set Source"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        context.scene.railflow_settings.source_mesh = context.active_object
        self.report({'INFO'}, f"Source set: {context.active_object.name}")
        return {'FINISHED'}


class RAILFLOW_OT_clear_source(bpy.types.Operator):
    """Clear source mesh"""
    bl_idname = "railflow.clear_source"
    bl_label = "Clear Source"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.railflow_settings.source_mesh is not None

    def execute(self, context):
        context.scene.railflow_settings.source_mesh = None
        self.report({'INFO'}, "Source cleared")
        return {'FINISHED'}


# ============================================
# MAIN PANEL
# ============================================
class RAILFLOW_PT_main(bpy.types.Panel):
    """Rail Flow main panel"""
    bl_label = "Rail Flow"
    bl_idname = "RAILFLOW_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"

    def draw(self, context):
        layout = self.layout
        layout.label(text="v1.1", icon='MESH_GRID')


# ============================================
# SOURCE MESH (Collapsible)
# ============================================
class RAILFLOW_PT_source(bpy.types.Panel):
    """Source mesh panel"""
    bl_label = "Source Mesh"
    bl_idname = "RAILFLOW_PT_source"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        rf = context.scene.railflow_settings
        if rf.source_mesh is not None:
            self.layout.label(text="", icon='CHECKMARK')
        else:
            self.layout.label(text="", icon='ERROR')

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings

        if rf.source_mesh is not None:
            row = layout.row()
            row.label(text=rf.source_mesh.name)
            face_count = len(rf.source_mesh.data.polygons)
            row.label(text=f"({face_count:,} faces)")
        else:
            layout.label(text="No source set")

        row = layout.row(align=True)
        row.operator("railflow.set_source", text="Set", icon='ADD')
        row.operator("railflow.clear_source", text="Clear", icon='X')
        
        layout.separator()
        row = layout.row()
        row.prop(rf, "use_xray", text="X-Ray", toggle=True, icon='XRAY')


# ============================================
# DO ON MESH
# ============================================
class RAILFLOW_PT_do_on_mesh(bpy.types.Panel):
    """Drawing modes panel"""
    bl_label = "Do on Mesh"
    bl_idname = "RAILFLOW_PT_do_on_mesh"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings

        col = layout.column(align=True)

        # Poly Draw
        row = col.row(align=True)
        row.scale_y = 1.5
        op = row.operator("railflow.draw", text="Poly Draw", icon='GREASEPENCIL',
                         depress=rf.active_mode == 'POLY_DRAW')
        op.u_divisions = rf.u_divisions
        op.v_divisions = rf.v_divisions
        op.width = rf.width
        op.snap_to_surface = rf.snap_to_surface

        # Tube
        row = col.row(align=True)
        row.scale_y = 1.5
        op = row.operator("railflow.tube", text="Tube", icon='MESH_CYLINDER',
                         depress=rf.active_mode == 'TUBE')
        op.segments = rf.tube_segments
        op.v_divisions = rf.v_divisions
        op.radius = rf.tube_radius
        op.adaptive_radius = rf.adaptive_radius

        # Future modes
        col.separator()
        sub = col.column(align=True)
        sub.enabled = False
        sub.scale_y = 1.2
        sub.operator("railflow.draw", text="Bridge", icon='MOD_SKIN')
        sub.operator("railflow.draw", text="Fill Hole", icon='MESH_CIRCLE')
        sub.operator("railflow.draw", text="Edge Loop", icon='MESH_TORUS')


# ============================================
# STROKE SETTINGS
# ============================================
class RAILFLOW_PT_stroke_settings(bpy.types.Panel):
    """Stroke settings panel"""
    bl_label = "Stroke Settings"
    bl_idname = "RAILFLOW_PT_stroke_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings

        col = layout.column(align=True)
        col.prop(rf, "stroke_spacing", text="Spacing")
        col.prop(rf, "stroke_smooth", text="Smooth")
        col.prop(rf, "snap_to_surface", text="Snap to Surface")


# ============================================
# MESH SETTINGS
# ============================================
class RAILFLOW_PT_mesh_settings(bpy.types.Panel):
    """Mesh generation settings panel"""
    bl_label = "Mesh Settings"
    bl_idname = "RAILFLOW_PT_mesh_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(rf, "u_divisions", text="U")
        row.prop(rf, "v_divisions", text="V")

        col.prop(rf, "width", text="Width", slider=True)


# ============================================
# POLY DRAW MODE SETTINGS (shows when active)
# ============================================
class RAILFLOW_PT_poly_draw_settings(bpy.types.Panel):
    """Poly Draw mode specific settings"""
    bl_label = "Poly Draw Settings"
    bl_idname = "RAILFLOW_PT_poly_draw_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        rf = context.scene.railflow_settings
        return rf.active_mode == 'POLY_DRAW'

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(rf, "u_divisions", text="U Divisions")
        row = col.row(align=True)
        row.prop(rf, "v_divisions", text="V Divisions")
        col.prop(rf, "width", text="Width", slider=True)
        col.prop(rf, "snap_to_surface", text="Snap to Surface")


# ============================================
# TUBE MODE SETTINGS (shows when active)
# ============================================
class RAILFLOW_PT_tube_settings(bpy.types.Panel):
    """Tube mode specific settings"""
    bl_label = "Tube Settings"
    bl_idname = "RAILFLOW_PT_tube_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        rf = context.scene.railflow_settings
        return rf.active_mode == 'TUBE'

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings

        col = layout.column(align=True)
        col.prop(rf, "tube_segments", text="Segments")
        col.prop(rf, "v_divisions", text="V Divisions")
        col.prop(rf, "tube_radius", text="Radius", slider=True)
        col.prop(rf, "adaptive_radius", text="Adaptive Radius")


class RAILFLOW_OT_reload(bpy.types.Operator):
    """Reload Rail Flow addon"""
    bl_idname = "railflow.reload"
    bl_label = "Reload Add-on"

    def execute(self, context):
        import importlib
        import sys

        # Unregister
        from .. import rf_operators, rf_ui
        rf_ui.unregister()
        rf_operators.unregister()

        # Reload modules
        modules_to_reload = [key for key in sys.modules.keys() if 'Rail_Flow_Blender' in key]
        for mod_name in modules_to_reload:
            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])

        # Re-register
        rf_operators.register()
        rf_ui.register()

        self.report({'INFO'}, "Rail Flow reloaded!")
        return {'FINISHED'}


class RAILFLOW_PT_help(bpy.types.Panel):
    """Help panel"""
    bl_label = "Help & Info"
    bl_idname = "RAILFLOW_PT_help"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Poly Draw instructions
        box = layout.box()
        box.label(text="Poly Draw Mode", icon='GREASEPENCIL')
        col = box.column(align=True)
        col.label(text="1 stroke = Single Rail")
        col.label(text="2+ strokes = Multi Rail")

        # Controls
        box = layout.box()
        box.label(text="Controls", icon='MOUSE_LMB')
        col = box.column(align=True)
        col.scale_y = 0.9

        row = col.row()
        row.label(text="LMB Drag", icon='MOUSE_LMB')
        row.label(text="Draw stroke")

        row = col.row()
        row.label(text="Enter", icon='EVENT_RETURN')
        row.label(text="Generate mesh")

        row = col.row()
        row.label(text="RMB", icon='MOUSE_RMB')
        row.label(text="Clear strokes")

        row = col.row()
        row.label(text="Esc", icon='EVENT_ESC')
        row.label(text="Cancel")

        # Developer section
        layout.separator()
        row = layout.row()
        row.operator("railflow.reload", text="Reload Add-on", icon='FILE_REFRESH')





classes = [
    RAILFLOW_OT_set_source,
    RAILFLOW_OT_clear_source,
    RAILFLOW_OT_reload,
    RAILFLOW_PT_main,
    RAILFLOW_PT_source,
    RAILFLOW_PT_do_on_mesh,
    RAILFLOW_PT_stroke_settings,
    RAILFLOW_PT_mesh_settings,
    RAILFLOW_PT_poly_draw_settings,
    RAILFLOW_PT_tube_settings,
    RAILFLOW_PT_help,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
