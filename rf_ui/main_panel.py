"""
Main UI Panel for Rail Flow Blender
Sidebar panel with drawing mode buttons and settings.
Redesigned to match Maya Rail Flow structure.
"""

################################################################################
# 🛡️ AI PRE-DEBUG CHECKPOINT: BLENDER UI & LOGIC INTEGRITY
# ------------------------------------------------------------------------------
# TRƯỚC KHI SỬA BẤT KỲ LỖI NÀO, BẠN BẮT BUỘC PHẢI ĐỌC CÁC FILE CẨM NANG SAU:
# 1. [SMART_DEV_HANDBOOK.md](file:///d:/Google_AntiGravity/scratch/Rail_Flow_Blender/docs/AI_ONBOARDING_STANDARDS/SMART_DEV_HANDBOOK.md)
# 2. [COLLABORATION_PROTOCOL.md](file:///d:/Google_AntiGravity/scratch/Rail_Flow_Blender/docs/AI_ONBOARDING_STANDARDS/COLLABORATION_PROTOCOL.md)
# 3. [DAILY_DEVELOPMENT_LOG.md](file:///d:/Google_AntiGravity/scratch/Rail_Flow_Blender/docs/notes/DAILY_DEVELOPMENT_LOG.md)
# ------------------------------------------------------------------------------
# 🇻🇳 NGÔN NGỮ: TIẾNG VIỆT LÀ BẮT BUỘC.
# 🏗️ KIẾN TRÚC: TUÂN THỦ MODULAR (UI tách biệt hoàn toàn CORE).
# ################################################################################

import bpy
from ..rf_core import patch_generator
from ..rf_core import acceleration

class RAILFLOW_OT_freeze_and_set(bpy.types.Operator):
    """Freeze transforms and set as source"""
    bl_idname = "railflow.freeze_and_set"
    bl_label = "Freeze & Set"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj:
            # Maya style: Freeze All (Translate, Rotate, Scale)
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            context.scene.railflow_settings.source_mesh = obj
            
            # Pre-build cache (Maya style)
            acceleration.pre_build(obj)
            
            self.report({'INFO'}, f"Source frozen and set: {obj.name}")
        return {'FINISHED'}

class RAILFLOW_OT_set_source_confirm(bpy.types.Operator):
    """Confirm setting source with unapplied transforms"""
    bl_idname = "railflow.set_source_confirm"
    bl_label = "Transform Warning"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    message: bpy.props.StringProperty()
    
    def execute(self, context):
        return {'FINISHED'}
        
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="⚠️ Non-frozen transforms detected!", icon='ERROR')
        col = layout.column()
        col.label(text="This can lead to inaccurate snapping.")
        col.label(text="Do you want to Freeze Transforms now?")
        
        row = layout.row()
        row.operator("railflow.freeze_and_set", text="Freeze & Set", icon='CHECKMARK')
        # row.operator("railflow.set_source", text="Skip & Set") # This would cause recursion if not careful, let user just click set again
        
class RAILFLOW_OT_set_source(bpy.types.Operator):
    """Set active object as source mesh"""
    bl_idname = "railflow.set_source"
    bl_label = "Set Source"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        context.scene.railflow_settings.source_mesh = obj
        
        # 1. Polycount Guard (Maya style: >500k warning)
        tri_count = sum(len(f.vertices) - 2 for f in obj.data.polygons) # Approx tris
        if tri_count > 500000:
            self.report({'WARNING'}, f"Source '{obj.name}' is too dense ({tri_count:,} tris)! Tool may be slow.")
            
        # 2. Check for unapplied transforms (Maya style: Rotation or Scale)
        has_scale = any(abs(s - 1.0) > 0.001 for s in obj.scale)
        has_rotation = any(abs(r) > 0.001 for r in obj.rotation_euler)
        
        # If skip_confirm is not set, show dialog
        if (has_scale or has_rotation):
            # We use invoke_props_dialog via a separate operator because execute can't be interactive easily here
            bpy.ops.railflow.set_source_confirm('INVOKE_DEFAULT')
            return {'FINISHED'}
            
        # Pre-build cache
        acceleration.pre_build(obj)
        
        self.report({'INFO'}, f"Source set: {obj.name}")
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
# SOURCE MESH
# ============================================
class RAILFLOW_PT_source(bpy.types.Panel):
    """Source mesh panel"""
    bl_label = "Source Mesh"
    bl_idname = "RAILFLOW_PT_source"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings

        if rf.source_mesh is not None:
            layout.label(text=rf.source_mesh.name, icon='MESH_DATA')
        else:
            layout.label(text="No source set", icon='ERROR')

        row = layout.row(align=True)
        op = row.operator("railflow.set_source", text="Add", icon='ADD')
        if op:
            pass # No specific properties to set for this operator in the UI
        op = row.operator("railflow.clear_source", text="Clear", icon='X')
        if op:
            pass # No specific properties to set for this operator in the UI
        
        # Exit Button
        if rf.active_mode != 'NONE':
            layout.separator()
            row = layout.row()
            row.operator("railflow.exit_tool", text="EXIT CURRENT TOOL", icon='X')
        
        layout.separator()
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(rf, "u_divisions", text="U")
        row.prop(rf, "v_divisions", text="V")

# ============================================
# SETTINGS & HOTKEYS
# ============================================
class RAILFLOW_PT_settings(bpy.types.Panel):
    """General settings and hotkeys"""
    bl_label = "Settings"
    bl_idname = "RAILFLOW_PT_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings
        
        row = layout.row(align=True)
        row.prop(rf, "use_xray", text="", icon='XRAY', toggle=True)
        row.prop(rf, "show_hotkey_on_button", text="", icon='TEXT')
        row.prop(rf, "enable_hotkey", text="", icon='PREFERENCES')

        # Wire thickness slider (only show when X-Ray is enabled)
        if rf.use_xray:
            row = layout.row(align=True)
            row.prop(rf, "wire_thickness", text="Wire")

# ============================================
# SYMMETRY
# ============================================
class RAILFLOW_PT_symmetry(bpy.types.Panel):
    """Symmetry settings"""
    bl_label = "Symmetry"
    bl_idname = "RAILFLOW_PT_symmetry"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings
        
        row = layout.row(align=True)
        row.operator("railflow.draw", text="Symmetry", icon='MOD_MIRROR') # Placeholder op
        
        sub = row.row(align=True)
        sub.prop(rf, "symmetry_x", text="X", toggle=True)
        sub.prop(rf, "symmetry_y", text="Y", toggle=True)
        sub.prop(rf, "symmetry_z", text="Z", toggle=True)

# ============================================
# DRAWING MODE
# ============================================
class RAILFLOW_PT_drawing_modes(bpy.types.Panel):
    """Drawing modes panel"""
    bl_label = "Drawing Mode"
    bl_idname = "RAILFLOW_PT_drawing_modes"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings

        col = layout.column(align=True)
        col.scale_y = 1.2

        # --- Poly Draw ---
        op = col.operator("railflow.draw", text="Poly Draw", icon='GREASEPENCIL',
                    depress=rf.active_mode == 'POLY_DRAW')
        if op:
            op.mode = 'POLY_DRAW'
        if rf.active_mode == 'POLY_DRAW':
            box = col.box()
            box.scale_y = 0.8
            box.label(text="Poly Draw Settings", icon='SETTINGS')
            b_col = box.column(align=True)
            b_col.prop(rf, "width", text="Width")
            b_col.prop(rf, "snap_to_surface", text="Snap to Surface")
        
        # --- Tube ---
        col.operator("railflow.tube", text="Tube", icon='MESH_CYLINDER',
                    depress=rf.active_mode == 'TUBE')
        if rf.active_mode == 'TUBE':
            box = col.box()
            box.scale_y = 0.8
            box.label(text="Tube Settings", icon='SETTINGS')
            b_col = box.column(align=True)
            b_col.prop(rf, "tube_segments", text="Segments")
            b_col.prop(rf, "tube_radius", text="Radius")
            b_col.prop(rf, "adaptive_radius", text="Adaptive Radius")
        
        # --- Ecollapse ---
        op = col.operator("railflow.draw", text="Ecollapse", icon='X',
                    depress=rf.active_mode == 'ECOLLAPSE')
        if op:
            op.mode = 'ECOLLAPSE'
        if rf.active_mode == 'ECOLLAPSE':
            box = col.box()
            box.label(text="Ecollapse Settings (Draft)")
        
        # --- Polygon ---
        op = col.operator("railflow.draw", text="Polygon", icon='MESH_PLANE',
                    depress=rf.active_mode == 'POLYGON')
        if op:
            op.mode = 'POLYGON'
        if rf.active_mode == 'POLYGON':
            box = col.box()
            box.label(text="Polygon Settings (Draft)")

# ============================================
# MESH OPERATIONS
# ============================================
class RAILFLOW_PT_mesh_operations(bpy.types.Panel):
    """Mesh operations panel"""
    bl_label = "Mesh Operations"
    bl_idname = "RAILFLOW_PT_mesh_operations"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings
        
        col = layout.column(align=True)
        col.scale_y = 1.1
        
        op = col.operator("railflow.bridge_activate", text="Vertex Bridge", icon='MOD_SKIN',
                    depress=rf.active_mode == 'VBRIDGE')
        if op:
            pass # Active mode is set by operator invoke
        if rf.active_mode == 'VBRIDGE':
            box = col.box()
            box.label(text="Vertex Bridge Setting", icon='LINKED')
            
            b_col = box.column(align=True)
            b_col.label(text="1. Select vertices -> Confirm")
            
            # Confirm Button
            # Note: This will be handled by the modal operator if active, 
            # or it can be a separate operator that starts the modal with selection.
            b_row = b_col.row(align=True)
            b_row.scale_y = 1.2
            op = b_row.operator("railflow.bridge_confirm", text="Confirm Selection", icon='CHECKMARK')
            if op:
                pass
            
            b_col.separator()
            b_col.label(text="Connection Mode:")
            b_col.prop(rf, "bridge_connection_mode", text="")
            
            b_col.separator()
            b_col.prop(rf, "bridge_poly_along_stroke", text="Poly Along Stroke")

        # --- Quaddraw ---
        op = col.operator("railflow.draw", text="Quaddraw", icon='MESH_GRID',
                    depress=rf.active_mode == 'QUADDRAW')
        if op:
            op.mode = 'QUADDRAW'
        if rf.active_mode == 'QUADDRAW':
            box = col.box()
            box.label(text="Quaddraw Settings (Draft)")

        # --- Fill Hole ---
        op = col.operator("railflow.draw", text="Fill Hole", icon='MESH_CIRCLE',
                    depress=rf.active_mode == 'FILL_HOLE')
        if op:
            op.mode = 'FILL_HOLE'
        if rf.active_mode == 'FILL_HOLE':
            box = col.box()
            box.label(text="Fill Hole Settings (Draft)")

# ============================================
# STROKE SETTING
# ============================================
class RAILFLOW_PT_stroke_settings(bpy.types.Panel):
    """Stroke settings panel"""
    bl_label = "Stroke Setting"
    bl_idname = "RAILFLOW_PT_stroke_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings

        col = layout.column(align=True)
        col.prop(rf, "stroke_smooth", text="Smoothness")
        col.prop(rf, "angle_threshold", text="Angle Threshold")

# ============================================
# MESH OPTION
# ============================================
class RAILFLOW_PT_mesh_options(bpy.types.Panel):
    """Mesh options panel"""
    bl_label = "Mesh Option"
    bl_idname = "RAILFLOW_PT_mesh_options"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"

    def draw(self, context):
        layout = self.layout
        rf = context.scene.railflow_settings
        
        layout.prop(rf, "adaptive_blend", text="Adaptive Blend", slider=True)


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


# RAILFLOW_PT_poly_draw_settings and RAILFLOW_PT_tube_settings removed
# Logic integrated into Drawing Mode and Mesh Operations panels contextual drawing.


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




# ============================================
# TECHNICAL PROTOCOLS (Theory Reminder)
# ============================================
class RAILFLOW_PT_protocols(bpy.types.Panel):
    """Technical Protocols panel (Reminder for AI/User)"""
    bl_label = "Technical Protocols"
    bl_idname = "RAILFLOW_PT_protocols"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Rail Flow"
    bl_parent_id = "RAILFLOW_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col = box.column(align=True)
        col.label(text="🛡️ MODE INTEGRITY PROTOCOL", icon='SHIELD')
        col.separator()
        col.label(text="1. STICK TO ACTIVE MODE")
        col.label(text="   Fixing Bridge must NOT break Poly Draw.")
        col.label(text="2. ESCAPE TO LOCK")
        col.label(text="   Press ESC to exit mode & lock meshes.")
        col.label(text="3. UNIQUE METADATA")
        col.label(text="   Each mode creates unique mesh tags.")
        col.separator()
        col.label(text="🇻🇳 Always communicate in VIETNAMESE.")

class RAILFLOW_OT_exit_tool(bpy.types.Operator):
    """Reset active mode to NONE"""
    bl_idname = "railflow.exit_tool"
    bl_label = "Exit Tool"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.railflow_settings.active_mode = 'NONE'
        return {'FINISHED'}

classes = [
    RAILFLOW_OT_set_source,
    RAILFLOW_OT_freeze_and_set,
    RAILFLOW_OT_set_source_confirm,
    RAILFLOW_OT_clear_source,
    RAILFLOW_OT_reload,
    RAILFLOW_OT_exit_tool,
    RAILFLOW_PT_main,
    RAILFLOW_PT_source,
    RAILFLOW_PT_settings,
    RAILFLOW_PT_symmetry,
    RAILFLOW_PT_drawing_modes,
    RAILFLOW_PT_mesh_operations,
    RAILFLOW_PT_stroke_settings,
    RAILFLOW_PT_mesh_options,
    RAILFLOW_PT_help,
    RAILFLOW_PT_protocols,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
