"""The guard never reads the truth: only the simulator and the evaluation may import guard.sim."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "guard"
ALLOWED = {"evaluate.py", "report.py", "cli.py"}


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module)
        elif isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
    return out


def test_guard_modules_do_not_import_the_simulator():
    for p in ROOT.glob("*.py"):
        if p.name in ALLOWED:
            continue
        assert not any(m.startswith("guard.sim") for m in imports(p)), p.name


def test_api_takes_only_a_path_from_the_evaluation():
    # The API serves generated reports; from guard.evaluate it may use the repository root and nothing else.
    tree = ast.parse((ROOT / "api.py").read_text())
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "guard.evaluate" for a in n.names}
    assert names <= {"ROOT"}
