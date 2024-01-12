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
    "color": list,
    "data_type": str,
    "domain": str,
    "fill_type": str,
    "hide": bool,
    "mapping": object,
    "mute": bool,
    "mode": str,
    "operation": str,
    "parent": object,
    "use_custom_color": bool,
    "width": int,
}


def new(nodes, bl_idname, inputs=None, **kwargs):
    nd = nodes.new(bl_idname)
    for name, value in kwargs.items():
        typ = ATTRIBUTES.get(name)
        if value and typ and isinstance(value, typ):
            if name == "mapping":
                crv = nd.mapping.curves[0]
                for _ in value[2:]:
                    crv.points.new(0, 0)
                for pnt, s in zip(crv.points, value):
                    pnt.handle_type, *pnt.location = s
            else:
                setattr(nd, name, value)
    for name, value in (inputs or {}).items():
        nd.inputs[name].default_value = value


def conv_value(name, value, dtype=None):
    if name == "parent":
        return f"nodes['{value.name}']"
    elif name == "mapping":
        return [
            (pnt.handle_type, round(pnt.location.x, 4), round(pnt.location.y, 4))
            for pnt in value.curves[0].points
        ]
    if not dtype and name in {"location", "width"}:
        dtype = int
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
    loc = []
    for node in node_group.nodes:
        input_dc = {}
        for name, it in node.inputs.items():
            if name and not it.is_unavailable and not it.links:
                input_dc[name] = conv_value(name, it.default_value)
        _s = f", {repr(input_dc)}" if input_dc else ""
        wr(f'new(nodes, "{node.bl_idname}"{_s}')
        use_custom_color = getattr(node, "use_custom_color", False)
        for name in ATTRIBUTES:
            if name == "color" and not use_custom_color:
                continue
            value = getattr(node, name, None)
            if name == "location" and isinstance(node, bpy.types.NodeFrame):
                loc.append((node.name, conv_value(name, value)))
                continue
            ignore = not value
            if name == "width" and value == 140:
                ignore = True
            if not ignore:
                out = conv_value(name, value)
                if name != "parent":
                    out = repr(out)
                wr(f", {name}={out}")
        wr(")\n")
    for name, location in loc:
        wr(f'nodes["{name}"].location = {location}\n')
    for link in node_group.links:
        fn, fs = socket_name(link.from_node, link.from_socket, link.from_node.outputs)
        tn, ts = socket_name(link.to_node, link.to_socket, link.to_node.inputs)
        wr(f"{var_name}.links.new(nodes[{fn}].outputs[{fs}], nodes[{tn}].inputs[{ts}])\n")
    return "".join(buf)


def socket_name(node, socket, lst):
    nd_name = repr(node.name)
    for i, sct in enumerate(lst):
        if sct.identifier == socket.identifier:
            break
    return nd_name, i
