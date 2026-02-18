"""
Vertex Bridge Operator
"""
import bpy
import bmesh
from .op_rail import RAILFLOW_OT_draw

class RAILFLOW_OT_bridge_activate(bpy.types.Operator):
    """Activate bridge selection mode"""
    bl_idname = "railflow.bridge_activate"
    bl_label = "Vertex Bridge"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        rf = context.scene.railflow_settings
        target_obj = context.active_object
        
        # Ensure we are in object mode to start cleanly
        if target_obj and target_obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # VALIDATION: Ensure we have a valid mesh that isn't the high-poly source
        if not (target_obj and target_obj.type == 'MESH' and target_obj != rf.source_mesh):
            # If no retopo mesh selected, try to find any mesh that isn't the source
            found_retopo = None
            for o in context.selected_objects:
                if o.type == 'MESH' and o != rf.source_mesh:
                    found_retopo = o
                    break
            
            if found_retopo:
                target_obj = found_retopo
                context.view_layer.objects.active = target_obj
            else:
                self.report({'WARNING'}, "Select the retopo mesh first!")
                return {'CANCELLED'}

        # Switch to VBRIDGE mode
        rf.active_mode = 'VBRIDGE'
        
        # Switch to Edit Mode for vertex selection on the target retopo mesh
        bpy.ops.object.select_all(action='DESELECT')
        target_obj.select_set(True)
        context.view_layer.objects.active = target_obj
        
        bpy.ops.object.mode_set(mode='EDIT')
            
        # Set to Vertex selection mode
        context.tool_settings.mesh_select_mode = (True, False, False)
        
        self.report({'INFO'}, f"Bridge Mode: Selecting vertices on {target_obj.name}")
        return {'FINISHED'}

class RAILFLOW_OT_bridge_confirm(bpy.types.Operator):
    """Confirm vertex selection and start bridging"""
    bl_idname = "railflow.bridge_confirm"
    bl_label = "Confirm Bridge Selection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        rf = context.scene.railflow_settings
        return rf.active_mode == 'VBRIDGE' and context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        rf = context.scene.railflow_settings

        # Ensure we are in object mode to read selection reliably
        was_edit = False
        if obj.mode == 'EDIT':
            was_edit = True
            bpy.ops.object.mode_set(mode='OBJECT')

        # Get selected vertices
        selected_verts = [v.index for v in obj.data.vertices if v.select]
        
        if not selected_verts:
            self.report({'WARNING'}, "No vertices selected! Please select a vertex loop in Edit Mode.")
            if was_edit:
                bpy.ops.object.mode_set(mode='EDIT')
            return {'CANCELLED'}

        # Store selection in settings
        rf.bridge_vertex_indices = ",".join(map(str, selected_verts))
        rf.bridge_object_name = obj.name
        
        # NITRO SYNC: Match divisions to selection for topological parity
        rf.v_divisions = max(2, len(selected_verts) - 1)
        
        print(f">>> Bridge confirmed: {len(selected_verts)} vertices selected on {obj.name}. Syncing V-Divisions to {rf.v_divisions}")
        
        # Start the draw operator in VBRIDGE mode
        bpy.ops.railflow.draw('INVOKE_DEFAULT', mode='VBRIDGE')
        
        return {'FINISHED'}

def register():
    bpy.utils.register_class(RAILFLOW_OT_bridge_activate)
    bpy.utils.register_class(RAILFLOW_OT_bridge_confirm)

def unregister():
    bpy.utils.unregister_class(RAILFLOW_OT_bridge_confirm)
    bpy.utils.unregister_class(RAILFLOW_OT_bridge_activate)
