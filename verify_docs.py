"""Local documentation build/verifier.

Purpose:
  Provides a quick, scriptable proof that the documentation site can build
  BEFORE (or in addition to) relying on the GitHub Pages workflow.

What it does:
  1. Checks for required files: mkdocs.yml, docs/ directory.
  2. Optionally imports mkdocs; if missing, prints install instructions.
  3. Attempts a dry build (mkdocs build) to ./site/ if mkdocs is available.
  4. Emits a concise JSON summary to stdout for easy parsing.

Usage:
  powershell:
    .\.venv\Scripts\python.exe .\verify_docs.py

Exit codes:
  0 = success (structure OK, build succeeded or was skipped due to missing mkdocs)
  1 = structure missing critical files
  2 = mkdocs import failed when build requested
  3 = mkdocs build raised an exception
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).parent

def main() -> int:
    summary: Dict[str, Any] = {
        "mkdocs_yml_present": False,
        "docs_dir_present": False,
        "mkdocs_installed": False,
        "build_attempted": False,
        "build_success": False,
        "site_dir": str(ROOT / "site"),
        "notes": []
    }

    mkdocs_yml = ROOT / "mkdocs.yml"
    docs_dir = ROOT / "docs"

    if mkdocs_yml.is_file():
        summary["mkdocs_yml_present"] = True
    else:
        summary["notes"].append("mkdocs.yml not found at repo root")

    if docs_dir.is_dir():
        summary["docs_dir_present"] = True
    else:
        summary["notes"].append("docs/ directory missing")

    if not (summary["mkdocs_yml_present"] and summary["docs_dir_present"]):
        print(json.dumps(summary, indent=2))
        return 1

    # Try to import mkdocs
    try:
        import mkdocs  # type: ignore
        summary["mkdocs_installed"] = True
    except Exception as e:  # pragma: no cover
        summary["notes"].append(f"mkdocs import failed: {e}")
        summary["notes"].append("Install with: pip install mkdocs mkdocs-material")
        print(json.dumps(summary, indent=2))
        # Structure is fine; absence of mkdocs locally isn't fatal.
        return 0

    # Perform build if mkdocs is available
    from mkdocs import config
    from mkdocs import commands

    summary["build_attempted"] = True
    try:
        cfg = config.load_config(str(mkdocs_yml))
        commands.build.build(cfg)  # builds into site/ per mkdocs.yml or default
        if (ROOT / "site").is_dir():
            summary["build_success"] = True
        else:
            summary["notes"].append("Build finished but site/ directory not found.")
    except Exception as e:  # pragma: no cover
        summary["notes"].append(f"mkdocs build error: {e}")
        print(json.dumps(summary, indent=2))
        return 3

    print(json.dumps(summary, indent=2))
    return 0 if summary["build_success"] else 3


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
