---
name: wincompat
description: Scans repository paths for Windows breakage -- DOS device names (NUL, CON, AUX, COM1, ...), case-only collisions, trailing dots/spaces, illegal characters, over-long paths. Use before committing, in CI on every PR, and when Linux-created trees are consumed by Windows contributors. Exit 1 means a path that fails or silently rewrites a Windows git checkout.
license: MIT
compatibility: Requires Python 3.8+; git optional (falls back to a working-tree walk, or scan any path list with --paths-file). Works in Claude Code, Codex, Cursor, and any Agent Skills compatible client.
metadata:
  author: F0Rextasy
  version: "1.0"
---

# wincompat

A tree that checks out clean on Linux CI can be un-checkoutable on a
Windows machine: `git checkout` dies on `CON`, leaves a file named `nul`
that cannot be deleted, or keeps both `README.md` and `readme.md` until
one platform silently loses one. Every rule here is a path rule - no
content, no execution, no model.

## The one rule

You may not commit a path Windows cannot honor:

```bash
python scripts/wincompat . --strict
```

- **exit 1** - a path fails the gate (or a warning with `--strict`).
- **exit 0** - every path checkout-safe on Windows.
- **exit 2** - usage error.

## Protocol

1. **Choose the scan source**:
   - default: `git ls-files` over `[path]` (tracked + staged = what a
     checkout produces);
   - `--walk`: the working tree (falls back automatically outside a
     repo);
   - `--paths-file FILE` (or `-` for stdin): any newline list - zip
     listings, monorepo snapshots, archives.
2. **Read the verdict rows** - `file  FAIL  rule  message` plus the
   summary.
3. **Act on the rule**, not the symptom:

| Rule | Severity | Meaning |
| --- | --- | --- |
| `reserved-name` | fail | DOS device name as a name or component, any extension |
| `case-collision` | fail | two paths differ only by case (file or directory level) |
| `trailing-dot` / `trailing-space` | fail | Windows strips it - the name changes |
| `illegal-char` | fail | `<>:"|?*` or control characters in a name |
| `path-too-long` | warn | beyond MAX_PATH (260); blocks only with `--strict` |

4. **Exempt deliberately**: `--allow RULE=reason` (repeatable) records the
   reason in the summary; unknown rules are usage errors.

```console
$ python scripts/wincompat --paths-file examples/red-flags.txt --no-color
NUL.txt                FAIL  reserved-name   DOS device name 'NUL.txt' -- checkout fails on Windows
docs/api:v1.md         FAIL  illegal-char    'api:v1.md' contains ':' -- git checkout fails on Windows
release.md.            FAIL  trailing-dot    'release.md.' ends with a dot -- Windows strips it
src/aux/settings.json  FAIL  reserved-name   DOS device name 'aux' -- checkout fails on Windows
README.md              FAIL  case-collision  'README.md' vs 'readme.md' -- one platform wins, the other loses

wincompat: 5 failure(s), 0 warning(s) -- 6 paths scanned (paths-file)
wincompat: rename the path -- or exempt the rule with:  --allow RULE=<reason>
[exit 1]
```

## Hard bans

- Never "fix" a reserved name by deleting it on a Windows machine - the
  device eats the evidence; rename from Linux or list it via
  `--paths-file`.
- Never blanket-exempt `case-collision` to silence one finding - rename
  one of the two paths instead; the exemption is rule-wide.
- Never claim a tree is Windows-safe from a partial scan: use the git
  source (tracked + staged) or `--walk`, not a hand-picked subset.

## Reporting back

1. Counts: failures / warnings / scanned paths / exempted rules.
2. Command and exit code.
3. Action: renamed the path, or exempted a whole rule with its reason.
