from typing import List, Optional
from ast_types import Point, BlockInfo, BindPhi, Program


# =========================
# Graphviz DOT 生成
# =========================

def build_point_dependency_dot(
    ast: Program,
    block_index: List[BlockInfo],
    point_index: List[Point],
    bindphi_index: List[BindPhi],
) -> str:
    """
    生成 Graphviz DOT，用于可视化 Point 依赖关系
    - def 节点：Point
    - use 节点：BindPhi.entry（虚拟）
    - 边：def -> use
    - 边权重：bindphi depth
    """

    lines: List[str] = []
    lines.append("digraph PointDependencyGraph {")
    lines.append("  rankdir=LR;")
    lines.append("  node [shape=box, fontname=monospace];")
    lines.append("  edge [fontname=monospace];")

    # -------------------------
    # def nodes (Point)
    # -------------------------
    for p in point_index:
        block_id = p.block.id if p.block else "None"
        label = (
            f"Point#{p.id}\\n"
            f"name: {p.name}\\n"
            f"block: {block_id}\\n"
            f"define_depth: {p.define_depth}"
        )

        lines.append(
            f'  p{p.id} [label="{label}"];'
        )

    # -------------------------
    # use nodes + edges
    # -------------------------
    for bp in bindphi_index:
        ident = bp.entry

        # 每个 use 一个独立节点
        use_node_id = f"use_{bp.id}"
        use_label = f"use {bp.name}\\nBindPhi#{bp.id}"

        lines.append(
            f'  {use_node_id} [shape=ellipse, label="{use_label}"];'
        )

        for depth, defs in bp.candidates.items():
            for def_point in defs:
                lines.append(
                    f"  p{def_point.id} -> {use_node_id} "
                    f'[label="depth={depth}"];'
                )

    lines.append("}")
    return "\n".join(lines)


# =========================
# 便捷调试入口
# =========================

def dump_point_dependency_graph(
    ast: Program,
    block_index: List[BlockInfo],
    point_index: List[Point],
    bindphi_index: List[BindPhi],
):
    dot = build_point_dependency_dot(
        ast,
        block_index,
        point_index,
        bindphi_index,
    )
    print(dot)
