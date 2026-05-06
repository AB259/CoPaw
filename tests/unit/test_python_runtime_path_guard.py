# -*- coding: utf-8 -*-
"""Tests for the injected Python runtime tenant path guard."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from swe.security.python_runtime_path_guard import (
    prepare_python_runtime_path_guard_env,
)


def test_runtime_guard_allows_imports_from_existing_pythonpath_roots(
    tmp_path: Path,
) -> None:
    """Editable/local packages outside the tenant root must remain importable."""
    tenant_root = tmp_path / "tenant"
    tenant_root.mkdir()
    package_root = tmp_path / "package_src"
    package_root.mkdir()
    (package_root / "outside_package.py").write_text(
        "VALUE = 'imported from package root'\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(package_root)
    guard_dir = prepare_python_runtime_path_guard_env(
        env,
        tenant_root=tenant_root,
        base_dir=tenant_root,
    )

    with guard_dir:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import outside_package; print(outside_package.VALUE)",
            ],
            cwd=tenant_root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "imported from package root"
