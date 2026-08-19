"""
Simulates the NFA over an input string using Thompson's algorithm:
at every step we track the *set* of NFA states we could currently be in
(instead of picking one branch and backtracking on failure, like a naive
recursive matcher would). This guarantees O(n*m) matching time (n = text
length, m = number of NFA states) with no catastrophic backtracking,
unlike many backtracking regex engines.

Public API:
    Regex(pattern).fullmatch(s)   -> bool
    Regex(pattern).match(s)       -> Optional[Match]   (anchored at start)
    Regex(pattern).search(s)      -> Optional[Match]   (anywhere in s)
    Regex(pattern).finditer(s)    -> iterator of Match  (all non-overlapping)
"""

from dataclasses import dataclass
from typing import Iterator, List, Optional, Set

from .parser import Parser, CharClass
from .nfa import State, compile_to_nfa, EPSILON


@dataclass
class Match:
    start: int
    end: int
    text: str

    @property
    def group(self) -> str:
        return self.text[self.start:self.end]


def _add_state(state: State, at_start: bool, at_end: bool,
                visited: Set[int], out: List[State]):
    """Epsilon-closure: follow all epsilon/anchor edges reachable from `state`
    without consuming input, collecting the resulting states into `out`."""
    if state.id in visited:
        return
    visited.add(state.id)
    out.append(state)
    for nxt in state.epsilons:
        _add_state(nxt, at_start, at_end, visited, out)
    if at_start:
        for nxt in state.start_anchor:
            _add_state(nxt, at_start, at_end, visited, out)
    if at_end:
        for nxt in state.end_anchor:
            _add_state(nxt, at_start, at_end, visited, out)


def _closure(states: List[State], at_start: bool, at_end: bool) -> List[State]:
    visited: Set[int] = set()
    out: List[State] = []
    for s in states:
        _add_state(s, at_start, at_end, visited, out)
    return out


class Regex:
    def __init__(self, pattern: str):
        self.pattern = pattern
        ast = Parser(pattern).parse()
        self._frag = compile_to_nfa(ast)

    # -- core simulation -----------------------------------------------------

    def _run(self, text: str, start_index: int) -> Optional[int]:
        """
        Try to match starting exactly at `start_index`. Returns the furthest
        end index of a successful match (greedy: the longest match found),
        or None if no match starts here.
        """
        at_start = start_index == 0
        current = _closure([self._frag.start], at_start, start_index == len(text))
        best_end: Optional[int] = None
        if any(s.accept for s in current):
            best_end = start_index

        pos = start_index
        while pos < len(text) and current:
            ch = text[pos]
            nxt_states: List[State] = []
            seen = set()
            for s in current:
                if ch in s.char_edges:
                    for t in s.char_edges[ch]:
                        if t.id not in seen:
                            nxt_states.append(t)
                for t in s.any_edge:
                    if t.id not in seen:
                        nxt_states.append(t)
                for cc, t in s.class_edges:
                    if cc.matches(ch) and t.id not in seen:
                        nxt_states.append(t)
            pos += 1
            at_end = pos == len(text)
            current = _closure(nxt_states, False, at_end)
            if any(s.accept for s in current):
                best_end = pos
        return best_end

    # -- public API ------------------------------------------------------------

    def match(self, text: str) -> Optional[Match]:
        """Match anchored at the start of `text` (like re.match)."""
        end = self._run(text, 0)
        if end is None:
            return None
        return Match(0, end, text)

    def fullmatch(self, text: str) -> bool:
        end = self._run(text, 0)
        return end == len(text)

    def search(self, text: str) -> Optional[Match]:
        """Find the first (leftmost, then longest) match anywhere in `text`."""
        for i in range(len(text) + 1):
            end = self._run(text, i)
            if end is not None:
                return Match(i, end, text)
        return None

    def finditer(self, text: str) -> Iterator[Match]:
        """Find all non-overlapping matches, left to right."""
        i = 0
        n = len(text)
        while i <= n:
            end = self._run(text, i)
            if end is not None:
                yield Match(i, end, text)
                i = end if end > i else i + 1
            else:
                i += 1
