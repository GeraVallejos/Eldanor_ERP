"""Fail-fast check: todas las acciones @action deben existir en permission_action_map."""

from __future__ import annotations

import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
VIEWS_GLOB = "apps/*/api/views.py"

ACTION_DEF_RE = re.compile(
    r"@action\([^)]*\)\s*\n\s*def\s+([a-zA-Z_]\w*)\s*\(",
    re.MULTILINE,
)
PERMISSION_MAP_RE = re.compile(
    r"permission_action_map\s*=\s*\{(?P<body>[\s\S]*?)\}",
    re.MULTILINE,
)
MAP_KEY_RE = re.compile(r"\"([a-zA-Z_]\w*)\"\s*:")


def extract_actions(content: str) -> set[str]:
    return {match.group(1) for match in ACTION_DEF_RE.finditer(content)}


def extract_permission_keys(content: str) -> set[str]:
    keys: set[str] = set()
    for block in PERMISSION_MAP_RE.finditer(content):
        keys.update(MAP_KEY_RE.findall(block.group("body")))
    return keys


def main() -> int:
    missing_by_file: list[tuple[pathlib.Path, list[str]]] = []

    for file_path in sorted(ROOT.glob(VIEWS_GLOB)):
        content = file_path.read_text(encoding="utf-8")
        actions = extract_actions(content)
        keys = extract_permission_keys(content)

        missing = sorted(action for action in actions if action not in keys)
        if missing:
            missing_by_file.append((file_path, missing))

    if not missing_by_file:
        print("OK: Todas las acciones @action estan mapeadas en permission_action_map.")
        return 0

    print("ERROR: Se detectaron acciones custom sin mapping de permisos:")
    for file_path, missing in missing_by_file:
        rel_path = file_path.relative_to(ROOT)
        print(f" - {rel_path}: {', '.join(missing)}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
