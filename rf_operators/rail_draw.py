"""
Rail Draw Operator for Rail Flow Blender
Modal operator for interactive stroke drawing and mesh generation.

This is the core drawing tool - equivalent to Maya's draggerContext.
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

    # Internal state
    _stroke_points = []
    _is_drawing = False
    _source_obj = None
    _draw_handler = None

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        # Find source mesh (active selected mesh)
        if context.active_object and context.active_object.type == 'MESH':
            self._source_obj = context.active_object
        else:
            self.report({'WARNING'}, "Please select a source mesh first")
            return {'CANCELLED'}

        # Initialize
        self._stroke_points = []
        self._is_drawing = False

        # Add draw handler for stroke preview
        args = (self, context)
        self._draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, 'WINDOW', 'POST_VIEW'
        )

        # Start modal
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set("Rail Draw: LMB to draw, ENTER to confirm, ESC to cancel")

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        context.area.tag_redraw()

        # Mouse move - add points to stroke
        if event.type == 'MOUSEMOVE':
            if self._is_drawing:
                point = self.get_surface_point(context, event)
                if point is not None:
                    # Add point if far enough from last point
                    if len(self._stroke_points) == 0:
                        self._stroke_points.append(point)
                    else:
                        last_point = Vector(self._stroke_points[-1])
                        if (Vector(point) - last_point).length > 0.01:
                            self._stroke_points.append(point)

        # Left mouse - start/continue drawing
        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                self._is_drawing = True
                point = self.get_surface_point(context, event)
                if point is not None:
                    self._stroke_points.append(point)
            elif event.value == 'RELEASE':
                self._is_drawing = False

        # Enter - confirm and generate mesh
        elif event.type in {'RET', 'NUMPAD_ENTER'}:
            if len(self._stroke_points) >= 2:
                self.generate_mesh(context)
            self.cleanup(context)
            return {'FINISHED'}

        # Escape - cancel
        elif event.type == 'ESC':
            self.cleanup(context)
            return {'CANCELLED'}

        # Right click - clear current stroke
        elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            self._stroke_points = []

        return {'RUNNING_MODAL'}

    def get_surface_point(self, context, event):
        """Raycast from mouse position to source mesh surface"""
        if self._source_obj is None:
            return None

        # Get ray from mouse position
        region = context.region
        rv3d = context.region_data
        coord = (event.mouse_region_x, event.mouse_region_y)

        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)

        # Raycast to source mesh
        result = acceleration.raycast_mesh(
            self._source_obj,
            ray_origin,
            ray_direction
        )

        if result is not None:
            location, normal, index, distance = result
            # Transform to world space
            world_location = self._source_obj.matrix_world @ location
            return world_location

        return None

    def generate_mesh(self, context):
        """Generate quad mesh from stroke points"""
        if len(self._stroke_points) < 2:
            return

        obj = patch_generator.generate_quad_patch(
            stroke_points=self._stroke_points,
            u_divisions=self.u_divisions,
            v_divisions=self.v_divisions,
            width=self.width,
            source_obj=self._source_obj if self.snap_to_surface else None,
            snap_to_surface=self.snap_to_surface
        )

        if obj is not None:
            # Select new object
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
            self.report({'INFO'}, f"Created mesh with {len(obj.data.polygons)} faces")

    def draw_callback(self, context):
        """Draw stroke preview in viewport"""
        if len(self._stroke_points) < 2:
            return

        # Draw line strip
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.line_width_set(3.0)
        gpu.state.blend_set('ALPHA')

        coords = [tuple(p) for p in self._stroke_points]
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})

        shader.bind()
        shader.uniform_float("color", (1.0, 0.5, 0.0, 0.8))  # Orange
        batch.draw(shader)

        # Draw points
        gpu.state.point_size_set(8.0)
        batch_points = batch_for_shader(shader, 'POINTS', {"pos": coords})
        shader.uniform_float("color", (1.0, 1.0, 0.0, 1.0))  # Yellow
        batch_points.draw(shader)

        # Reset state
        gpu.state.blend_set('NONE')
        gpu.state.line_width_set(1.0)
        gpu.state.point_size_set(1.0)

    def cleanup(self, context):
        """Clean up handlers and state"""
        if self._draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handler, 'WINDOW')
            self._draw_handler = None

        context.area.header_text_set(None)
        self._stroke_points = []
        self._is_drawing = False


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
    _source_obj = None
    _draw_handler = None

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        if context.active_object and context.active_object.type == 'MESH':
            self._source_obj = context.active_object
        else:
            self.report({'WARNING'}, "Please select a source mesh first")
            return {'CANCELLED'}

        self._stroke_points = []
        self._is_drawing = False

        args = (self, context)
        self._draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback, args, 'WINDOW', 'POST_VIEW'
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

        elif event.type in {'RET', 'NUMPAD_ENTER'}:
            if len(self._stroke_points) >= 2:
                self.generate_mesh(context)
            self.cleanup(context)
            return {'FINISHED'}

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
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
            self.report({'INFO'}, f"Created tube with {len(obj.data.polygons)} faces")

    def draw_callback(self, context):
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

        context.area.header_text_set(None)
        self._stroke_points = []
        self._is_drawing = False


classes = [
    RAILFLOW_OT_draw,
    RAILFLOW_OT_tube,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
