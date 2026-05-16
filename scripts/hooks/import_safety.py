"""
Pre-commit guard: block destructive `db.py` SQL-runner calls at module scope.

Rule:
  Calls to `db.execute_file()`, `db.execute_values_file()`, or
  `db.truncate_table()` must live inside a function/class body or under
  `if __name__ == "__main__":`. At module scope they fire on import.

Why: `scripts/utils/reset_db_schema.py` once held a top-level
`db.execute("TRUNCATE ...")` that wiped two tables when the module was
imported during a verification check. Pairs with `sql_guard.py`, which
blocks destructive SQL strings in .py — this hook covers the same risk
class for SQL invoked via externalized files (`db.execute_file(...)`).
Bare `execute()` is intentionally excluded: the name collides with the
psycopg2 cursor API, and any destructive SQL string passed to it is
already caught by `sql_guard.py`.

Usage:
  python scripts/hooks/import_safety.py            # sweep entire repo
  python scripts/hooks/import_safety.py <file> ... # only the given files

Exit codes: 0 = clean, 1 = violations found.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Methods unique to the `db.py` connection helper that issue arbitrary SQL
# or truncate. At module scope they execute on import — same class of bug
# as the reset_db_schema incident. Bare `execute` is omitted because the
# name collides with `psycopg2.cursor.execute`; the destructive-string risk
# on that path is covered by `sql_guard.py`.
DESTRUCTIVE_METHODS = frozenset({
    "execute_file",
    "execute_values_file",
    "truncate_table",
})

WHITELIST = {
    "db.py",  # defines the methods themselves
}

EXCLUDE_DIRS = {".venv", "venv", "env", ".git", "__pycache__", "sql", "data_files"}

SAFE_CONTAINERS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def is_main_guard(node: ast.AST) -> bool:
    """True iff `node` is `if __name__ == "__main__":`."""
    if not isinstance(node, ast.If):
        return False
    test = node.test
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    sides = (test.left, test.comparators[0])
    has_name = any(isinstance(s, ast.Name) and s.id == "__name__" for s in sides)
    has_main = any(
        isinstance(s, ast.Constant) and s.value == "__main__" for s in sides
    )
    return has_name and has_main


def collect_safe_node_ids(tree: ast.AST) -> set[int]:
    """Return id() of every AST node living inside a safe container.

    Safe = function/class body, or `if __name__ == "__main__":` block.
    Anything not in this set runs on import.
    """
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, SAFE_CONTAINERS):
            for child in ast.walk(node):
                ids.add(id(child))
        elif is_main_guard(node):
            for stmt in (*node.body, *node.orelse):
                for child in ast.walk(stmt):
                    ids.add(id(child))
    return ids


def check_file(path: Path) -> list[tuple[int, str]]:
    """Return [(lineno, method), ...] for any module-scope destructive calls."""
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []

    safe_ids = collect_safe_node_ids(tree)
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr not in DESTRUCTIVE_METHODS:
            continue
        if id(node) in safe_ids:
            continue
        findings.append((node.lineno, func.attr))
    return findings


def is_whitelisted(rel: str) -> bool:
    return rel.replace("\\", "/") in WHITELIST


def is_excluded(rel: str) -> bool:
    return any(p in EXCLUDE_DIRS for p in Path(rel).parts)


def is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def iter_repo_py_files() -> list[Path]:
    return [
        p for p in REPO_ROOT.rglob("*.py")
        if not is_excluded(str(p.relative_to(REPO_ROOT)))
    ]


def resolve_targets(argv: list[str]) -> list[Path]:
    if not argv:
        return iter_repo_py_files()
    paths = []
    for arg in argv:
        p = Path(arg)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if p.suffix != ".py" or not p.exists():
            continue
        if not is_under(p, REPO_ROOT):
            continue
        paths.append(p)
    return paths


def main(argv: list[str]) -> int:
    targets = resolve_targets(argv)
    violations: list[tuple[Path, list[tuple[int, str]]]] = []

    for path in targets:
        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        if is_whitelisted(rel) or is_excluded(rel):
            continue
        hits = check_file(path)
        if hits:
            violations.append((path, hits))

    if not violations:
        return 0

    print("import_safety: destructive db.py SQL-runner call at module scope.")
    print("These run on import. Move into a function and gate behind")
    print('`if __name__ == "__main__":` so import is side-effect-free.\n')
    for path, hits in violations:
        rel = path.relative_to(REPO_ROOT)
        for lineno, method in hits:
            print(f"  {rel}:{lineno}: db.{method}()")
    print(f"\n{sum(len(h) for _, h in violations)} violation(s) in {len(violations)} file(s).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
