"""
Thompson's construction: turns a regex AST into an NFA (Nondeterministic
Finite Automaton) with epsilon transitions.

Each NFA fragment has exactly one start state and one accept state,
which makes composing fragments (concat, alternation, closure) simple:
this is the classic "Thompson construction" used in early Unix grep/ed
and described in Ken Thompson's 1968 CACM paper.

State representation
---------------------
A State is a simple object with:
    - transitions: dict mapping a "symbol" to a set of target states.
      The symbol is either a literal character, an AnyChar sentinel,
      a CharClass object, or EPSILON for an epsilon move.
    - is_start_anchor / is_end_anchor flags for ^ and $ pseudo-transitions.

We don't do table-based DFA states; instead the matcher below performs an
on-the-fly subset simulation (like `grep`/`egrep` implementations that
avoid the sometimes-exponential blowup of building a full DFA upfront).
"""

from typing import Dict, List, Optional, Set, Union

from .parser import (
    AnyChar, Alt, Char, CharClass, Concat, EndAnchor, Group, Node,
    Plus, Question, StartAnchor, Star,
)

EPSILON = object()   # sentinel for epsilon transitions
ANY = object()        # sentinel meaning "matches any character" edge


class State:
    __slots__ = ("id", "epsilons", "char_edges", "any_edge", "class_edges",
                 "start_anchor", "end_anchor", "accept")

    _counter = 0

    def __init__(self):
        self.id = State._counter
        State._counter += 1
        self.epsilons: List["State"] = []
        self.char_edges: Dict[str, List["State"]] = {}
        self.any_edge: List["State"] = []
        self.class_edges: List[tuple] = []   # (CharClass, target_state)
        self.start_anchor: List["State"] = []  # epsilon-like, only if at pos 0
        self.end_anchor: List["State"] = []    # epsilon-like, only if at end
        self.accept = False

    def __repr__(self):
        return f"State({self.id}{'*' if self.accept else ''})"


class Fragment:
    """An NFA fragment with a single start state and single accept state."""

    __slots__ = ("start", "accept")

    def __init__(self, start: State, accept: State):
        self.start = start
        self.accept = accept


def _frag_for_char(ch: str) -> Fragment:
    s, a = State(), State()
    s.char_edges.setdefault(ch, []).append(a)
    return Fragment(s, a)


def _frag_for_any() -> Fragment:
    s, a = State(), State()
    s.any_edge.append(a)
    return Fragment(s, a)


def _frag_for_class(cc: CharClass) -> Fragment:
    s, a = State(), State()
    s.class_edges.append((cc, a))
    return Fragment(s, a)


def _frag_for_start_anchor() -> Fragment:
    s, a = State(), State()
    s.start_anchor.append(a)
    return Fragment(s, a)


def _frag_for_end_anchor() -> Fragment:
    s, a = State(), State()
    s.end_anchor.append(a)
    return Fragment(s, a)


def _concat(frags: List[Fragment]) -> Fragment:
    if not frags:
        s = State()
        return Fragment(s, s)  # matches empty string
    for a, b in zip(frags, frags[1:]):
        a.accept.epsilons.append(b.start)
    return Fragment(frags[0].start, frags[-1].accept)


def _alternate(frags: List[Fragment]) -> Fragment:
    s, a = State(), State()
    for f in frags:
        s.epsilons.append(f.start)
        f.accept.epsilons.append(a)
    return Fragment(s, a)


def _star(f: Fragment) -> Fragment:
    s, a = State(), State()
    s.epsilons.append(f.start)
    s.epsilons.append(a)
    f.accept.epsilons.append(f.start)
    f.accept.epsilons.append(a)
    return Fragment(s, a)


def _plus(f: Fragment) -> Fragment:
    s, a = State(), State()
    s.epsilons.append(f.start)
    f.accept.epsilons.append(f.start)
    f.accept.epsilons.append(a)
    return Fragment(s, a)


def _question(f: Fragment) -> Fragment:
    s, a = State(), State()
    s.epsilons.append(f.start)
    s.epsilons.append(a)
    f.accept.epsilons.append(a)
    return Fragment(s, a)


def build_nfa(node: Node) -> Fragment:
    """Recursively compile an AST node into an NFA fragment."""
    if isinstance(node, Char):
        return _frag_for_char(node.ch)
    if isinstance(node, AnyChar):
        return _frag_for_any()
    if isinstance(node, CharClass):
        return _frag_for_class(node)
    if isinstance(node, StartAnchor):
        return _frag_for_start_anchor()
    if isinstance(node, EndAnchor):
        return _frag_for_end_anchor()
    if isinstance(node, Group):
        return build_nfa(node.child)
    if isinstance(node, Concat):
        return _concat([build_nfa(p) for p in node.parts])
    if isinstance(node, Alt):
        return _alternate([build_nfa(o) for o in node.options])
    if isinstance(node, Star):
        return _star(build_nfa(node.child))
    if isinstance(node, Plus):
        return _plus(build_nfa(node.child))
    if isinstance(node, Question):
        return _question(build_nfa(node.child))
    raise TypeError(f"unknown AST node: {node!r}")


def compile_to_nfa(node: Node) -> Fragment:
    frag = build_nfa(node)
    frag.accept.accept = True
    return frag
