"""Initialize project directory structure for Vibe/KK-code."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_kkcode_directory(workdir: Path, auto_create: bool = True) -> bool:
    """Ensure .kkcode directory exists in project root.

    Creates the .kkcode directory and adds it to .gitignore if needed.

    Args:
        workdir: Project working directory
        auto_create: If True, create automatically. If False, return status only.

    Returns:
        True if .kkcode exists or was created, False if it doesn't exist
    """
    kkcode_dir = workdir / ".kkcode"

    # Check if .kkcode exists but is not a directory
    if kkcode_dir.exists() and not kkcode_dir.is_dir():
        logger.warning(f".kkcode exists but is not a directory: {kkcode_dir}")
        return False

    # Return early if auto_create is disabled and directory doesn't exist
    if not auto_create and not kkcode_dir.exists():
        return False

    try:
        # Create .kkcode directory if needed
        if not kkcode_dir.exists():
            kkcode_dir.mkdir(parents=False, exist_ok=True)
            logger.info(f"Created .kkcode directory: {kkcode_dir}")

        # Always ensure README exists (even if directory already existed)
        _create_kkcode_readme(kkcode_dir)

        # Always ensure .gitignore entry exists
        _ensure_gitignore_entry(workdir)

        return True

    except Exception as e:
        logger.error(f"Failed to initialize .kkcode directory: {e}")
        return False


def _create_kkcode_readme(kkcode_dir: Path) -> None:
    """Create README.md in .kkcode directory explaining its purpose.

    Args:
        kkcode_dir: Path to .kkcode directory
    """
    readme_path = kkcode_dir / "README.md"

    # Don't overwrite existing README
    if readme_path.exists():
        return

    readme_content = """# .kkcode-mappe

Denne mappe er oprettet og bruges af **KK-code** til lokale sessionsdata.

## Indhold

- `snapshots/` - Sessions-snapshots til fortryd/gendan-funktionalitet
  - Hver session har sin egen undermappe med AI-modificerede filkopier
  - Gør det muligt at gendanne koden til tidligere tilstande

- `logs/` - Logs over sessionsinteraktioner (valgfrit, hvis konfigureret til projekt-lokal lagring)
  - Fuld samtalshistorik med metadata
  - Bruges til at genoptage sessioner

- `config.toml` - Projektspecifik konfiguration (valgfrit)
  - Overskriver globale indstillinger for dette projekt

## NB

**Denne mappe bør være i `.gitignore`** - den indeholder lokale udviklingsdata.

**Sikker at slette** - denne mappe kan fjernes for at rydde lokale sessionsdata.
   Din kildekode bliver aldrig påvirket.
"""

    try:
        readme_path.write_text(readme_content, encoding="utf-8")
        logger.debug(f"Created README in .kkcode: {readme_path}")
    except Exception as e:
        logger.warning(f"Failed to create .kkcode README: {e}")


def _ensure_gitignore_entry(workdir: Path) -> None:
    """Ensure .kkcode is in .gitignore.

    Args:
        workdir: Project working directory
    """
    gitignore_path = workdir / ".gitignore"

    # Check if .gitignore exists
    if not gitignore_path.exists():
        # Create new .gitignore with .kkcode entry
        try:
            gitignore_path.write_text(
                "# KK-code / Vibe local data\n.kkcode/\n",
                encoding="utf-8"
            )
            logger.info("Created .gitignore with .kkcode entry")
        except Exception as e:
            logger.warning(f"Failed to create .gitignore: {e}")
        return

    # Read existing .gitignore
    try:
        content = gitignore_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read .gitignore: {e}")
        return

    # Check if .kkcode is already in .gitignore
    lines = content.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped in [".kkcode", ".kkcode/", "/.kkcode", "/.kkcode/"]:
            # Already present
            return

    # Add .kkcode to .gitignore
    try:
        # Add with newline if file doesn't end with one
        new_content = content
        if not content.endswith("\n"):
            new_content += "\n"

        new_content += "\n# KK-code / Vibe local data\n.kkcode/\n"

        gitignore_path.write_text(new_content, encoding="utf-8")
        logger.info("Added .kkcode/ to .gitignore")

    except Exception as e:
        logger.warning(f"Failed to update .gitignore: {e}")


def prompt_create_kkcode_directory(workdir: Path) -> bool:
    """Prompt user to create .kkcode directory.

    This is used in interactive mode when .kkcode doesn't exist
    and we're in a new/untrusted directory.

    Args:
        workdir: Project working directory

    Returns:
        True if user confirms, False otherwise
    """
    # This is a placeholder for interactive prompting
    # The actual UI integration will call this and show a dialog
    # For now, we return True (auto-create) since we're always in trusted folders
    return True


def initialize_project_structure(workdir: Path, trusted: bool = True) -> bool:
    """Initialize project directory structure.

    Creates .kkcode directory and ensures proper .gitignore setup.

    Args:
        workdir: Project working directory
        trusted: Whether the directory is trusted (auto-create if True)

    Returns:
        True if initialization succeeded
    """
    #### KK-code altercation ####
    # Always create .kkcode in trusted directories
    if trusted:
        return ensure_kkcode_directory(workdir, auto_create=True)

    # For untrusted directories, prompt first
    if prompt_create_kkcode_directory(workdir):
        return ensure_kkcode_directory(workdir, auto_create=True)

    return False
