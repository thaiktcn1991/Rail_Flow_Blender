import bpy
from ..rf_core import patch_generator

# Map Active Mode to Mesh Type for smart updates
MODE_TO_TYPE_MAP = {
    'POLY_DRAW': ['SINGLE_RAIL', 'POLY_MULTI'],
    'TUBE': ['TUBE'],
    'POLYGON': ['POLYGON'],
    'VBRIDGE': ['BRIDGE', 'BRIDGE_CHAIN'],
    'QUADDRAW': ['QUADDRAW'],
}

def update_mesh_callback(self, context):
    """
    Callback to rebuild mesh when settings change.
    Only allows update if the active object's type matches the active mode.
    """
    obj = context.active_object
    if not (obj and obj.select_get() and obj.type == 'MESH' and "type" in obj):
        return

    # DECOUPLING LOGIC: Only update if active mode matches object's creation mode
    obj_type = obj.get("type")
    active_mode = self.active_mode
    
    should_update = False
    if active_mode == 'NONE':
        # DISCONNECT: When no mode is active, sliders do nothing to protected meshes
        should_update = False
    elif active_mode in MODE_TO_TYPE_MAP:
        allowed_types = MODE_TO_TYPE_MAP[active_mode]
        if isinstance(allowed_types, list):
            if obj_type in allowed_types:
                should_update = True
        elif obj_type == allowed_types:
            should_update = True
            
    if should_update:
        # Force sync settings to object custom properties
        obj["u_divisions"] = self.u_divisions
        obj["v_divisions"] = self.v_divisions
        obj["width"] = self.width
        obj["radius"] = self.tube_radius
        obj["segments"] = self.tube_segments
        obj["snap_to_surface"] = self.snap_to_surface
        obj["adaptive_radius"] = self.adaptive_radius
        
        patch_generator.rebuild_mesh(obj)


def update_xray_callback(self, context):
    """Callback to toggle X-Ray on active object"""
    if context.active_object and context.active_object.type == 'MESH':
        patch_generator.apply_style(context.active_object, self.use_xray)


def update_wire_thickness_callback(self, context):
    """Callback to update wire thickness on all Rail Flow meshes"""
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and "type" in obj:
            # Check if it's a Rail Flow mesh
            mod = obj.modifiers.get("RailFlow_ThickWire")
            if mod:
                mod.thickness = self.wire_thickness






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
    wire_thickness: bpy.props.FloatProperty(
        name="Wire Thickness",
        description="Thickness of wireframe lines (in Blender units)",
        default=0.008,
        min=0.001, max=0.05,
        step=1,
        precision=3,
        update=update_wire_thickness_callback
    )
    show_hotkey_on_button: bpy.props.BoolProperty(
        name="Show Hotkey on Button",
        default=True
    )
    enable_hotkey: bpy.props.BoolProperty(
        name="Enable Hotkey",
        default=True
    )

    # Symmetry settings
    symmetry_x: bpy.props.BoolProperty(name="X", default=False)
    symmetry_y: bpy.props.BoolProperty(name="Y", default=False)
    symmetry_z: bpy.props.BoolProperty(name="Z", default=False)

    # Active mode tracking
    active_mode: bpy.props.EnumProperty(
        name="Active Mode",
        description="Currently active drawing mode",
        items=[
            ('NONE', "None", "No mode active"),
            ('POLY_DRAW', "Poly Draw", "Poly Draw mode"),
            ('TUBE', "Tube", "Tube mode"),
            ('ECOLLAPSE', "Ecollapse", "Edge Collapse mode"),
            ('POLYGON', "Polygon", "Polygon mode"),
            ('VBRIDGE', "Vertex Bridge", "Vertex Bridge mode"),
            ('QUADDRAW', "Quaddraw", "Quaddraw mode"),
            ('FILL_HOLE', "Fill Hole", "Fill Hole mode"),
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
    angle_threshold: bpy.props.FloatProperty(
        name="Angle Threshold",
        description="Angle threshold for adaptive sampling",
        default=15.0,
        min=0.1, max=90.0,
        precision=1
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
    adaptive_blend: bpy.props.FloatProperty(
        name="Adaptive Blend",
        description="Blending factor for adaptive sampling",
        default=0.0,
        min=0.0, max=1.0,
        precision=2
    )

    # Vertex Bridge settings
    bridge_connection_mode: bpy.props.EnumProperty(
        name="Connection Mode",
        items=[
            ('AUTO', 'Auto Connect (Geometric)', 'Geometric connection'),
            ('EQUAL', 'Equal Strip (Topological)', 'Topological connection'),
            ('OFF', 'Off', 'Manual connection')
        ],
        default='AUTO',
        description="How to connect selected vertices to the stroke"
    )
    bridge_poly_along_stroke: bpy.props.BoolProperty(
        name="Poly Along Stroke",
        description="Generate poly strip along the drawn stroke",
        default=False
    )

    # Hidden properties for Bridge logic
    bridge_vertex_indices: bpy.props.StringProperty(default="")
    bridge_object_name: bpy.props.StringProperty(default="")


def register():
    bpy.utils.register_class(RailFlowSettings)
    bpy.types.Scene.railflow_settings = bpy.props.PointerProperty(type=RailFlowSettings)

def unregister():
    del bpy.types.Scene.railflow_settings
    bpy.utils.unregister_class(RailFlowSettings)
