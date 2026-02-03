from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path
from uuid import uuid4

import aiofiles  # For async file I/O in preview diff #### KK-code altercation

from vibe.core.config import EditorConfig

logger = logging.getLogger(__name__)

# Extension folder name (VS Code format: publisher.name-version)
EXTENSION_FOLDER = "kkcode.kk-code-vsc-1.0.0"


class DiffManager:
    """Manages automatic diff opening for file edits."""

    def __init__(self, config: EditorConfig, workdir: Path):
        self.config = config
        self.workdir = workdir
        self.editor_command = (
            self._detect_editor() if config.auto_detect else config.command
        )
        self.temp_backups: dict[str, Path] = {}  # Maps file_path -> backup_path

        self.preview_files: dict[str, Path] = {}  # Maps file_path -> preview_path for cleanup #### KK-code altercation

        self.cleanup_tasks: list[asyncio.Task] = []

    def _detect_editor(self) -> str | None:
        """Detect VS Code or Cursor installation."""
        if shutil.which("code"):
            return "code"
        if shutil.which("cursor"):
            return "cursor"
        return None

    def _is_wsl(self) -> bool:
        """Check if running in WSL."""
        try:
            with open("/proc/version", "r") as f:
                return "microsoft" in f.read().lower()
        except Exception:
            return False

    def _is_extension_installed(self) -> bool:
        """Check if the KK-Code VSC extension is installed."""
        from pathlib import Path

        home = Path.home()
        is_wsl = self._is_wsl()

        # Determine extensions directory based on editor and platform
        if self.editor_command == "cursor":
            extensions_dir = home / ".cursor-server" / "extensions" if is_wsl else home / ".cursor" / "extensions"
        else:
            # WSL uses .vscode-server, native Linux uses .vscode
            extensions_dir = home / ".vscode-server" / "extensions" if is_wsl else home / ".vscode" / "extensions"

        ext_path = extensions_dir / EXTENSION_FOLDER
        return ext_path.exists()

    async def _send_extension_command(self, command: dict) -> bool:
        """Send a command to the VS Code extension via file.

        Args:
            command: Dict with 'action' and other parameters

        Returns:
            True if command was written successfully
        """
        try:
            # Create commands directory
            commands_dir = self.workdir / ".kkcode" / ".vscode-commands"
            commands_dir.mkdir(parents=True, exist_ok=True)

            # Write command file with unique name
            command_file = commands_dir / f"{uuid4().hex[:8]}.json"

            async with aiofiles.open(command_file, mode="w", encoding="utf-8") as f:
                await f.write(json.dumps(command))

            logger.debug(f"Sent extension command: {command['action']}")
            return True

        except Exception as e:
            logger.debug(f"Failed to send extension command: {e}")
            return False

    async def create_backup(self, file_path: Path) -> Path | None:
        """Create a temporary backup before file modification."""
        if not self.config.enabled or not self.config.open_diffs:
            return None

        if not file_path.exists():
            return None  # No backup needed for new files

        try:
            # Create temp dir in same location as file
            temp_dir = file_path.parent / ".kkcode_backups"
            temp_dir.mkdir(exist_ok=True)

            # Unique backup filename
            backup_path = temp_dir / f"{file_path.name}.{uuid4().hex[:8]}.bak"
            shutil.copy2(file_path, backup_path)

            self.temp_backups[str(file_path)] = backup_path
            return backup_path
        except Exception as e:
            logger.debug(f"Failed to create backup for {file_path}: {e}")
            return None

    async def open_diff(self, file_path: Path, backup_path: Path | None = None) -> bool:
        """Open diff window in VS Code/Cursor."""
        if not self.config.enabled or not self.config.open_diffs:
            return False

        if not self.editor_command:
            return False

        if backup_path is None:
            backup_path = self.temp_backups.get(str(file_path))

        if not backup_path or not backup_path.exists():
            return False

        try:
            # Try extension first (preserves focus), fall back to CLI
            if self._is_extension_installed():
                await self._send_extension_command({
                    "action": "open-diff",
                    "leftPath": str(backup_path),
                    "rightPath": str(file_path),
                    "title": f"Changes: {file_path.name}",
                })
            else:
                # Fallback to direct CLI (will steal focus)
                await asyncio.create_subprocess_exec(
                    self.editor_command,
                    "--diff",
                    str(backup_path),
                    str(file_path),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )

            # Schedule cleanup
            self._schedule_cleanup(backup_path)

            logger.debug(f"Opened diff for {file_path}")
            return True
        except Exception as e:
            logger.debug(f"Failed to open diff: {e}")
            return False

    #### KK-code altercation BEGIN #####
    async def open_preview_diff(self, file_path: Path, preview_content: str) -> bool:
        """Open diff window showing current file vs proposed changes.

        This is called BEFORE tool execution to let the user review changes before approval.

        Args:
            file_path: Path to the file being modified
            preview_content: What the file will look like after the change

        Returns:
            True if diff was opened successfully, False otherwise
        """
        if not self.config.enabled or not self.config.open_diffs:
            return False

        if not self.editor_command:
            return False

        try:
            # Check if file exists FIRST, before any async operations that yield to event loop
            is_new_file = not file_path.exists()
            # debug_log = self.workdir / ".kkcode" / "debug.log"
            # debug_log.parent.mkdir(parents=True, exist_ok=True)
            # with open(debug_log, "a") as dbg:
            #     dbg.write(f"DEBUG open_preview_diff: file_path={file_path}, is_new_file={is_new_file}\n")

            # Create centralized preview directory in .kkcode/.previews
            temp_dir = self.workdir / ".kkcode" / ".previews"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Create preview file with unique name
            preview_path = temp_dir / f"{file_path.name}.{uuid4().hex[:8]}.preview"

            # Write the preview content to the temp file using async I/O (aiofiles)
            async with aiofiles.open(preview_path, mode="w", encoding="utf-8") as f:
                await f.write(preview_content)

            # Small delay to ensure filesystem has flushed the write
            await asyncio.sleep(0.1)

            # Store the preview path for cleanup after approval/rejection
            self.preview_files[str(file_path)] = preview_path

            # For new files, create an empty temp file for the left side
            # VS Code doesn't handle non-existent files well in diff view
            left_path = file_path
            empty_file_path: Path | None = None
            if is_new_file:
                empty_file_path = temp_dir / f"{file_path.name}.{uuid4().hex[:8]}.empty"
                # with open(debug_log, "a") as dbg:
                #     dbg.write(f"DEBUG: Creating empty file at {empty_file_path}\n")
                # Use synchronous touch() - no need for async for empty file
                empty_file_path.touch()
                # with open(debug_log, "a") as dbg:
                #     dbg.write(f"DEBUG: Empty file created: {empty_file_path.exists()}\n")
                left_path = empty_file_path
            # else:
                # with open(debug_log, "a") as dbg:
                #     dbg.write(f"DEBUG: File exists, not creating empty file\n")

            # Try extension first (preserves focus), fall back to CLI
            if self._is_extension_installed():
                await self._send_extension_command({
                    "action": "open-diff",
                    "leftPath": str(left_path),
                    "rightPath": str(preview_path),
                    "title": f"{'New: ' if empty_file_path else 'Preview: '}{file_path.name}",
                })
            else:
                # Fallback to direct CLI (will steal focus)
                await asyncio.create_subprocess_exec(
                    self.editor_command,
                    "--diff",
                    str(left_path),  # Current file or empty file (left side)
                    str(preview_path),  # Preview file (right side)
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )

            # Schedule cleanup of empty file if created
            if empty_file_path:
                self._schedule_cleanup(empty_file_path)

            # DON'T schedule time-based cleanup for preview files
            # They will be cleaned up after approval/rejection via cleanup_preview_file()

            logger.debug(f"Opened preview diff for {file_path}")
            return True

        except Exception as e:
            logger.debug(f"Failed to open preview diff: {e}")
            return False

    async def cleanup_preview_file(self, file_path: Path) -> None:
        """Clean up preview file for a given file path after approval/rejection.

        This also closes the diff tab in VS Code if extension is installed.

        Args:
            file_path: Path to the file that was being previewed
        """
        try:
            preview_path = self.preview_files.get(str(file_path))
            if preview_path:
                # Close the diff tab via extension (if installed)
                if self._is_extension_installed():
                    await self._send_extension_command({
                        "action": "close-diff",
                        "previewPath": str(preview_path),
                    })
                    # Small delay to let extension close the tab before we delete the file
                    await asyncio.sleep(0.1)

                # Delete the preview file if it exists
                if preview_path.exists():
                    preview_path.unlink()

                # Clean up empty preview directory (.kkcode/.previews)
                if preview_path.parent.name == ".previews":
                    try:
                        preview_path.parent.rmdir()
                        # Also try to clean up .kkcode if empty
                        if preview_path.parent.parent.name == ".kkcode":
                            try:
                                preview_path.parent.parent.rmdir()
                            except OSError:
                                pass  # Directory not empty
                    except OSError:
                        pass  # Directory not empty or other issue

                # Remove from tracking dict
                del self.preview_files[str(file_path)]
                logger.debug(f"Cleaned up preview file for {file_path}")
        except Exception as e:
            logger.debug(f"Failed to clean up preview file for {file_path}: {e}")
    #### KK-code altercation END #####

    def _schedule_cleanup(self, backup_path: Path) -> None:
        """Schedule deletion of backup file after delay."""

        async def cleanup_later():
            await asyncio.sleep(self.config.diff_cleanup_delay)
            try:
                if backup_path.exists():
                    backup_path.unlink()
                # Clean up empty backup directory
                if backup_path.parent.name == ".kkcode_backups":
                    try:
                        backup_path.parent.rmdir()
                    except OSError:
                        pass
            except Exception:
                pass

        task = asyncio.create_task(cleanup_later())
        self.cleanup_tasks.append(task)
