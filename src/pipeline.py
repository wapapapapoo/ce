import logging
import sys
from snapshot_closure_convert import closure_convert
from src_to_cst import build_cst, cst_dict_to_xml, parse_cst_to_dict
from cst_to_ast import build_ast, dump_ast
from ast_to_bdg import build_bdg
from bdg_to_vg import build_value_graph, dump_value_graph

import xml.etree.ElementTree as ET
import argparse
import json


def run():
    parser = argparse.ArgumentParser(description="YAFL Compiler - Yet Another Functional Language")
    parser.add_argument(
        "source",
        help="Source file path, or '-' to read from stdin"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)",
        default=None
    )

    args = parser.parse_args()

    if args.source == "-":
        src = sys.stdin.read()
    else:
        with open(args.source, "r", encoding="utf-8") as f:
            src = f.read()

    cst = build_cst(src)

    # print(cst)

    ast = build_ast(cst)

    # if args.output:
    #     import sys
    #     from contextlib import redirect_stdout
    #     with open(args.output, "w", encoding="utf-8") as f:
    #         with redirect_stdout(f):
    #             dump_ast(ast)
    # else:
    #     dump_ast(ast)

    bdg, block_index, point_index, bindphi_index = build_bdg(ast)

    # for item in bindphi_index:
    #     print(item.entry.name, end=' ')
    #     # print(item.entry, ': ')
    #     print(f"at {item.entry.getCstPointer()['line']} {item.entry.getCstPointer()['column']}", ': ')
    #     for k in item.candidates:
    #         print('  ', k, ': ')
    #         for i in item.candidates[k]:
    #             # print('    ', i.identifier.getCstPointer())
    #             print('    ', i.name, f"at {i.identifier.getCstPointer()['line']} {i.identifier.getCstPointer()['column']}" if i.identifier.point.define_depth != -1 else '<builtin>', ', ')
    #         print('; ', end='')
    #     print('')

    vg = build_value_graph(bdg, block_index, point_index, bindphi_index)
    # dump_value_graph(vg)

    from snapshot_resolve_phi import resolve_all_phis
    resolve_all_phis(vg)
    closure_convert(vg)
    # dump_value_graph(vg)

    from vg_effects import apply_effects
    effect = apply_effects(vg, block_index)

    def dump_edge(e):
        print(
            f"E{e.id} "
            f"effect={getattr(e, '_is_effect', None)} "
            f"idx={getattr(e, '_effect_index', None)} "
            f"ast={type(e.ast).__name__}"
            f"{e.ast.getCstPointer().get('start', '<rule>') if e.ast.getCstPointer() is not None else '<none>'}"
            f"placeholder={e.transform.placeholder if e.kind == 'call' else ''}"
        )
    for edge in vg.edges:
        dump_edge(edge)




if __name__ == "__main__":
    # try:
    run()
    # except Exception as e:
    #     logging.info('Compiler Fail.')