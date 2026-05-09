"""
Pre-commit guard: block destructive SQL embedded in Python files.

Rule (see DEVELOPMENT.md "SQL externalization"):
  Destructive SQL must live in `sql/`, not in `.py`. The only exception is
  `db.py`, the canonical DB interface module.

Why: yesterday a top-level destructive statement in
`scripts/utils/reset_db_schema.py` silently wiped two tables on import.
Externalizing destructive verbs out of importable Python removes that class
of footgun.

How:
  Walks each .py file's AST and inspects string literal nodes. Module-,
  class-, and function-level docstrings are excluded so prose can describe
  the rule without tripping it. Comments are excluded because the AST drops
  them before string-node walking.

Usage:
  python scripts/hooks/sql_guard.py                # sweep entire repo
  python scripts/hooks/sql_guard.py <file> ...     # only the given files

Exit codes: 0 = clean, 1 = violations found.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

WHITELIST = {
    "db.py",
    # reset_db_schema.py is the canonical typed-confirmation gate for the
    # TRUNCATE in sql/admin/. Its CONFIRMATION_PHRASE and user prompts have
    # to mention TRUNCATE by name -- that is the gate -- but the actual SQL
    # statement lives in sql/admin/, not in this Python file.
    "scripts/utils/reset_db_schema.py",
}

EXCLUDE_DIRS = {".venv", "venv", "env", ".git", "__pycache__", "sql", "data_files"}

DESTRUCTIVE_PATTERNS = [
    # TABLE keyword is optional in Postgres for TRUNCATE; require a following
    # identifier so prose like "will TRUNCATE the table" or "(TRUNCATE)" does
    # not self-trip in scripts that have to describe the operation.
    re.compile(r"\bTRUNCATE\s+(?:TABLE\s+)?\w",             re.IGNORECASE),
    re.compile(r"\bDROP\s+TABLE\b",                         re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\b",                        re.IGNORECASE),
    re.compile(r"\bALTER\s+TABLE\b",                        re.IGNORECASE),
    re.compile(r"\bCREATE\s+TABLE\b",                       re.IGNORECASE),
    # UNIQUE / CONCURRENTLY are optional modifiers; keep them in scope.
    re.compile(r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\b",         re.IGNORECASE),
    re.compile(r"\bDROP\s+INDEX\b",                         re.IGNORECASE),
    re.compile(r"\bALTER\s+INDEX\b",                        re.IGNORECASE),
    re.compile(r"\bREINDEX\b",                              re.IGNORECASE),
    # Views and schemas are equally destructive.
    re.compile(r"\bDROP\s+(?:MATERIALIZED\s+)?VIEW\b",      re.IGNORECASE),
    re.compile(r"\bDROP\s+SCHEMA\b",                        re.IGNORECASE),
]


def first_match(s: str) -> str | None:
    for pat in DESTRUCTIVE_PATTERNS:
        m = pat.search(s)
        if m:
            return m.group(0)
    return None


def collect_docstring_node_ids(tree: ast.AST) -> set[int]:
    """Return the id() of every ast.Constant str that is a docstring."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if not body:
                continue
            first = body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                ids.add(id(first.value))
    return ids


def check_file(path: Path) -> list[tuple[int, str, str]]:
    """Return [(lineno, pattern, snippet), ...] for any destructive hits."""
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []

    docstring_ids = collect_docstring_node_ids(tree)
    findings: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstring_ids:
            continue
        match = first_match(node.value)
        if match:
            snippet = node.value.strip().splitlines()[0][:120]
            findings.append((node.lineno, match, snippet))
    return findings


def is_whitelisted(rel: str) -> bool:
    return rel.replace("\\", "/") in WHITELIST


def is_excluded(rel: str) -> bool:
    return any(p in EXCLUDE_DIRS for p in Path(rel).parts)


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
        # Skip explicit targets that resolve outside REPO_ROOT — main()
        # downstream calls path.relative_to(REPO_ROOT), which raises
        # ValueError on out-of-repo paths.
        try:
            p.relative_to(REPO_ROOT)
        except ValueError:
            continue
        paths.append(p)
    return paths


def main(argv: list[str]) -> int:
    targets = resolve_targets(argv)
    violations: list[tuple[Path, list[tuple[int, str, str]]]] = []

    for path in targets:
        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        if is_whitelisted(rel) or is_excluded(rel):
            continue
        hits = check_file(path)
        if hits:
            violations.append((path, hits))

    if not violations:
        return 0

    print("sql_guard: destructive SQL embedded in Python -- must live in sql/.")
    print("Move the statement into sql/{etl,schema,admin,analytics}/ and call")
    print("via db.execute_file(...) / db.query_file(...). See DEVELOPMENT.md.\n")
    for path, hits in violations:
        rel = path.relative_to(REPO_ROOT)
        for lineno, pattern, snippet in hits:
            print(f"  {rel}:{lineno}: {pattern.upper()}  |  {snippet}")
    print(f"\n{sum(len(h) for _, h in violations)} violation(s) in {len(violations)} file(s).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
