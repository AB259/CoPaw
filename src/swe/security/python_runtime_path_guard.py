# -*- coding: utf-8 -*-
"""Runtime path guard injected into shell-launched Python processes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import MutableMapping

_TENANT_ROOT_ENV = "SWE_TENANT_PATH_GUARD_ROOT"
_BASE_DIR_ENV = "SWE_TENANT_PATH_GUARD_BASE_DIR"

_SITE_CUSTOMIZE_SOURCE = """\
from swe_tenant_path_guard import install_from_env

install_from_env()
"""

_RUNTIME_GUARD_SOURCE = r'''
"""Tenant path guard installed through sitecustomize."""

from __future__ import annotations

import builtins
import functools
import io
import os
import pathlib
import shlex
import shutil
import subprocess
import sys

try:
    import _io
except ImportError:  # pragma: no cover - implementation dependent
    _io = None

try:
    import posix
except ImportError:  # pragma: no cover - non-POSIX platforms
    posix = None

try:
    import sysconfig
except ImportError:  # pragma: no cover - always present on CPython
    sysconfig = None

_TENANT_ROOT_ENV = "SWE_TENANT_PATH_GUARD_ROOT"
_BASE_DIR_ENV = "SWE_TENANT_PATH_GUARD_BASE_DIR"
_MISSING = object()


class TenantPathGuardError(PermissionError):
    """Raised when Python runtime code tries to escape the tenant root."""


_ORIGINAL_PATH_RESOLVE = pathlib.Path.resolve
_ORIGINAL_PATH_CWD = pathlib.Path.cwd
_ORIGINAL_SUBPROCESS_POPEN = subprocess.Popen
_INSTALLED = False
_TENANT_ROOT = None
_BASE_DIR = None
_RUNTIME_ALLOWED_ROOTS = ()
_CHECKING_PATH = False


def _resolve_without_guard(path, *, strict=False):
    return _ORIGINAL_PATH_RESOLVE(path, strict=strict)


def _is_relative_to(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _collect_runtime_allowed_roots():
    candidates = [pathlib.Path(__file__).parent]

    for value in sys.path:
        if value:
            candidates.append(pathlib.Path(value))

    for value in (
        getattr(sys, "base_prefix", None),
        getattr(sys, "prefix", None),
        getattr(sys, "base_exec_prefix", None),
        getattr(sys, "exec_prefix", None),
    ):
        if value:
            candidates.append(pathlib.Path(value))

    if sysconfig is not None:
        for value in sysconfig.get_paths().values():
            if value:
                candidates.append(pathlib.Path(value))

    roots = []
    for candidate in candidates:
        try:
            resolved = _resolve_without_guard(candidate.expanduser(), strict=False)
        except (OSError, RuntimeError):
            continue
        if resolved not in roots:
            roots.append(resolved)
    return tuple(roots)


def _fsdecode_path(path):
    if isinstance(path, int):
        return None
    try:
        return os.fsdecode(path)
    except (TypeError, ValueError):
        return None


def _current_base_dir():
    try:
        cwd = _resolve_without_guard(_ORIGINAL_PATH_CWD(), strict=False)
    except (OSError, RuntimeError):
        return _BASE_DIR
    if _TENANT_ROOT is not None and _is_relative_to(cwd, _TENANT_ROOT):
        return cwd
    return _BASE_DIR


def _resolve_candidate(path):
    decoded = _fsdecode_path(path)
    if decoded is None:
        return None, None

    path_obj = pathlib.Path(os.path.expanduser(decoded))
    if not path_obj.is_absolute():
        path_obj = _current_base_dir() / path_obj

    try:
        resolved = _resolve_without_guard(path_obj, strict=False)
    except (OSError, RuntimeError):
        resolved = path_obj.absolute()
    return decoded, resolved


def _is_runtime_allowed_path(resolved):
    return any(
        resolved == root or _is_relative_to(resolved, root)
        for root in _RUNTIME_ALLOWED_ROOTS
    )


def _check_path(path, operation):
    global _CHECKING_PATH

    if _TENANT_ROOT is None:
        return
    if _CHECKING_PATH:
        return

    _CHECKING_PATH = True
    try:
        decoded, resolved = _resolve_candidate(path)
        if resolved is None:
            return

        if _is_relative_to(resolved, _TENANT_ROOT):
            return
        if _is_runtime_allowed_path(resolved):
            return

        raise TenantPathGuardError(
            f"Python runtime guard denied {operation} outside the allowed workspace: "
            f"{decoded}"
        )
    finally:
        _CHECKING_PATH = False


def _argument(args, kwargs, index, keyword):
    if len(args) > index:
        return args[index]
    if keyword and keyword in kwargs:
        return kwargs[keyword]
    return _MISSING


def _wrap_path_function(module, name, specs):
    original = getattr(module, name, None)
    if original is None or not callable(original):
        return

    @functools.wraps(original)
    def wrapper(*args, **kwargs):
        for index, keyword, label in specs:
            value = _argument(args, kwargs, index, keyword)
            if value is not _MISSING:
                _check_path(value, f"{label or name} path")
        return original(*args, **kwargs)

    setattr(module, name, wrapper)


def _wrap_path_method(cls, name, specs):
    original = getattr(cls, name, None)
    if original is None or not callable(original):
        return

    @functools.wraps(original)
    def wrapper(self, *args, **kwargs):
        _check_path(self, f"pathlib.{name} path")
        for index, keyword, label in specs:
            value = _argument(args, kwargs, index, keyword)
            if value is not _MISSING:
                _check_path(value, f"pathlib.{label or name} path")
        return original(self, *args, **kwargs)

    setattr(cls, name, wrapper)


def _looks_like_path_token(value):
    decoded = _fsdecode_path(value)
    if not decoded:
        return False
    return decoded.startswith(("/", "./", "../", "~"))


def _iter_command_tokens(command):
    if isinstance(command, (list, tuple)):
        return list(command)
    if isinstance(command, str):
        try:
            return shlex.split(command)
        except ValueError:
            return command.split()
    return []


def _check_subprocess_command(command, cwd=None, executable=None):
    if cwd is not None:
        _check_path(cwd, "subprocess cwd")
    if executable is not None and _looks_like_path_token(executable):
        _check_path(executable, "subprocess executable")

    for token in _iter_command_tokens(command):
        if _looks_like_path_token(token):
            _check_path(token, "subprocess argument")


class _GuardedPopen(_ORIGINAL_SUBPROCESS_POPEN):
    def __init__(self, *args, **kwargs):
        command = _argument(args, kwargs, 0, "args")
        if command is not _MISSING:
            _check_subprocess_command(
                command,
                cwd=kwargs.get("cwd"),
                executable=kwargs.get("executable"),
            )
        super().__init__(*args, **kwargs)


def _wrap_os_system(name):
    original = getattr(os, name, None)
    if original is None or not callable(original):
        return

    @functools.wraps(original)
    def wrapper(command, *args, **kwargs):
        _check_subprocess_command(command)
        return original(command, *args, **kwargs)

    setattr(os, name, wrapper)


def _install_function_wrappers():
    for module in (builtins, io, _io):
        if module is None:
            continue
        _wrap_path_function(module, "open", [(0, "file", "open")])
        _wrap_path_function(module, "open_code", [(0, "path", "open_code")])

    for module in (os, posix):
        if module is None:
            continue
        for name in (
            "access",
            "chdir",
            "chmod",
            "chown",
            "lchown",
            "listdir",
            "lstat",
            "mkdir",
            "makedirs",
            "open",
            "readlink",
            "remove",
            "rmdir",
            "scandir",
            "stat",
            "truncate",
            "unlink",
            "utime",
        ):
            _wrap_path_function(module, name, [(0, "path", name)])
        for name in ("rename", "replace", "link"):
            _wrap_path_function(
                module,
                name,
                [(0, "src", "source"), (1, "dst", "destination")],
            )
        _wrap_path_function(
            module,
            "symlink",
            [(0, "src", "symlink target"), (1, "dst", "symlink path")],
        )

    for name in (
        "copyfile",
        "copymode",
        "copystat",
        "copy",
        "copy2",
        "copytree",
        "move",
    ):
        _wrap_path_function(
            shutil,
            name,
            [(0, "src", "source"), (1, "dst", "destination")],
        )
    _wrap_path_function(shutil, "rmtree", [(0, "path", "rmtree")])

    for name in ("system", "popen"):
        _wrap_os_system(name)

    subprocess.Popen = _GuardedPopen


def _install_pathlib_wrappers():
    for name in (
        "chmod",
        "exists",
        "glob",
        "is_dir",
        "is_file",
        "is_mount",
        "is_symlink",
        "iterdir",
        "lchmod",
        "link_to",
        "lstat",
        "mkdir",
        "open",
        "read_bytes",
        "read_text",
        "readlink",
        "rename",
        "replace",
        "rglob",
        "rmdir",
        "samefile",
        "stat",
        "touch",
        "unlink",
        "write_bytes",
        "write_text",
    ):
        _wrap_path_method(pathlib.Path, name, [])

    for name in ("rename", "replace", "link_to", "hardlink_to"):
        _wrap_path_method(pathlib.Path, name, [(0, "target", "target")])
    _wrap_path_method(pathlib.Path, "symlink_to", [(0, "target", "symlink target")])


def _audit_hook(event, args):
    if event == "open" and args:
        _check_path(args[0], "open")
    elif event in {
        "os.chdir",
        "os.listdir",
        "os.mkdir",
        "os.remove",
        "os.rmdir",
        "os.scandir",
        "os.truncate",
        "os.unlink",
    } and args:
        _check_path(args[0], event)
    elif event in {"os.rename", "os.replace", "os.link", "os.symlink"}:
        if len(args) > 0:
            _check_path(args[0], f"{event} source")
        if len(args) > 1:
            _check_path(args[1], f"{event} destination")
    elif event == "subprocess.Popen" and len(args) >= 2:
        _check_subprocess_command(args[1], cwd=args[2] if len(args) > 2 else None)


def install_from_env():
    global _INSTALLED, _TENANT_ROOT, _BASE_DIR, _RUNTIME_ALLOWED_ROOTS

    if _INSTALLED:
        return

    tenant_root = os.environ.get(_TENANT_ROOT_ENV)
    if not tenant_root:
        return

    _TENANT_ROOT = _resolve_without_guard(
        pathlib.Path(os.path.expanduser(tenant_root)),
        strict=False,
    )
    base_dir = os.environ.get(_BASE_DIR_ENV) or tenant_root
    _BASE_DIR = _resolve_without_guard(
        pathlib.Path(os.path.expanduser(base_dir)),
        strict=False,
    )
    _RUNTIME_ALLOWED_ROOTS = _collect_runtime_allowed_roots()

    _install_function_wrappers()
    _install_pathlib_wrappers()
    sys.addaudithook(_audit_hook)
    _INSTALLED = True
'''


def prepare_python_runtime_path_guard_env(
    env: MutableMapping[str, str],
    *,
    tenant_root: Path,
    base_dir: Path,
) -> tempfile.TemporaryDirectory[str]:
    """Create a temporary sitecustomize guard and inject it into env.

    The returned ``TemporaryDirectory`` must stay alive until the shell command
    and its Python descendants have exited.
    """
    # The caller owns this object so the directory survives subprocess execution.
    # pylint: disable=consider-using-with
    guard_dir = tempfile.TemporaryDirectory(prefix="swe_pyguard_")
    guard_path = Path(guard_dir.name)
    (guard_path / "swe_tenant_path_guard.py").write_text(
        _RUNTIME_GUARD_SOURCE,
        encoding="utf-8",
    )
    (guard_path / "sitecustomize.py").write_text(
        _SITE_CUSTOMIZE_SOURCE,
        encoding="utf-8",
    )

    env[_TENANT_ROOT_ENV] = str(tenant_root.resolve())
    env[_BASE_DIR_ENV] = str(base_dir.resolve())

    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        env["PYTHONPATH"] = str(guard_path) + os.pathsep + existing_pythonpath
    else:
        env["PYTHONPATH"] = str(guard_path)

    return guard_dir
