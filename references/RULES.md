# Path catalogue

`scripts/wincompat` scans **paths only** - never file contents. Sources,
in priority order:

| Source | When | What it sees |
| --- | --- | --- |
| `--paths-file FILE` (`-` = stdin) | any time; mutually exclusive with a path argument | your newline list (`#` comments and blank lines skipped; trailing spaces are data, not padding) |
| `git ls-files` over `[path]` | inside a repository (default) | tracked + staged paths - exactly what a checkout produces |
| working-tree walk | outside a repo, or with `--walk` | every file under the root, excluding `.git`, `node_modules`, `__pycache__`, `.venv`, `venv` |

## Rules

Each path is checked component by component (directories break just like
files), then as a whole:

| Rule | Severity | Fires when | Message shows |
| --- | --- | --- | --- |
| `reserved-name` | fail | any component's stem (text before the first dot, case-insensitive) is `con`, `prn`, `aux`, `nul`, `com0`-`com9`, `lpt0`-`lpt9` - so `NUL`, `nul.txt`, and `src/AUX/x.json` all fire | the offending component |
| `trailing-dot` | fail | component ends with `.` | the component |
| `trailing-space` | fail | component ends with a space | the component |
| `illegal-char` | fail | component contains any of `<>:"|?*` or a control character (0x00-0x1F), shown as reprs | component + characters |
| `path-too-long` | warn | the whole path exceeds 259 characters (MAX_PATH 260 minus NUL) | length in characters |

## Case collisions (separate pass)

Every **ancestor prefix** of every path is keyed by `lower()`; a key owned
by two different spellings yields one `case-collision` finding naming both
(representative file = first in sort order). Checking prefixes, not whole
paths, is what catches `Docs/a.md` vs `docs/b.md`: the collision happens at
the directory level, where Windows keeps exactly one spelling.

## Exemptions

`--allow RULE=reason` (repeatable) exempts the **whole rule**, requires a
non-empty reason, and is echoed in JSON (`exempt`) and the text summary.
Unknown rule or empty reason -> usage error (exit 2). Exempt findings are
counted separately and never rendered as findings.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | no failing path; no warning when `--strict` |
| 1 | at least one fail, or a warning under `--strict` |
| 2 | usage: nonexistent root, unreadable paths file, bad `--allow`, conflicting arguments |

## Invariants

- Verdict = pure function of the path list: same list, same rows. No
  model, no network, no execution.
- Findings cite the exact component; a rename that clears the component
  clears the rule.
- A partial scan can never be sold as Windows-safe: git mode covers
  tracked+staged, walk covers the tree, `--paths-file` covers whatever
  list you feed it - `source` is recorded in the JSON verdict.
