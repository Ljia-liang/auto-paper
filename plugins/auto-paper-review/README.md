# Auto Paper Review plugin

This directory is the complete distributable Codex plugin. It includes the
workflow skill, MCP configuration, Python source, domain configuration, and a
first-use dependency bootstrapper.

Requirements:

- Codex with plugin and STDIO MCP support
- Python 3.10 or newer available as `python`
- PyPI network access on the first MCP launch

Users do not need to install the root Python project. The launcher creates an
isolated environment in the user's cache, installs `requirements-runtime.txt`,
and starts the bundled `auto_paper.mcp_server` module.

The `runtime/` and `config/` directories are generated from the repository's
canonical sources. Maintainers must run this from the repository root before a
release:

```text
python scripts/build_plugin.py
python scripts/build_plugin.py --check
```
