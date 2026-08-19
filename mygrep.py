#!/usr/bin/env python3
"""
mygrep.py — a small `grep` clone powered entirely by our from-scratch
regex_engine (parser -> Thompson NFA -> NFA simulation), no `re` module.

Usage:
    mygrep.py [options] PATTERN [FILE ...]

Options:
    -i, --ignore-case     case-insensitive matching
    -n, --line-number     prefix each match with its line number
    -v, --invert-match    print lines that do NOT match
    -c, --count           print only a count of matching lines per file
    -r, --recursive       recursively search directories
    -l, --files-with-matches   print only names of files with matches
    -o, --only-matching    print only the matched part of each line
    --color[=WHEN]         highlight matches (always|never|auto), default auto

If no FILE is given, reads from stdin.
"""

import argparse
import os
import sys

from regex_engine import Regex, RegexSyntaxError

RED = "\033[91m"
RESET = "\033[0m"


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mygrep.py",
        description="grep-alike backed by a hand-built regex engine (NFA based).",
    )
    p.add_argument("pattern", help="regex pattern to search for")
    p.add_argument("files", nargs="*", help="files to search (default: stdin)")
    p.add_argument("-i", "--ignore-case", action="store_true")
    p.add_argument("-n", "--line-number", action="store_true")
    p.add_argument("-v", "--invert-match", action="store_true")
    p.add_argument("-c", "--count", action="store_true")
    p.add_argument("-r", "--recursive", action="store_true")
    p.add_argument("-l", "--files-with-matches", action="store_true")
    p.add_argument("-o", "--only-matching", action="store_true")
    p.add_argument("--color", nargs="?", const="always", default="auto",
                    choices=["always", "never", "auto"])
    return p


def iter_files(paths, recursive):
    for path in paths:
        if os.path.isdir(path):
            if not recursive:
                print(f"mygrep.py: {path}: Is a directory", file=sys.stderr)
                continue
            for root, _, files in os.walk(path):
                for f in files:
                    yield os.path.join(root, f)
        else:
            yield path


def colorize(line: str, spans, use_color: bool) -> str:
    if not use_color or not spans:
        return line
    out = []
    last = 0
    for s, e in spans:
        out.append(line[last:s])
        out.append(RED + line[s:e] + RESET)
        last = e
    out.append(line[last:])
    return "".join(out)


def search_lines(regex: Regex, lines, ignore_case: bool):
    """Yield (line_no, line_text, matched_bool, spans) for each line."""
    for i, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n")
        haystack = line.lower() if ignore_case else line
        spans = [(m.start, m.end) for m in regex.finditer(haystack)]
        yield i, line, bool(spans), spans


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)

    pattern = args.pattern.lower() if args.ignore_case else args.pattern
    try:
        regex = Regex(pattern)
    except RegexSyntaxError as e:
        print(f"mygrep.py: bad pattern: {e}", file=sys.stderr)
        return 2

    targets = list(iter_files(args.files, args.recursive)) if args.files else [None]
    multi_file = len(targets) > 1
    use_color = (args.color == "always") or (args.color == "auto" and sys.stdout.isatty())

    exit_status = 1  # 1 = no matches found anywhere (grep convention), 0 if found
    for target in targets:
        try:
            if target is None:
                fh = sys.stdin
                label = "(standard input)"
                lines = fh.readlines()
            else:
                label = target
                with open(target, "r", errors="replace") as fh:
                    lines = fh.readlines()
        except OSError as e:
            print(f"mygrep.py: {target}: {e.strerror}", file=sys.stderr)
            continue

        match_count = 0
        file_had_match = False

        for lineno, line, matched, spans in search_lines(regex, lines, args.ignore_case):
            show = matched != args.invert_match  # invert flips which lines "count"
            if not show:
                continue

            match_count += 1
            file_had_match = True
            exit_status = 0

            if args.files_with_matches or args.count:
                continue  # defer printing

            prefix = ""
            if multi_file:
                prefix += f"{label}:"
            if args.line_number:
                prefix += f"{lineno}:"

            if args.only_matching and not args.invert_match:
                for s, e in spans:
                    piece = line[s:e]
                    print(f"{prefix}{RED + piece + RESET if use_color else piece}")
            else:
                print(prefix + colorize(line, spans if not args.invert_match else [], use_color))

        if args.files_with_matches:
            if file_had_match:
                print(label)
        elif args.count:
            prefix = f"{label}:" if multi_file else ""
            print(f"{prefix}{match_count}")

    return exit_status


if __name__ == "__main__":
    sys.exit(main())
