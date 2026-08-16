"""Format Python files after Cursor edits. Reads hook JSON from stdin."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SKIP_PARTS = {
    "regtool",
    "generated",
    "reports",
    "site",
    ".venv",
    "__pycache__",
}

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _file_path(payload: dict) -> Path | None:
    raw = payload.get("file_path") or payload.get("filePath") or payload.get("path")
    if not raw:
        return None
    return Path(raw)


def _skip(path: Path) -> bool:
    if path.suffix != ".py":
        return True
    parts = {p.lower() for p in path.parts}
    return bool(parts & SKIP_PARTS)


def _ruff_cmd() -> list[str] | None:
    win = REPO_ROOT / ".venv" / "Scripts" / "ruff.exe"
    unix = REPO_ROOT / ".venv" / "bin" / "ruff"
    if win.is_file():
        return [str(win)]
    if unix.is_file():
        return [str(unix)]
    found = shutil.which("ruff")
    if found:
        return [found]
    uv = shutil.which("uv")
    if uv:
        return [uv, "run", "ruff"]
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("{}")
        return

    path = _file_path(payload if isinstance(payload, dict) else {})
    if path is None or _skip(path) or not path.is_file():
        print("{}")
        return

    ruff = _ruff_cmd()
    if ruff is None:
        print("{}")
        return

    result = subprocess.run(
        [*ruff, "format", str(path)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print("{}")
        return

    print(json.dumps({"additional_context": f"Ran ruff format on {path.name}."}))


if __name__ == "__main__":
    main()
