# mypy: ignore-errors
import bpy
import mathutils  # noqa: F401

from .geometry import conv_value, new, script_add_geometry  # noqa: F401
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
        modifier = next(iter([m for m in obj.modifiers if m.type == "NODES"]), None)
        if not modifier or not modifier.node_group:
            self.report({"WARNING"}, "Add geometry node.")
            return {"CANCELLED"}
        result = script_add_geometry(modifier.node_group)
        if not result:
            self.report({"WARNING"}, "Not DAG with node groups.")
            return {"CANCELLED"}
        bpy.context.window_manager.clipboard = result
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
        if not code.startswith("# ATTRIBUTES = "):
            self.report({"WARNING"}, "Not code.")
            return {"CANCELLED"}
        modifier = next(iter(m for m in obj.modifiers if m.type == "NODES"), None)
        if not modifier:
            modifier = obj.modifiers.new("GeometryNodes", "NODES")
        exec(code)
        return {"FINISHED"}


class CGS_PT_bit(bpy.types.Panel):
    bl_label = "GeometryScript"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Edit"

    def draw(self, context):
        operator(self.layout, CGS_OT_geometry_copy)
        operator(self.layout, CGS_OT_geometry_exec)


# __init__.pyで使用
ui_classes = _get_cls(__name__)
