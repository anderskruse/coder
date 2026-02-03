"""File operation utilities for snapshot system."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
from pathlib import Path

from vibe.core.snapshots.constants import KKCODE_DIR_NAME
from vibe.core.utils import is_windows

logger = logging.getLogger(__name__)


async def get_project_files(workdir: Path, respect_gitignore: bool = True) -> list[str]:
    """Get all project files, optionally respecting .gitignore.

    Args:
        workdir: Project working directory
        respect_gitignore: Whether to respect .gitignore (if git repo)

    Returns:
        List of relative file paths
    """
    if (workdir / ".git").exists() and respect_gitignore:
        # Use git to respect .gitignore
        return await _get_git_files(workdir)
    else:
        # Not a git repo or ignoring .gitignore - use manual traversal
        return await _get_files_manual(workdir)


async def _get_git_files(workdir: Path) -> list[str]:
    """Get files using git (respects .gitignore)."""
    try:
        # Get tracked files
        tracked_proc = await asyncio.create_subprocess_exec(
            "git",
            "ls-files",
            cwd=workdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL if is_windows() else None,
        )
        tracked_out, _ = await tracked_proc.communicate()

        # Get untracked files (excluding ignored)
        untracked_proc = await asyncio.create_subprocess_exec(
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            cwd=workdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL if is_windows() else None,
        )
        untracked_out, _ = await untracked_proc.communicate()

        files = set()
        for line in tracked_out.decode("utf-8").split("\n"):
            if line.strip():
                files.add(line.strip())
        for line in untracked_out.decode("utf-8").split("\n"):
            if line.strip():
                files.add(line.strip())

        return sorted(files)

    except Exception as e:
        logger.warning(f"Failed to get git files, falling back to manual: {e}")
        return await _get_files_manual(workdir)


async def _get_files_manual(workdir: Path) -> list[str]:
    """Get files manually, respecting .vibeignore."""
    files = []
    ignore_patterns = _load_ignore_patterns(workdir)

    for item in workdir.rglob("*"):
        if item.is_file() or item.is_symlink():
            rel_path = item.relative_to(workdir)

            # Skip if matches ignore patterns
            if _should_ignore(rel_path, ignore_patterns):
                continue

            files.append(str(rel_path))

    return sorted(files)


def _load_ignore_patterns(workdir: Path) -> list[str]:
    """Load ignore patterns from .vibeignore file."""
    ignore_file = workdir / ".vibeignore"

    # Default patterns
    patterns = [
        ".git/",
        f"{KKCODE_DIR_NAME}/",
        ".venv/",
        "venv/",
        "env/",
        "node_modules/",
        "__pycache__/",
        ".pytest_cache/",
        ".mypy_cache/",
        ".tox/",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".DS_Store",
        "Thumbs.db",
    ]

    if ignore_file.exists():
        try:
            content = ignore_file.read_text()
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
        except Exception as e:
            logger.warning(f"Failed to read .vibeignore: {e}")

    return patterns


def _should_ignore(path: Path, patterns: list[str]) -> bool:
    """Check if path matches any ignore pattern."""
    path_str = str(path)

    for pattern in patterns:
        # Directory pattern
        if pattern.endswith("/"):
            if any(part == pattern.rstrip("/") for part in path.parts):
                return True
        # Wildcard pattern
        elif "*" in pattern:
            import fnmatch

            if fnmatch.fnmatch(path_str, pattern):
                return True
        # Exact match
        elif path_str == pattern or path_str.startswith(pattern + "/"):
            return True

    return False


async def copy_file_or_symlink(src: Path, dest: Path) -> None:
    """Copy file or symlink, preserving type.

    Args:
        src: Source path
        dest: Destination path
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    if src.is_symlink():
        # Preserve symlink
        link_target = os.readlink(src)
        if dest.exists() or dest.is_symlink():
            dest.unlink()
        dest.symlink_to(link_target)
        logger.debug(f"Copied symlink: {src} -> {link_target}")
    else:
        # Regular file - copy without following symlinks
        shutil.copy2(src, dest, follow_symlinks=False)


async def get_git_info(workdir: Path) -> dict[str, str | bool]:
    """Get current git metadata.

    Returns:
        Dict with keys: commit, branch, dirty
    """
    info = {"commit": None, "branch": None, "dirty": False}

    if not (workdir / ".git").exists():
        return info

    try:
        # Get commit hash
        proc = await asyncio.create_subprocess_exec(
            "git",
            "rev-parse",
            "HEAD",
            cwd=workdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL if is_windows() else None,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            info["commit"] = stdout.decode("utf-8").strip()

        # Get branch name
        proc = await asyncio.create_subprocess_exec(
            "git",
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
            cwd=workdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL if is_windows() else None,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            info["branch"] = stdout.decode("utf-8").strip()

        # Check if dirty
        proc = await asyncio.create_subprocess_exec(
            "git",
            "status",
            "--porcelain",
            cwd=workdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL if is_windows() else None,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            info["dirty"] = bool(stdout.decode("utf-8").strip())

    except Exception as e:
        logger.debug(f"Failed to get git info: {e}")

    return info


def calculate_directory_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
    except Exception as e:
        logger.warning(f"Failed to calculate directory size: {e}")
    return total
