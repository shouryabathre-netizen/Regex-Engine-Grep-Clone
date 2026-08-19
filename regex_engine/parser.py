r"""
Recursive-descent parser for a regex dialect supporting:

    literals        a b c ...
    concatenation   ab
    alternation     a|b
    grouping        (ab)
    star            a*
    plus            a+
    optional        a?
    any char        .
    char class      [abc] [^abc] [a-z] [a-zA-Z0-9_]
    escapes         \d \D \w \W \s \S \. \* \+ \? \( \) \[ \] \| \\
    anchors         ^ (start of line)  $ (end of line)

Grammar (roughly, lowest to highest precedence):

    expr    := alt
    alt     := concat ('|' concat)*
    concat  := repeat*
    repeat  := atom ('*' | '+' | '?')?
    atom    := char | '.' | class | '(' expr ')' | anchor
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


class RegexSyntaxError(Exception):
    pass


# ---------------------------------------------------------------------------
# AST node types
# ---------------------------------------------------------------------------

class Node:
    pass


@dataclass
class Char(Node):
    ch: str


@dataclass
class AnyChar(Node):
    pass


@dataclass
class CharClass(Node):
    ranges: List[Tuple[str, str]]   # list of (lo, hi) inclusive char ranges
    negate: bool = False

    def matches(self, ch: str) -> bool:
        inside = any(lo <= ch <= hi for lo, hi in self.ranges)
        return (not inside) if self.negate else inside


@dataclass
class StartAnchor(Node):
    pass


@dataclass
class EndAnchor(Node):
    pass


@dataclass
class Concat(Node):
    parts: List[Node]


@dataclass
class Alt(Node):
    options: List[Node]


@dataclass
class Star(Node):
    child: Node


@dataclass
class Plus(Node):
    child: Node


@dataclass
class Question(Node):
    child: Node


@dataclass
class Group(Node):
    child: Node


# ---------------------------------------------------------------------------
# Predefined shorthand character classes
# ---------------------------------------------------------------------------

_DIGIT = [("0", "9")]
_WORD = [("a", "z"), ("A", "Z"), ("0", "9"), ("_", "_")]
_SPACE = [(" ", " "), ("\t", "\t"), ("\n", "\n"), ("\r", "\r"), ("\f", "\f"), ("\v", "\v")]

_SHORTHAND = {
    "d": (_DIGIT, False),
    "D": (_DIGIT, True),
    "w": (_WORD, False),
    "W": (_WORD, True),
    "s": (_SPACE, False),
    "S": (_SPACE, True),
}

_METACHARS = set(".*+?()[]|\\^$")


class Parser:
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.pos = 0
        self.n = len(pattern)

    # -- helpers -----------------------------------------------------------

    def _peek(self) -> Optional[str]:
        return self.pattern[self.pos] if self.pos < self.n else None

    def _advance(self) -> str:
        ch = self.pattern[self.pos]
        self.pos += 1
        return ch

    def _expect(self, ch: str):
        if self._peek() != ch:
            raise RegexSyntaxError(
                f"expected '{ch}' at position {self.pos} in pattern {self.pattern!r}"
            )
        self._advance()

    # -- entry point ---------------------------------------------------------

    def parse(self) -> Node:
        node = self._parse_alt()
        if self.pos != self.n:
            raise RegexSyntaxError(
                f"unexpected '{self._peek()}' at position {self.pos} in pattern {self.pattern!r}"
            )
        return node

    # -- grammar rules -------------------------------------------------------

    def _parse_alt(self) -> Node:
        options = [self._parse_concat()]
        while self._peek() == "|":
            self._advance()
            options.append(self._parse_concat())
        if len(options) == 1:
            return options[0]
        return Alt(options)

    def _parse_concat(self) -> Node:
        parts = []
        while self._peek() is not None and self._peek() not in ("|", ")"):
            parts.append(self._parse_repeat())
        if len(parts) == 1:
            return parts[0]
        return Concat(parts)

    def _parse_repeat(self) -> Node:
        atom = self._parse_atom()
        while self._peek() in ("*", "+", "?"):
            op = self._advance()
            if op == "*":
                atom = Star(atom)
            elif op == "+":
                atom = Plus(atom)
            else:
                atom = Question(atom)
        return atom

    def _parse_atom(self) -> Node:
        ch = self._peek()
        if ch is None:
            raise RegexSyntaxError("unexpected end of pattern")

        if ch == "(":
            self._advance()
            inner = self._parse_alt()
            self._expect(")")
            return Group(inner)

        if ch == ".":
            self._advance()
            return AnyChar()

        if ch == "^":
            self._advance()
            return StartAnchor()

        if ch == "$":
            self._advance()
            return EndAnchor()

        if ch == "[":
            return self._parse_class()

        if ch == "\\":
            self._advance()
            esc = self._peek()
            if esc is None:
                raise RegexSyntaxError("dangling escape at end of pattern")
            self._advance()
            if esc in _SHORTHAND:
                ranges, negate = _SHORTHAND[esc]
                return CharClass(list(ranges), negate)
            # \n, \t, \r escapes
            special = {"n": "\n", "t": "\t", "r": "\r"}
            return Char(special.get(esc, esc))

        if ch in (")", "|"):
            raise RegexSyntaxError(f"unexpected '{ch}' at position {self.pos}")

        self._advance()
        return Char(ch)

    def _parse_class(self) -> Node:
        self._expect("[")
        negate = False
        if self._peek() == "^":
            negate = True
            self._advance()

        ranges: List[Tuple[str, str]] = []
        first = True
        while True:
            ch = self._peek()
            if ch is None:
                raise RegexSyntaxError("unterminated character class")
            if ch == "]" and not first:
                break
            first = False

            lo = self._read_class_char()
            if isinstance(lo, list):  # shorthand like \d inside a class
                ranges.extend(lo)
                continue

            if self._peek() == "-" and self.pos + 1 < self.n and self.pattern[self.pos + 1] != "]":
                self._advance()  # consume '-'
                hi = self._read_class_char()
                if isinstance(hi, list):
                    raise RegexSyntaxError("invalid range in character class")
                ranges.append((lo, hi))
            else:
                ranges.append((lo, lo))

        self._expect("]")
        return CharClass(ranges, negate)

    def _read_class_char(self):
        ch = self._advance()
        if ch == "\\":
            esc = self._peek()
            if esc is None:
                raise RegexSyntaxError("dangling escape in character class")
            self._advance()
            if esc in _SHORTHAND:
                r, neg = _SHORTHAND[esc]
                if neg:
                    raise RegexSyntaxError("negated shorthand not allowed inside class range")
                return list(r)
            special = {"n": "\n", "t": "\t", "r": "\r"}
            return special.get(esc, esc)
        return ch
