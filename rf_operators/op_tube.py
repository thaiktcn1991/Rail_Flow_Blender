"""
Tube Draw Operator
"""
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from bpy_extras import view3d_utils

from ..rf_core import patch_generator, acceleration


class RAILFLOW_OT_tube(bpy.types.Operator):
    """Draw tube mesh along stroke"""
    bl_idname = "railflow.tube"
    bl_label = "Tube Draw"
    bl_options = {'REGISTER', 'UNDO'}

    segments: bpy.props.IntProperty(
        name="Segments",
        default=8,
        min=3, max=32
    )
    v_divisions: bpy.props.IntProperty(
        name="V Divisions",
        default=8,
        min=2, max=64
    )
    radius: bpy.props.FloatProperty(
        name="Radius",
        default=0.1,
        min=0.001, max=10.0
    )
    adaptive_radius: bpy.props.BoolProperty(
        name="Adaptive Radius",
        default=False
    )

    _stroke_points = []
    _is_drawing = False
    _active_obj = None
    _source_obj = None
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
        rf.active_mode = 'TUBE'

        self._stroke_points = []
        self._is_drawing = False

        self._draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, (), 'WINDOW', 'POST_VIEW'
        )

        context.window_manager.modal_handler_add(self)
        context.area.header_text_set("Tube Draw: LMB to draw, ENTER to confirm, ESC to cancel")

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            if self._is_drawing:
                point = self.get_surface_point(context, event)
                if point is not None:
                    if len(self._stroke_points) == 0:
                        self._stroke_points.append(point)
                    else:
                        last_point = Vector(self._stroke_points[-1])
                        if (Vector(point) - last_point).length > 0.01:
                            self._stroke_points.append(point)

        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                self._is_drawing = True
                point = self.get_surface_point(context, event)
                if point is not None:
                    self._stroke_points.append(point)
            elif event.value == 'RELEASE':
                self._is_drawing = False
                # Auto-generate mesh when release mouse
                if len(self._stroke_points) >= 2:
                    self.generate_mesh(context)
                    self._stroke_points = []  # Clear for next stroke

        elif event.type in {'RET', 'NUMPAD_ENTER'}:
            self.cleanup(context)
            return {'FINISHED'}

        # Scroll - Adjust Segments
        elif event.type == 'WHEELUPMOUSE':
            if event.ctrl:
                self.v_divisions += 1
                context.scene.railflow_settings.v_divisions = self.v_divisions
                context.area.header_text_set(f"V Divisions: {self.v_divisions}")
            else:
                self.segments += 1
                context.scene.railflow_settings.tube_segments = self.segments
                context.area.header_text_set(f"Segments: {self.segments}")
            return {'RUNNING_MODAL'}

        elif event.type == 'WHEELDOWNMOUSE':
            if event.ctrl:
                self.v_divisions = max(2, self.v_divisions - 1)
                context.scene.railflow_settings.v_divisions = self.v_divisions
                context.area.header_text_set(f"V Divisions: {self.v_divisions}")
            else:
                self.segments = max(3, self.segments - 1)
                context.scene.railflow_settings.tube_segments = self.segments
                context.area.header_text_set(f"Segments: {self.segments}")
            return {'RUNNING_MODAL'}

        elif event.type == 'ESC':
            self.cleanup(context)
            return {'CANCELLED'}

        elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            self._stroke_points = []

        return {'RUNNING_MODAL'}

    def get_surface_point(self, context, event):
        if self._source_obj is None:
            return None

        region = context.region
        rv3d = context.region_data
        coord = (event.mouse_region_x, event.mouse_region_y)

        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)

        result = acceleration.raycast_mesh(self._source_obj, ray_origin, ray_direction)

        if result is not None:
            location, normal, index, distance = result
            world_location = self._source_obj.matrix_world @ location
            return world_location

        return None

    def generate_mesh(self, context):
        if len(self._stroke_points) < 2:
            return

        obj = patch_generator.generate_tube(
            stroke_points=self._stroke_points,
            segments=self.segments,
            v_divisions=self.v_divisions,
            radius=self.radius,
            source_obj=self._source_obj if self.adaptive_radius else None,
            adaptive_radius=self.adaptive_radius
        )

        if obj is not None:
            # NITRO RECYCLING
            if self._active_obj:
                data = self._active_obj.data
                bpy.data.objects.remove(self._active_obj, do_unlink=True)
                if data.users == 0:
                    bpy.data.meshes.remove(data)
            
            self._active_obj = obj
            
            # NITRO SMART NORMAL
            if self._source_obj:
                patch_generator.enforce_outward_normals(obj, self._source_obj)
                
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
            self.report({'INFO'}, f"Created tube with {len(obj.data.polygons)} faces")
        
        # Don't clear stroke points here if you want post-draw slider updates?
        # Actually Tube uses its own radius/segments props which update the mesh.
        # If we clear strokes, we can't rebuild!
        # Reversion: Keep strokes until next draw.

    def draw_callback(self):
        if len(self._stroke_points) < 2:
            return

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.line_width_set(3.0)
        gpu.state.blend_set('ALPHA')

        coords = [tuple(p) for p in self._stroke_points]
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})

        shader.bind()
        shader.uniform_float("color", (0.0, 1.0, 0.5, 0.8))  # Cyan-green
        batch.draw(shader)

        gpu.state.point_size_set(8.0)
        batch_points = batch_for_shader(shader, 'POINTS', {"pos": coords})
        shader.uniform_float("color", (0.0, 1.0, 1.0, 1.0))  # Cyan
        batch_points.draw(shader)

        gpu.state.blend_set('NONE')
        gpu.state.line_width_set(1.0)
        gpu.state.point_size_set(1.0)

    def cleanup(self, context):
        if self._draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handler, 'WINDOW')
            self._draw_handler = None

        # context.scene.railflow_settings.active_mode = 'NONE' # Don't reset to allow post-draw editing
        context.area.header_text_set(None)
        self._stroke_points = []
        self._is_drawing = False
        self._active_obj = None


def register():
    bpy.utils.register_class(RAILFLOW_OT_tube)


def unregister():
    bpy.utils.unregister_class(RAILFLOW_OT_tube)
