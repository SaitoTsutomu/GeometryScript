"""
オブジェクト`obj`のジオメトリーノードを作成するには、下記のようにします。
```
node_group = bpy.data.node_groups.new("Geometry Nodes", "GeometryNodeTree")
mod = obj.modifiers.new("GeometryNodes", "NODES")
mod.node_group = node_group
「script_add_geometry(node_group)」の内容をペースト
```
"""
# mypy: ignore-errors
import bpy  # noqa: F401
import mathutils

ATTRIBUTES = {
    "name": str,
    "location": list,
    "label": str,
    "hide": bool,
    "mute": bool,
    "mode": str,
    "data_type": str,
    "domain": str,
    "operation": str,
    "fill_type": str,
}


def new(nodes, bl_idname, inputs=None, **kwargs):
    nd = nodes.new(bl_idname)
    for name, typ in ATTRIBUTES.items():
        value = kwargs.get(name)
        if value and isinstance(value, typ):
            setattr(nd, name, value)
    for name, value in (inputs or {}).items():
        nd.inputs[name].default_value = value


def conv_value(value, dtype=None) -> str:
    if isinstance(value, (mathutils.Vector, mathutils.Euler, mathutils.Color)):
        value = [round(i, 4) for i in value]
    if dtype and isinstance(value, list):
        value = [dtype(i) for i in value]
    elif dtype:
        value = dtype(value)
        if isinstance(value, float):
            value = round(value, 4)
    return value


def script_add_geometry(node_group, var_name="node_group"):
    buf = []
    wr = buf.append
    wr(f"nodes = {var_name}.nodes\n")
    for item in node_group.interface.items_tree:
        nm, io, st = item.name, item.in_out, item.socket_type
        wr(f'{var_name}.interface.new_socket("{nm}", in_out="{io}", socket_type="{st}")\n')
    for node in node_group.nodes:
        wr(f'new(nodes, "{node.bl_idname}", {{')
        for name, it in node.inputs.items():
            if not name:
                break
            if not it.links:
                wr(f'"{name}": {repr(conv_value(it.default_value))}, ')
        wr("}")
        for name in ATTRIBUTES:
            value = getattr(node, name, None)
            if value:
                wr(f", {name}={repr(conv_value(value))}")
        wr(")\n")
    for link in node_group.links:
        fn = link.from_node.name
        fs = link.from_socket.name
        tn = link.to_node.name
        ts = link.to_socket.name
        wr(f'{var_name}.links.new(nodes["{fn}"].outputs["{fs}"], nodes["{tn}"].inputs["{ts}"])\n')
    return "".join(buf)
