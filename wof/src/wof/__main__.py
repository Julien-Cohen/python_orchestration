"""Command-line entry point.

Usage:
    python -m wof FILE.wof            # print the AST as JSON
    python -m wof FILE.wof --tree     # print the raw Lark parse tree instead
    python -m wof FILE.wof -o out.json
"""
import argparse
import sys
from pathlib import Path

from lark import Lark
from lark.exceptions import UnexpectedInput, VisitError

from .transformer import ToAst

GRAMMAR_PATH = Path(__file__).with_name("wof.lark")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m wof",
        description="Parse a .wof workflow file and print its AST as JSON.",
    )
    ap.add_argument("file", type=Path, help="path to the .wof file")
    ap.add_argument("--tree", action="store_true",
                    help="print the raw Lark parse tree instead of the AST")
    ap.add_argument("-o", "--output", type=Path,
                    help="write the result to this file instead of stdout")
    args = ap.parse_args(argv)

    try:
        text = args.file.read_text(encoding="utf-8")
    except OSError as e:
        print(f"error: cannot read {args.file}: {e}", file=sys.stderr)
        return 2

    parser = Lark(GRAMMAR_PATH.read_text(encoding="utf-8"),
                  start="workflow", parser="lalr")

    # 1. Syntax: text -> parse tree
    try:
        tree = parser.parse(text)
    except UnexpectedInput as e:
        where = f"{e.line}:{e.column}" if getattr(e, "line", -1) != -1 else "end of file"
        print(f"{args.file}:{where}: syntax error", file=sys.stderr)
        if getattr(e, "line", -1) != -1:
            print(e.get_context(text), file=sys.stderr)
        return 1

    # 2. Structure: parse tree -> validated Pydantic AST
    if args.tree:
        result = tree.pretty()
    else:
        try:
            wf = ToAst().transform(tree)
        except VisitError as e:
            print(f"{args.file}: invalid workflow: {e.orig_exc}", file=sys.stderr)
            return 1
        result = wf.model_dump_json(indent=2)

    if args.output:
        args.output.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())