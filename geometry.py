"""
単独で、オブジェクトとそのジオメトリーノードを作成するには、下記のようにします。
- 下記のここからここまでをペースト
- オブジェクトを作成または参照
- `modifier = bpy.context.object.modifiers.new("GeometryNodes", "NODES")`
- アドオンのコピーの内容をペースト
"""

from collections import defaultdict
from typing import Iterable

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

# ----ここから
import bpy  # noqa: E402


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


# ----ここまで


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


def topological_sort(
    original_node_groups: Iterable[bpy.types.NodeTree],
) -> list[bpy.types.GeometryNodeGroup] | None:
    """Node Groupの参照先が先になるようにソート"""
    node_groups: list[bpy.types.GeometryNodeGroup] = []
    node_trees: set[bpy.types.NodeTree] = set()
    refs = defaultdict(set)
    for node_tree in original_node_groups:
        node_trees.add(node_tree)
        for node in node_tree.nodes:
            if node.bl_idname == "GeometryNodeGroup" and node.node_tree:
                refs[node.node_tree].add(node_tree)
    while node_trees:
        node_tree = next(iter(nt for nt in node_trees if not refs.get(nt)), None)
        if not node_tree:
            return None
        node_groups.append(node_tree)
        node_trees.remove(node_tree)
        for ref in refs.values():
            if node_tree in ref:
                ref.remove(node_tree)
    return list(reversed(node_groups))


def script_add_geometry(target_node_tree):
    node_groups = topological_sort(bpy.data.node_groups)
    if node_groups is None:
        return ""
    buf = []
    wr = buf.append
    wr(
        "node_groups = bpy.data.node_groups\n"
        "for node_tree in list(node_groups):\n"
        "    node_groups.remove(node_tree)\n\n"
    )
    used_kwargs = set()
    for node_tree in node_groups:
        wr(f'node_tree = node_groups.new("{node_tree.name}", "GeometryNodeTree")\n')
        wr("nodes = node_tree.nodes\n")
        for item in node_tree.interface.items_tree:
            nm, io, st = item.name, item.in_out, item.socket_type
            wr(f'node_tree.interface.new_socket("{nm}", in_out="{io}", socket_type="{st}")\n')
        frame_locations = []
        for node in node_tree.nodes:
            input_dc = {}
            s1 = f'new(nodes, "{node.bl_idname}"'
            for i, (name, it) in enumerate(node.inputs.items()):
                if name and not it.is_unavailable and not it.links:
                    value = getattr(it, "default_value", None)
                    input_dc[i] = conv_value(name, value)
            s2 = f", {repr(input_dc)}" if input_dc else ""
            use_custom_color = getattr(node, "use_custom_color", False)
            kwargs_dc = {}
            for name in ATTRIBUTES:
                if name == "color" and not use_custom_color:
                    continue
                value = getattr(node, name, None)
                if name == "location" and isinstance(node, bpy.types.NodeFrame):
                    frame_locations.append((node.name, conv_value(name, value)))
                    continue
                ignore = not value
                if name == "width" and value == 140:
                    ignore = True
                if not ignore:
                    out = conv_value(name, value)
                    if name != "parent":
                        out = repr(out)
                    kwargs_dc[name] = out
                    used_kwargs.add(name)
            _s = ", ".join(f"{k}={v}" for k, v in kwargs_dc.items())
            s3 = (f", {_s}" if _s else "") + ")"
            ls1, ls2, ls3 = len(s1), len(s2), len(s3)
            if ls1 + ls2 + ls3 <= 100:
                wr(f"{s1}{s2}{s3}\n")
            elif ls2 >= ls3 and ls1 + ls3 + 8 <= 100:
                wr(f"inputs = {s2[2:]}\n")
                wr(f"{s1}, inputs{s3}\n")
            elif ls2 <= ls3 and ls1 + ls2 + 10 <= 100:
                wr(f"kwargs = dict({s3[2:]}\n")
                wr(f"{s1}{s2}, **kwargs)\n")
            else:
                wr(f"inputs = {s2[2:]}\n")
                wr(f"kwargs = dict({s3[2:]}\n")
                wr(f"{s1}, inputs, **kwargs)\n")
            if node.bl_idname == "GeometryNodeGroup" and node.node_tree:
                wr(f'nodes["{node.name}"].node_tree = node_groups["{node.node_tree.name}"]\n')
        for name, location in frame_locations:
            wr(f'nodes["{name}"].location = {location}\n')
        for link in node_tree.links:
            fn, fs = socket_name(link.from_node, link.from_socket, link.from_node.outputs)
            tn, ts = socket_name(link.to_node, link.to_socket, link.to_node.inputs)
            wr(f"node_tree.links.new(nodes[{fn}].outputs[{fs}], nodes[{tn}].inputs[{ts}])\n")
        wr("\n")
    wr(f'modifier.node_group = node_groups["{target_node_tree.name}"]\n')
    s = ", ".join(f'"{k}": {ATTRIBUTES[k].__name__}' for k in used_kwargs)
    buf.insert(0, f"ATTRIBUTES = {{{s}}}\n\n")
    return "".join(buf)


def socket_name(node, socket, lst):
    nd_name = repr(node.name)
    for i, sct in enumerate(lst):
        if sct.identifier == socket.identifier:
            break
    return nd_name, i
