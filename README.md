# regex-engine

A regular-expression engine built from scratch in Python — parser →
Thompson NFA construction → NFA simulation — plus `mygrep.py`, a
`grep`-style command-line tool built on top of it.

No use of Python's built-in `re` module anywhere in the engine.

## Why

This is a learning project that reimplements, at a small scale, how
tools like `grep`, `ed`, and regex libraries have worked since Ken
Thompson's 1968 paper *"Regular Expression Search Algorithm"*. Building
it touches:

- **Parsing** — recursive-descent parsing of a regex grammar into an AST
- **Finite automata** — Thompson's construction, turning an AST into an
  NFA with epsilon transitions
- **Pattern matching** — simulating the NFA over input by tracking a
  *set* of active states at each step (instead of backtracking), which
  guarantees linear-ish time matching with no catastrophic backtracking
- **CLI tool design** — turning the engine into a practical `grep` clone

## Supported syntax

| Syntax        | Meaning                                   |
|---------------|--------------------------------------------|
| `a`, `b`, `c` | literal characters                        |
| `.`           | any character                             |
| `*`           | zero or more (greedy)                     |
| `+`           | one or more (greedy)                      |
| `?`           | zero or one                               |
| `\|`          | alternation                               |
| `(...)`       | grouping                                  |
| `[abc]`       | character class                           |
| `[^abc]`      | negated character class                   |
| `[a-z]`       | character range                           |
| `\d \w \s`    | digit / word / whitespace shorthand       |
| `\D \W \S`    | negated shorthand                         |
| `^` `$`       | start / end of string anchors             |
| `\.` `\*` ... | escaped metacharacters                    |

## Architecture

```
regex_engine/
  parser.py    # tokenizes/parses a pattern string into an AST
  nfa.py       # Thompson's construction: AST -> NFA (states + epsilon edges)
  matcher.py   # simulates the NFA over text; Regex/Match public API
mygrep.py      # CLI grep clone built on regex_engine
tests/
  test_regex_engine.py
```

The matcher never backtracks. At every input position it keeps the
*set* of NFA states reachable so far (computing the epsilon-closure
after each character), the same approach classic Unix `grep`/`egrep`
use to avoid exponential blowups on patterns like `(a*)*b` that trip up
naive backtracking engines.

## Usage as a library

```python
from regex_engine import Regex

r = Regex(r"[a-zA-Z0-9._]+@[a-zA-Z0-9]+\.[a-zA-Z]+")
r.fullmatch("user@example.com")     # True
r.search("contact: user@example.com!")   # Match(start=9, end=25, ...)
list(r.finditer("a@b.com and c@d.org"))  # both matches
```

## Usage as a CLI (`mygrep.py`)

```bash
# basic search
python3 mygrep.py "fox" sample.txt

# case-insensitive, with line numbers
python3 mygrep.py -in "error|warning" sample.txt

# only print the matched text (like grep -o)
python3 mygrep.py -o '[a-zA-Z0-9._]+@[a-zA-Z0-9]+\.[a-zA-Z]+' sample.txt

# invert match
python3 mygrep.py -v '[0-9]' sample.txt

# recursive directory search, count matches per file
python3 mygrep.py -rc "TODO" src/

# read from stdin
cat sample.txt | python3 mygrep.py "o+"
```

Flags: `-i/--ignore-case`, `-n/--line-number`, `-v/--invert-match`,
`-c/--count`, `-r/--recursive`, `-l/--files-with-matches`,
`-o/--only-matching`, `--color[=always|never|auto]`.

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```

23 tests covering literals, quantifiers, character classes,
alternation, groups, anchors, greedy matching, `finditer`, and syntax
error handling.

## Known limitations

This is an educational implementation, not a drop-in `re` replacement:

- No capturing groups / backreferences (groups are used only for
  precedence, not extraction)
- No lazy (`*?`, `+?`) quantifiers or bounded repetition (`{m,n}`)
- No lookahead/lookbehind
- `^`/`$` are treated as whole-string anchors, not per-line multiline
  anchors (the CLI works around this by matching line-by-line)

## License

MIT — see [LICENSE](LICENSE).
