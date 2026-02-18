"""
Rail Draw Operator (Poly Draw)
"""
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from bpy_extras import view3d_utils

from ..rf_core import patch_generator, acceleration


class RAILFLOW_OT_draw(bpy.types.Operator):
    """Draw rail strokes to create retopology mesh"""
    bl_idname = "railflow.draw"
    bl_label = "Rail Draw"
    bl_options = {'REGISTER', 'UNDO'}

    # Properties
    u_divisions: bpy.props.IntProperty(
        name="U Divisions",
        default=4,
        min=1, max=32,
        description="Divisions across width"
    )
    v_divisions: bpy.props.IntProperty(
        name="V Divisions",
        default=8,
        min=2, max=64,
        description="Divisions along length"
    )
    width: bpy.props.FloatProperty(
        name="Width",
        default=0.5,
        min=0.01, max=10.0,
        description="Patch width"
    )
    snap_to_surface: bpy.props.BoolProperty(
        name="Snap to Surface",
        default=True,
        description="Snap vertices to source mesh surface"
    )

    mode: bpy.props.StringProperty(
        name="Mode",
        default='POLY_DRAW'
    )

    # Internal state
    _strokes = []  # List of strokes
    _current_stroke = []  # Current stroke
    _is_drawing = False
    _source_obj = None
    _active_obj = None  # Track the current mesh being generated in this session
    _draw_handler = None

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        # Get source mesh from settings or active object
        rf = context.scene.railflow_settings
        if rf.source_mesh is not None:
            self._source_obj = rf.source_mesh
        elif context.active_object and context.active_object.type == 'MESH':
            self._source_obj = context.active_object
        else:
            self.report({'WARNING'}, "Please set a source mesh first (click 'Set' button)")
            return {'CANCELLED'}

        # Set active mode
        rf.active_mode = self.mode

        # Initialize
        self._strokes = []
        self._current_stroke = []
        self._is_drawing = False

        # Add draw handler
        self._draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, (), 'WINDOW', 'POST_VIEW'
        )

        # Start modal
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set("Rail Draw: LMB to draw, ENTER to confirm, ESC to cancel")

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        context.area.tag_redraw()

        # Mouse move
        if event.type == 'MOUSEMOVE':
            if self._is_drawing:
                point = self.get_surface_point(context, event)
                if point is not None:
                    if len(self._current_stroke) == 0:
                        self._current_stroke.append(point)
                    else:
                        last_point = Vector(self._current_stroke[-1])
                        if (Vector(point) - last_point).length > 0.01:
                            self._current_stroke.append(point)

        # Left mouse
        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                self._is_drawing = True
                
                # NITRO ITERATIVE DRAWING: 
                # POLYGON: Replaces on every stroke (Single loop tool)
                # POLY_DRAW & VBRIDGE: Accumulate for multi-rail/chaining
                rf = context.scene.railflow_settings
                if rf.active_mode == 'POLYGON':
                    self._strokes = []
                
                self._current_stroke = []
                point = self.get_surface_point(context, event)
                if point is not None:
                    self._current_stroke.append(point)
            elif event.value == 'RELEASE':
                self._is_drawing = False
                if len(self._current_stroke) >= 2:
                    self._strokes.append(self._current_stroke.copy())
                    
                    # NITRO WORKFLOW: Auto-generate on release ONLY for Bridge and Polygon
                    # Poly Draw waits for ENTER to allow multi-stroke lofting
                    rf = context.scene.railflow_settings
                    if rf.active_mode in {'VBRIDGE', 'POLYGON'} and len(self._strokes) >= 1:
                        self.generate_mesh(context)
                self._current_stroke = []

        # Enter
        elif event.type in {'RET', 'NUMPAD_ENTER'}:
            if len(self._strokes) >= 1:
                self.generate_mesh(context)
            self.cleanup(context)
            return {'FINISHED'}

        # Escape
        elif event.type == 'ESC':
            self.cleanup(context)
            return {'CANCELLED'}

        # Scroll - Adjust Divisions
        elif event.type == 'WHEELUPMOUSE':
            if event.ctrl:
                self.v_divisions += 1
                context.scene.railflow_settings.v_divisions = self.v_divisions
                context.area.header_text_set(f"V Divisions: {self.v_divisions}")
            else:
                self.u_divisions += 1
                context.scene.railflow_settings.u_divisions = self.u_divisions
                context.area.header_text_set(f"U Divisions: {self.u_divisions}")
            return {'RUNNING_MODAL'}

        elif event.type == 'WHEELDOWNMOUSE':
            if event.ctrl:
                self.v_divisions = max(2, self.v_divisions - 1)
                context.scene.railflow_settings.v_divisions = self.v_divisions
                context.area.header_text_set(f"V Divisions: {self.v_divisions}")
            else:
                self.u_divisions = max(1, self.u_divisions - 1)
                context.scene.railflow_settings.u_divisions = self.u_divisions
                context.area.header_text_set(f"U Divisions: {self.u_divisions}")
            return {'RUNNING_MODAL'}

        # Right click
        elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            self._strokes = []
            self._current_stroke = []

        return {'RUNNING_MODAL'}

    def get_surface_point(self, context, event):
        if self._source_obj is None:
            return None

        region = context.region
        rv3d = context.region_data
        coord = (event.mouse_region_x, event.mouse_region_y)

        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)

        result = acceleration.raycast_mesh(
            self._source_obj,
            ray_origin,
            ray_direction
        )

        if result is not None:
            location, normal, index, distance = result
            world_location = self._source_obj.matrix_world @ location
            return world_location

    def generate_mesh(self, context):
        if len(self._strokes) == 0 and context.scene.railflow_settings.active_mode != 'VBRIDGE':
            return

        try:
            rf = context.scene.railflow_settings

            if rf.active_mode == 'VBRIDGE' and rf.bridge_vertex_indices:
                # Vertex Bridge Mode: Chain Selection -> S1 -> S2 -> ...
                indices = [int(i) for i in rf.bridge_vertex_indices.split(",") if i]
                source_obj = bpy.data.objects.get(rf.bridge_object_name)
                
                if source_obj and indices and self._strokes:
                    # 1. Extract selection world positions as a virtual first stroke
                    mat = source_obj.matrix_world
                    selection_verts = [mat @ source_obj.data.vertices[i].co for i in indices]
                    
                    # 2. Prepend to strokes
                    all_profiles = [selection_verts] + self._strokes
                    
                    # 3. Generate using multi-rail logic with SEGMENTED mode
                    obj = patch_generator.generate_multi_rail_patch(
                        strokes=all_profiles,
                        u_divisions=rf.u_divisions,
                        v_divisions=rf.v_divisions,
                        source_obj=self._source_obj if self.snap_to_surface else None,
                        snap_to_surface=rf.snap_to_surface,
                        segmented=True # BRIDGE MUST BE SEGMENTED
                    )
                    
                    if obj is not None:
                        # NITRO RECYCLING
                        if self._active_obj:
                            data = self._active_obj.data
                            bpy.data.objects.remove(self._active_obj, do_unlink=True)
                            if data.users == 0:
                                bpy.data.meshes.remove(data)
                        
                        self._active_obj = obj
                        bpy.ops.object.select_all(action='DESELECT')
                        obj.select_set(True)
                        context.view_layer.objects.active = obj
                        self.report({'INFO'}, f"Bridge Chain: {len(obj.data.polygons)} faces")

            elif len(self._strokes) == 1:
                obj = patch_generator.generate_quad_patch(
                    stroke_points=self._strokes[0],
                    u_divisions=self.u_divisions,
                    v_divisions=self.v_divisions,
                    width=self.width,
                    source_obj=self._source_obj if self.snap_to_surface else None,
                    snap_to_surface=self.snap_to_surface
                )
                if obj is not None:
                    # NITRO RECYCLING
                    if self._active_obj:
                        data = self._active_obj.data
                        bpy.data.objects.remove(self._active_obj, do_unlink=True)
                        if data.users == 0:
                            bpy.data.meshes.remove(data)
                    
                    self._active_obj = obj
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    self.report({'INFO'}, f"Single Rail: {len(obj.data.polygons)} faces")

            else:
                obj = patch_generator.generate_multi_rail_patch(
                    strokes=self._strokes,
                    u_divisions=self.u_divisions,
                    v_divisions=self.v_divisions,
                    source_obj=self._source_obj if self.snap_to_surface else None,
                    snap_to_surface=self.snap_to_surface
                )
                if obj is not None:
                    # NITRO RECYCLING: Delete previous mesh in this session
                    if self._active_obj:
                        data = self._active_obj.data
                        bpy.data.objects.remove(self._active_obj, do_unlink=True)
                        if data.users == 0:
                            bpy.data.meshes.remove(data)
                    
                    self._active_obj = obj
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    self.report({'INFO'}, f"Multi Rail ({len(self._strokes)} strokes): {len(obj.data.polygons)} faces")

        except Exception as e:
            # NITRO ERROR DETECTION: Fast reporting to user
            err_msg = f"GENERATE ERROR: {str(e)}"
            self.report({'ERROR'}, err_msg)
            print(f">>> [NITRO_CORE] {err_msg}")
            import traceback
            traceback.print_exc()

    def draw_callback(self):
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.line_width_set(3.0)
        gpu.state.blend_set('ALPHA')

        colors = [
            (1.0, 0.5, 0.0, 0.8),  # Orange
            (0.0, 1.0, 0.5, 0.8),  # Green
            (0.5, 0.0, 1.0, 0.8),  # Purple
            (1.0, 1.0, 0.0, 0.8),  # Yellow
        ]

        for i, stroke in enumerate(self._strokes):
            if len(stroke) >= 2:
                color = colors[i % len(colors)]
                coords = [tuple(p) for p in stroke]
                batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
                shader.bind()
                shader.uniform_float("color", color)
                batch.draw(shader)

                gpu.state.point_size_set(8.0)
                batch_points = batch_for_shader(shader, 'POINTS', {"pos": coords})
                shader.uniform_float("color", (1.0, 1.0, 1.0, 1.0))
                batch_points.draw(shader)

        if len(self._current_stroke) >= 2:
            coords = [tuple(p) for p in self._current_stroke]
            batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
            shader.bind()
            shader.uniform_float("color", (1.0, 0.0, 0.0, 0.9))
            batch.draw(shader)

            gpu.state.point_size_set(10.0)
            batch_points = batch_for_shader(shader, 'POINTS', {"pos": coords})
            shader.uniform_float("color", (1.0, 1.0, 0.0, 1.0))
            batch_points.draw(shader)

        gpu.state.blend_set('NONE')
        gpu.state.line_width_set(1.0)
        gpu.state.point_size_set(1.0)

    def cleanup(self, context):
        if self._draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handler, 'WINDOW')
            self._draw_handler = None

        context.area.header_text_set(None)
        self._strokes = []
        self._current_stroke = []
        self._is_drawing = False
        self._active_obj = None


def register():
    bpy.utils.register_class(RAILFLOW_OT_draw)


def unregister():
    bpy.utils.unregister_class(RAILFLOW_OT_draw)
