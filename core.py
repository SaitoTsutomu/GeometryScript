import bpy

from .geometry import conv_value, new, script_add_geometry
from .register_class import _get_cls, operator


class CGS_OT_geometry_copy(bpy.types.Operator):
    """Copy nodes"""

    bl_idname = "object.geometry_copy"
    bl_label = "Copy"
    bl_description = "Copy script of geometry nodes."

    def execute(self, context):
        if not (obj := bpy.context.object):
            self.report({"WARNING"}, "Select object.")
            return {"CANCELLED"}
        modifiers = next(iter([m for m in obj.modifiers if m.type == "NODES"]), None)
        if not modifiers or not modifiers.node_group:
            self.report({"WARNING"}, "Add geometry node.")
            return {"CANCELLED"}
        bpy.context.window_manager.clipboard = script_add_geometry(modifiers.node_group)
        self.report({"INFO"}, "Copied to clipboard.")
        return {"FINISHED"}


class CGS_OT_geometry_exec(bpy.types.Operator):
    """Execute script"""

    bl_idname = "object.geometry_exec"
    bl_label = "Exec"
    bl_description = "Execute script."

    def execute(self, context):
        if not (obj := bpy.context.object):
            self.report({"WARNING"}, "Select object.")
            return {"CANCELLED"}
        code = str(bpy.context.window_manager.clipboard)
        if not code.startswith("nodes = "):
            self.report({"WARNING"}, "Not code.")
            return {"CANCELLED"}
        modifiers = next(iter([m for m in obj.modifiers if m.type == "NODES"]), None)
        if not modifiers:
            modifiers = bpy.context.object.modifiers.new("GeometryNodes", "NODES")
        if not modifiers.node_group:
            modifiers.node_group = bpy.data.node_groups.new("Geometry Nodes", "GeometryNodeTree")
        exec(code)
        ops_func(bpy.ops.node.view_all, "NODE_EDITOR")
        return {"FINISHED"}


class CGS_PT_bit(bpy.types.Panel):
    bl_label = "GeometryScript"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Edit"

    def draw(self, context):
        operator(self.layout, CGS_OT_geometry_copy)
        operator(self.layout, CGS_OT_geometry_exec)


def ops_func(func, area_type, region_type="WINDOW"):
    for area in bpy.context.screen.areas:
        if area.type == area_type:
            for region in area.regions:
                if region.type == region_type:
                    ctx = bpy.context.copy()
                    ctx["area"] = area
                    ctx["region"] = region
                    try:
                        func(ctx)
                    except RuntimeError:
                        pass
                    return


# __init__.pyで使用
ui_classes = _get_cls(__name__)
