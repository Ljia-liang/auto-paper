"""Assemble the self-contained Codex plugin from the canonical source tree."""

from __future__ import annotations

import argparse
import filecmp
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "auto-paper-review"


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )


def _tree_matches(source: Path, destination: Path) -> bool:
    if not destination.is_dir():
        return False
    comparison = filecmp.dircmp(source, destination, ignore=["__pycache__"])
    if comparison.left_only or comparison.right_only or comparison.diff_files or comparison.funny_files:
        return False
    return all(
        _tree_matches(source / name, destination / name)
        for name in comparison.common_dirs
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the bundled runtime is stale")
    args = parser.parse_args()
    pairs = [
        (ROOT / "src" / "auto_paper", PLUGIN / "runtime" / "src" / "auto_paper"),
        (ROOT / "config" / "domains", PLUGIN / "config" / "domains"),
    ]
    if args.check:
        stale = [str(destination) for source, destination in pairs if not _tree_matches(source, destination)]
        if stale:
            raise SystemExit("Plugin runtime is stale; run python scripts/build_plugin.py\n" + "\n".join(stale))
        print("Plugin runtime is in sync")
        return
    for source, destination in pairs:
        _copy_tree(source, destination)
    print(f"Built plugin runtime at {PLUGIN}")


if __name__ == "__main__":
    main()
