"""Command line: python -m wof FILE [--strict] [--tokens] [--loc]"""

import argparse
import json
import sys

from .errors import WofError
from .lexer import tokenize
from .parser import parse_with_warnings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m wof", description="Parse a workflow file and print its AST as JSON.")
    ap.add_argument("file")
    ap.add_argument("--strict", action="store_true", help="treat tolerated syntax slips as errors")
    ap.add_argument("--tokens", action="store_true", help="print the token stream instead of the AST")
    ap.add_argument("--loc", action="store_true", help="include source locations in the JSON")
    args = ap.parse_args(argv)

    with open(args.file, encoding="utf-8") as f:
        source = f.read()

    try:
        if args.tokens:
            for tok in tokenize(source):
                print(f"{tok.loc!s:>8}  {tok.kind:<6} {tok.text!r}")
            return 0
        workflow, warnings = parse_with_warnings(source, strict=args.strict)
    except WofError as exc:
        print(f"error: {args.file}:{exc}", file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"{args.file}:{warning}", file=sys.stderr)
    print(json.dumps(workflow.to_dict(include_loc=args.loc), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
