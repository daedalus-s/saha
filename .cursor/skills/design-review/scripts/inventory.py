#!/usr/bin/env python3
"""Design-review inventory: objective metrics for targeted Python and TypeScript code.

Usage:
    python inventory.py <path> [<path> ...] [--json] [--root <repo-root>]

Reports per target:
  * file and function/component sizes, branch-complexity hotspots
  * internal import graph and cycles (Python absolute `app.*` imports, TS relative imports)
  * naming-convention deviations (Python snake_case/PascalCase, TS camelCase/PascalCase)
  * source modules that have no matching test file

Standard library only. Heuristic for TypeScript (regex + brace matching); exact for Python (ast).
Findings are leads to verify by reading the code, not conclusions.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Thresholds (tune here, not in callers)
MAX_FILE_LINES = 300
MAX_FUNC_LINES = 40
MAX_COMPLEXITY = 10
MAX_PARAMS = 5

PY_EXT = {".py"}
TS_EXT = {".ts", ".tsx"}
SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build", ".expo", ".cache", ".cache-test"}
TEST_MARKERS = (".test.", "_test.", "/tests/", "\\tests\\", "test_")
# Names that legitimately recur (protocol methods, React/Expo conventions, dunder-like entry points)
IGNORED_DUP_NAMES = {"search", "main", "styles", "default", "render", "setup", "teardown", "handler"}

SNAKE = re.compile(r"^_{0,2}[a-z][a-z0-9_]*_?$")
UPPER_SNAKE = re.compile(r"^_?[A-Z][A-Z0-9_]*$")
PASCAL = re.compile(r"^_?[A-Z][A-Za-z0-9]*$")
CAMEL = re.compile(r"^_?[a-z][A-Za-z0-9]*$")


@dataclass
class Unit:
    name: str
    kind: str
    start: int
    end: int
    complexity: int = 0
    params: int = 0

    @property
    def lines(self) -> int:
        return self.end - self.start + 1


@dataclass
class FileReport:
    path: str
    language: str
    lines: int
    units: list[Unit] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    naming: list[str] = field(default_factory=list)
    has_test: bool | None = None
    is_test: bool = False


# --------------------------------------------------------------------------- discovery

def iter_files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            if p.suffix in PY_EXT | TS_EXT:
                out.append(p)
            continue
        if not p.is_dir():
            print(f"warning: {raw} does not exist", file=sys.stderr)
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                fp = Path(dirpath) / fn
                if fp.suffix in PY_EXT | TS_EXT and not fn.endswith(".d.ts"):
                    out.append(fp)
    return sorted(set(out))


def is_test_file(path: Path) -> bool:
    s = str(path).replace("\\", "/")
    return any(m.strip("\\") in s for m in TEST_MARKERS) or path.name.startswith("test_")


# --------------------------------------------------------------------------- python

class _Complexity(ast.NodeVisitor):
    BRANCH = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.AsyncWith,
              ast.IfExp, ast.comprehension, ast.Assert, ast.Match)

    def __init__(self) -> None:
        self.score = 1

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, self.BRANCH):
            self.score += 1
        elif isinstance(node, ast.BoolOp):
            self.score += len(node.values) - 1
        super().generic_visit(node)


def analyze_python(path: Path, root: Path) -> FileReport:
    text = path.read_text(encoding="utf-8", errors="replace")
    rep = FileReport(path=_rel(path, root), language="python", lines=text.count("\n") + 1, is_test=is_test_file(path))
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        rep.naming.append(f"syntax error, skipped analysis: {exc}")
        return rep

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cx = _Complexity()
            for child in node.body:
                cx.visit(child)
            args = node.args
            nparams = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
            if args.args and args.args[0].arg in ("self", "cls"):
                nparams -= 1
            rep.units.append(Unit(node.name, "function", node.lineno, node.end_lineno or node.lineno, cx.score, nparams))
            if not SNAKE.match(node.name) and not node.name.startswith("__"):
                rep.naming.append(f"L{node.lineno} function `{node.name}` is not snake_case")
            for a in args.args + args.kwonlyargs + args.posonlyargs:
                if not SNAKE.match(a.arg) and a.arg not in ("self", "cls"):
                    rep.naming.append(f"L{node.lineno} parameter `{a.arg}` is not snake_case")
        elif isinstance(node, ast.ClassDef):
            rep.units.append(Unit(node.name, "class", node.lineno, node.end_lineno or node.lineno))
            if not PASCAL.match(node.name):
                rep.naming.append(f"L{node.lineno} class `{node.name}` is not PascalCase")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = ("." * node.level) + node.module
                rep.imports.append(mod)
            elif isinstance(node, ast.Import):
                rep.imports.extend(alias.name for alias in node.names)

    # module-level assignments: constants UPPER_SNAKE or snake_case; anything else flagged
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    n = tgt.id
                    if not (UPPER_SNAKE.match(n) or SNAKE.match(n)):
                        rep.naming.append(f"L{node.lineno} module variable `{n}` is neither UPPER_SNAKE nor snake_case")
    return rep


# --------------------------------------------------------------------------- typescript (heuristic)

TS_IMPORT = re.compile(r"""^\s*(?:import|export)\s[^;]*?\sfrom\s+["']([^"']+)["']""", re.M)
TS_FUNC = re.compile(
    r"""^(?P<indent>[ \t]*)(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(?P<name>[A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\s*\((?P<params>[^)]*)\)""",
    re.M,
)
TS_ARROW = re.compile(
    r"""^(?P<indent>[ \t]*)(?:export\s+)?(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s*)?(?:\((?P<params>[^)]*)\)|[A-Za-z_$][\w$]*)\s*(?::[^=]+)?=>""",
    re.M,
)
TS_TYPE = re.compile(r"""^\s*(?:export\s+)?(?:type|interface|enum|class)\s+(?P<name>[A-Za-z_$][\w$]*)""", re.M)
TS_CONST = re.compile(r"""^(?:export\s+)?const\s+(?P<name>[A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?!.*=>)""", re.M)
TS_BRANCH = re.compile(r"\b(if|for|while|case|catch)\b|\?\s*[^.:]|&&|\|\||\?\?")


def _block_end(text: str, start_idx: int) -> int:
    """Return the index of the closing brace of the first `{` at/after start_idx (or -1)."""
    i = text.find("{", start_idx)
    if i == -1:
        return -1
    depth = 0
    in_str: str | None = None
    j = i
    while j < len(text):
        c = text[j]
        if in_str:
            if c == "\\":
                j += 2
                continue
            if c == in_str:
                in_str = None
        elif c in "\"'`":
            in_str = c
        elif c == "/" and text[j:j + 2] == "//":
            j = text.find("\n", j)
            if j == -1:
                return -1
        elif c == "/" and text[j:j + 2] == "/*":
            j = text.find("*/", j)
            if j == -1:
                return -1
            j += 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def analyze_typescript(path: Path, root: Path) -> FileReport:
    text = path.read_text(encoding="utf-8", errors="replace")
    rep = FileReport(path=_rel(path, root), language="typescript", lines=text.count("\n") + 1, is_test=is_test_file(path))
    is_tsx = path.suffix == ".tsx"

    rep.imports = [m.group(1) for m in TS_IMPORT.finditer(text)]

    seen: set[tuple[str, int]] = set()
    for rx, kind in ((TS_FUNC, "function"), (TS_ARROW, "arrow")):
        for m in rx.finditer(text):
            name = m.group("name")
            start = _line_of(text, m.start())
            if (name, start) in seen:
                continue
            seen.add((name, start))
            end_idx = _block_end(text, m.end())
            end = _line_of(text, end_idx) if end_idx != -1 else start
            body = text[m.end():end_idx] if end_idx != -1 else ""
            complexity = 1 + len(TS_BRANCH.findall(body))
            params = m.group("params") or ""
            nparams = len([p for p in params.split(",") if p.strip()]) if params.strip() else 0
            # destructured props count as one param
            if params.strip().startswith("{"):
                nparams = 1
            unit_kind = "component" if (is_tsx and PASCAL.match(name) and "return" in body and "<" in body) else kind
            rep.units.append(Unit(name, unit_kind, start, end, complexity, nparams))

            if unit_kind == "component":
                if not PASCAL.match(name):
                    rep.naming.append(f"L{start} component `{name}` is not PascalCase")
            elif not CAMEL.match(name) and not (kind == "arrow" and UPPER_SNAKE.match(name)):
                if not (is_tsx and PASCAL.match(name)):
                    rep.naming.append(f"L{start} function `{name}` is not camelCase")

    for m in TS_TYPE.finditer(text):
        name = m.group("name")
        if not PASCAL.match(name):
            rep.naming.append(f"L{_line_of(text, m.start())} type `{name}` is not PascalCase")

    for m in TS_CONST.finditer(text):
        name = m.group("name")
        line = _line_of(text, m.start())
        if not (CAMEL.match(name) or UPPER_SNAKE.match(name) or (is_tsx and PASCAL.match(name))):
            rep.naming.append(f"L{line} const `{name}` is neither camelCase nor UPPER_SNAKE")

    if is_tsx and not path.name.startswith(("_", "+", "[", "(")) and path.parent.name != "app" \
            and "components" in path.parts and not PASCAL.match(path.stem):
        rep.naming.append(f"component file `{path.name}` is not PascalCase")
    return rep


# --------------------------------------------------------------------------- graph

def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _py_module_name(rel: str) -> str | None:
    # services/api/app/search/base.py -> app.search.base ; __init__ -> package
    parts = rel[:-3].split("/")
    if "app" not in parts:
        return None
    parts = parts[parts.index("app"):]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def build_graph(reports: list[FileReport], root: Path) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    py_by_mod = {m: r.path for r in reports if r.language == "python" for m in [_py_module_name(r.path)] if m}
    ts_paths = {r.path for r in reports if r.language == "typescript"}

    for r in reports:
        deps: set[str] = set()
        if r.language == "python":
            for imp in r.imports:
                if imp.startswith("app"):
                    # resolve longest matching module (handles `from app.search import x` where x is a symbol)
                    cand = imp
                    while cand and cand not in py_by_mod:
                        cand = cand.rpartition(".")[0]
                    if cand and py_by_mod[cand] != r.path:
                        deps.add(py_by_mod[cand])
        else:
            base = Path(r.path).parent
            for imp in r.imports:
                if not imp.startswith("."):
                    continue
                target = (base / imp).as_posix()
                target = os.path.normpath(target).replace("\\", "/")
                for cand in (target + ".ts", target + ".tsx", target + "/index.ts", target + "/index.tsx"):
                    if cand in ts_paths:
                        deps.add(cand)
                        break
        graph[r.path] = deps
    return graph


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    seen_cycles: set[frozenset[str]] = set()
    state: dict[str, int] = {}
    stack: list[str] = []

    def dfs(n: str) -> None:
        state[n] = 1
        stack.append(n)
        for m in sorted(graph.get(n, ())):
            if state.get(m, 0) == 0:
                dfs(m)
            elif state.get(m) == 1:
                cyc = stack[stack.index(m):] + [m]
                key = frozenset(cyc)
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    cycles.append(cyc)
        stack.pop()
        state[n] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            dfs(node)
    return cycles


# --------------------------------------------------------------------------- tests

def locate_tests(reports: list[FileReport], root: Path) -> None:
    test_files = [p for p in root.rglob("*") if p.is_file() and p.suffix in PY_EXT | TS_EXT
                  and is_test_file(p) and not any(s in p.parts for s in SKIP_DIRS)]
    test_names = {p.name for p in test_files}
    test_stems = {p.stem for p in test_files}
    for r in reports:
        if r.is_test:
            r.has_test = None
            continue
        p = Path(r.path)
        if r.language == "python":
            if p.name == "__init__.py":
                stem = p.parent.name
            else:
                stem = p.stem
            r.has_test = f"test_{stem}.py" in test_names or any(s.startswith(f"test_{stem}") for s in test_stems)
        else:
            r.has_test = f"{p.stem}.test{p.suffix}" in test_names or f"{p.stem}.test.ts" in test_names \
                or f"{p.stem}.spec{p.suffix}" in test_names


# --------------------------------------------------------------------------- output

def render_text(reports: list[FileReport], graph: dict[str, set[str]], cycles: list[list[str]]) -> str:
    out: list[str] = []
    src = [r for r in reports if not r.is_test]
    out.append(f"Design inventory: {len(reports)} files ({len(src)} source, {len(reports) - len(src)} test)\n")

    out.append("== Files by size ==")
    for r in sorted(reports, key=lambda r: -r.lines):
        flag = "  <-- over %d lines" % MAX_FILE_LINES if r.lines > MAX_FILE_LINES else ""
        out.append(f"  {r.lines:5d}  {r.path}{flag}")

    out.append("\n== Long or complex units (>%d lines, complexity >%d, or >%d params) ==" % (MAX_FUNC_LINES, MAX_COMPLEXITY, MAX_PARAMS))
    hot = []
    for r in reports:
        for u in r.units:
            if u.kind == "class":
                continue
            if u.lines > MAX_FUNC_LINES or u.complexity > MAX_COMPLEXITY or u.params > MAX_PARAMS:
                hot.append((r.path, u))
    if not hot:
        out.append("  none")
    for path, u in sorted(hot, key=lambda t: (-t[1].complexity, -t[1].lines)):
        out.append(f"  {path}:{u.start}-{u.end}  {u.kind} {u.name}  lines={u.lines} complexity={u.complexity} params={u.params}")

    out.append("\n== Internal dependencies (target -> internal deps) ==")
    for path in sorted(graph):
        deps = graph[path]
        if deps:
            out.append(f"  {path}")
            for d in sorted(deps):
                out.append(f"      -> {d}")
    fan_in: dict[str, int] = {}
    for deps in graph.values():
        for d in deps:
            fan_in[d] = fan_in.get(d, 0) + 1
    if fan_in:
        out.append("  fan-in (most depended-upon):")
        for d, n in sorted(fan_in.items(), key=lambda kv: -kv[1])[:8]:
            out.append(f"      {n:3d}  {d}")

    out.append("\n== Import cycles ==")
    if not cycles:
        out.append("  none")
    for cyc in cycles:
        out.append("  " + " -> ".join(cyc))

    out.append("\n== Naming deviations ==")
    any_naming = False
    for r in reports:
        for n in r.naming:
            any_naming = True
            out.append(f"  {r.path}: {n}")
    if not any_naming:
        out.append("  none")

    out.append("\n== Same-named units defined in more than one file (possible duplication) ==")
    by_name: dict[str, list[str]] = {}
    for r in src:
        for u in r.units:
            if u.kind in ("class",) or u.name.startswith("__") or u.name in IGNORED_DUP_NAMES:
                continue
            by_name.setdefault(u.name, []).append(f"{r.path}:{u.start}")
    dups = {n: locs for n, locs in by_name.items() if len({l.split(":")[0] for l in locs}) > 1}
    if not dups:
        out.append("  none")
    for n, locs in sorted(dups.items()):
        out.append(f"  {n}: " + ", ".join(locs))

    out.append("\n== Source modules without a matching test file ==")
    missing = [r.path for r in src if r.has_test is False]
    if not missing:
        out.append("  none")
    for m in missing:
        out.append(f"  {m}")

    out.append("\n== Unit inventory ==")
    for r in reports:
        if not r.units:
            continue
        out.append(f"  {r.path}")
        for u in sorted(r.units, key=lambda u: u.start):
            out.append(f"      L{u.start:<4} {u.kind:<9} {u.name}  ({u.lines} lines, cx {u.complexity})")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="files or directories to inventory")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    ap.add_argument("--root", default=None, help="repository root (default: git toplevel or cwd)")
    args = ap.parse_args(argv)

    root = Path(args.root) if args.root else _detect_root()
    files = iter_files(args.paths)
    if not files:
        print("no .py/.ts/.tsx files found in targets", file=sys.stderr)
        return 1

    reports = [analyze_python(f, root) if f.suffix in PY_EXT else analyze_typescript(f, root) for f in files]
    graph = build_graph(reports, root)
    cycles = find_cycles(graph)
    locate_tests(reports, root)

    if args.json:
        payload = {
            "root": str(root),
            "thresholds": {"file_lines": MAX_FILE_LINES, "func_lines": MAX_FUNC_LINES, "complexity": MAX_COMPLEXITY, "params": MAX_PARAMS},
            "files": [{**asdict(r), "units": [{**asdict(u), "lines": u.lines} for u in r.units]} for r in reports],
            "graph": {k: sorted(v) for k, v in graph.items()},
            "cycles": cycles,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_text(reports, graph, cycles))
    return 0


def _detect_root() -> Path:
    p = Path.cwd()
    for cand in (p, *p.parents):
        if (cand / ".git").exists():
            return cand
    return p


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
