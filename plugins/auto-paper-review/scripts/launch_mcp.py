"""Bootstrap and launch the bundled Auto Paper MCP server.

The launcher uses only the Python standard library. On first use it creates a
versioned virtual environment in the user's cache and installs the plugin's
runtime dependencies. MCP protocol output remains on stdout; bootstrap logs go
to stderr.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import venv


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = PLUGIN_ROOT / "requirements-runtime.txt"
MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"


def _cache_root() -> Path:
    override = os.getenv("AUTO_PAPER_CACHE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "auto-paper-review"


def _environment_path() -> Path:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    version = str(manifest["version"])
    digest = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()[:12]
    return _cache_root() / f"{version}-{digest}"


def _environment_python(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def _dependencies_ready(python: Path) -> bool:
    if not python.is_file():
        return False
    probe = "import httpx,mcp,openpyxl,pydantic,pypdf,yaml,reportlab,rich"
    return subprocess.run(
        [str(python), "-c", probe],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def _prepare_environment() -> Path:
    if sys.version_info < (3, 10):
        raise RuntimeError("Auto Paper Review requires Python 3.10 or newer")

    environment = _environment_path()
    python = _environment_python(environment)
    if _dependencies_ready(python):
        return python

    print("Auto Paper Review: preparing the first-use Python environment...", file=sys.stderr)
    environment.parent.mkdir(parents=True, exist_ok=True)
    if not python.is_file():
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--requirement",
            str(REQUIREMENTS),
        ],
        stdout=sys.stderr,
        stderr=sys.stderr,
        check=True,
    )
    if not _dependencies_ready(python):
        raise RuntimeError("Auto Paper Review dependencies did not install correctly")
    return python


def main() -> int:
    try:
        python = _prepare_environment()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Auto Paper Review could not start: {error}", file=sys.stderr)
        return 1

    if "--bootstrap-only" in sys.argv[1:]:
        print(f"Auto Paper Review runtime ready: {python}", file=sys.stderr)
        return 0

    env = os.environ.copy()
    runtime_source = str(PLUGIN_ROOT / "runtime" / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (runtime_source, existing_pythonpath) if part
    )
    env.setdefault("AUTO_PAPER_DOMAIN", str(PLUGIN_ROOT / "config" / "domains" / "vit_reid.yaml"))
    return subprocess.call(
        [str(python), "-m", "auto_paper.mcp_server"],
        cwd=PLUGIN_ROOT,
        env=env,
    )


if __name__ == "__main__":
    raise SystemExit(main())
