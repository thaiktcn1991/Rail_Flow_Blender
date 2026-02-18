import bpy
from ..rf_core import patch_generator

def update_mesh_callback(self, context):
    """Callback to rebuild mesh when settings change"""
    obj = context.active_object
    if obj and obj.select_get() and obj.type == 'MESH':
        # Sync settings to object custom properties
        # This ensures rebuild_mesh uses the new values from UI
        if "u_divisions" in obj: obj["u_divisions"] = self.u_divisions
        if "v_divisions" in obj: obj["v_divisions"] = self.v_divisions
        if "width" in obj: obj["width"] = self.width
        if "radius" in obj: obj["radius"] = self.tube_radius
        if "segments" in obj: obj["segments"] = self.tube_segments
        if "snap_to_surface" in obj: obj["snap_to_surface"] = self.snap_to_surface
        if "adaptive_radius" in obj: obj["adaptive_radius"] = self.adaptive_radius
        
        patch_generator.rebuild_mesh(obj)


def update_xray_callback(self, context):
    """Callback to toggle X-Ray on active object"""
    if context.active_object and context.active_object.type == 'MESH':
        patch_generator.apply_style(context.active_object, self.use_xray)






class RailFlowSettings(bpy.types.PropertyGroup):
    """Rail Flow settings stored in scene"""

    # Source mesh reference
    source_mesh: bpy.props.PointerProperty(
        name="Source Mesh",
        description="Source mesh for retopology",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH'
    )

    # Display settings
    use_xray: bpy.props.BoolProperty(
        name="X-Ray Mode",
        description="Show retopo mesh in front of source",
        default=True,
        update=update_xray_callback
    )

    # Active mode tracking
    active_mode: bpy.props.EnumProperty(
        name="Active Mode",
        description="Currently active drawing mode",
        items=[
            ('NONE', "None", "No mode active"),
            ('POLY_DRAW', "Poly Draw", "Poly Draw mode"),
            ('TUBE', "Tube", "Tube mode"),
        ],
        default='NONE'
    )

    # Stroke settings
    stroke_spacing: bpy.props.FloatProperty(
        name="Stroke Spacing",
        description="Minimum distance between stroke points",
        default=0.01,
        min=0.001, max=1.0,
        step=1,
        precision=3
    )
    stroke_smooth: bpy.props.IntProperty(
        name="Stroke Smooth",
        description="Smoothing iterations for stroke",
        default=0,
        min=0, max=10
    )

    # Division settings
    u_divisions: bpy.props.IntProperty(
        name="U Divisions",
        description="Divisions across width",
        default=4,
        min=1, max=32,
        update=update_mesh_callback
    )
    v_divisions: bpy.props.IntProperty(
        name="V Divisions",
        description="Divisions along length",
        default=8,
        min=2, max=64,
        update=update_mesh_callback
    )

    # Size settings
    width: bpy.props.FloatProperty(
        name="Width",
        description="Patch width",
        default=0.5,
        min=0.01, max=10.0,
        step=10,
        precision=2,
        update=update_mesh_callback
    )

    # Tube settings
    tube_radius: bpy.props.FloatProperty(
        name="Tube Radius",
        description="Radius of tube mesh",
        default=0.1,
        min=0.001, max=10.0,
        step=1,
        precision=3,
        update=update_mesh_callback
    )
    tube_segments: bpy.props.IntProperty(
        name="Tube Segments",
        description="Segments around tube circumference",
        default=8,
        min=3, max=32,
        update=update_mesh_callback
    )

    # Snapping settings
    snap_to_surface: bpy.props.BoolProperty(
        name="Snap to Surface",
        description="Snap vertices to source mesh surface",
        default=True,
        update=update_mesh_callback
    )
    adaptive_radius: bpy.props.BoolProperty(
        name="Adaptive Radius",
        description="Calculate tube radius based on surface thickness",
        default=False,
        update=update_mesh_callback
    )


def register():
    bpy.utils.register_class(RailFlowSettings)
    bpy.types.Scene.railflow_settings = bpy.props.PointerProperty(type=RailFlowSettings)

def unregister():
    del bpy.types.Scene.railflow_settings
    bpy.utils.unregister_class(RailFlowSettings)
