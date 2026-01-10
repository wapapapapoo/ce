import logging
import sys
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

    dump_value_graph(vg)
    

if __name__ == "__main__":
    # try:
    run()
    # except Exception as e:
    #     logging.info('Compiler Fail.')