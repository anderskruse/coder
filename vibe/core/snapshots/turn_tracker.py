"""Turn-level snapshot tracking.

Tracks file changes during a single conversation turn by hooking into
tool execution rather than scanning the entire project tree.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from vibe.core.snapshots.constants import KKCODE_DIR_NAME, SNAPSHOT_DIR_NAME

logger = logging.getLogger(__name__)


def _snapshot_debug(msg: str) -> None:
    """Write debug message to a dedicated file."""
    try:
        debug_file = Path.cwd() / KKCODE_DIR_NAME / "snapshot_debug.log"
        debug_file.parent.mkdir(parents=True, exist_ok=True)
        with open(debug_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} {msg}\n")
            f.flush()
    except Exception:
        pass


class SnapshotTurnContext:
    """Tracks file changes during a single conversation turn.

    Instead of scanning the full project tree before/after each turn,
    this class hooks into tool execution via ``track_file()`` and records
    only the files that tools actually touch.
    """

    def __init__(
        self,
        snapshot_manager,
        workdir: Path,
        session_id: str,
        user_msg: str,
        message_index: int,
    ):
        self.snapshot_manager = snapshot_manager
        self.workdir = workdir
        self.session_id = session_id
        self.user_msg = user_msg
        self.message_index = message_index

        self.snapshot_dir = (
            workdir / KKCODE_DIR_NAME / SNAPSHOT_DIR_NAME / session_id / f"msg-{message_index}"
        )
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        # rel_path -> existed_before_turn
        self._tracked_files: dict[str, bool] = {}

        _snapshot_debug(
            f"[turn_tracker] SnapshotTurnContext created: msg-{message_index}"
        )

    async def track_file(self, tool_instance, args) -> None:
        """Called before tool execution to capture the before-state of a file.

        Uses ``tool_instance.get_preview()`` to determine which file the tool
        will modify, then saves a copy if the file already exists.
        """
        try:
            preview_result = await tool_instance.get_preview(args)
            if preview_result is None:
                return

            file_path, _preview_content = preview_result
            if not isinstance(file_path, Path):
                file_path = Path(file_path)

            # Determine relative path; skip files outside workdir
            try:
                rel_path = str(file_path.relative_to(self.workdir))
            except ValueError:
                return

            # Don't re-track the same file twice in one turn
            if rel_path in self._tracked_files:
                return

            existed = file_path.exists()
            self._tracked_files[rel_path] = existed

            if existed and file_path.is_file():
                dest = self.snapshot_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest)
                _snapshot_debug(f"[turn_tracker] saved before-state: {rel_path}")
            else:
                _snapshot_debug(f"[turn_tracker] new file will be created: {rel_path}")

        except Exception as e:
            _snapshot_debug(f"[turn_tracker] track_file error: {e}")
            logger.debug(f"Snapshot track_file failed: {e}")

    async def finalize(self, tool_manager=None) -> None:
        """Called in the finally block to create snapshot metadata.

        No project scanning is needed — we already know exactly which files
        were touched from ``track_file()`` calls.
        """
        try:
            from vibe.core.snapshots.types import SnapshotInfo

            # Separate created vs modified files
            created_files: list[str] = []
            modified_files: list[str] = []
            total_size = 0

            for rel_path, existed_before in self._tracked_files.items():
                if existed_before:
                    modified_files.append(rel_path)
                else:
                    created_files.append(rel_path)
                    # Save created file to snapshot so later restores can access it
                    src = self.workdir / rel_path
                    if src.exists() and src.is_file():
                        dest = self.snapshot_dir / rel_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dest)

            # Calculate total snapshot size
            for snapshot_file in self.snapshot_dir.rglob("*"):
                if snapshot_file.is_file() and snapshot_file.name != ".snapshot_metadata.json":
                    total_size += snapshot_file.stat().st_size

            # Collect all files stored in snapshot dir
            saved_files: list[str] = []
            for snapshot_file in self.snapshot_dir.rglob("*"):
                if snapshot_file.is_file() and snapshot_file.name != ".snapshot_metadata.json":
                    saved_files.append(str(snapshot_file.relative_to(self.snapshot_dir)))

            # Get current plan/todo state
            plan_todos: list[dict] = []
            plan_count = 0
            if tool_manager:
                try:
                    todo_tool = tool_manager.get("todo")
                    plan_todos = [todo.model_dump() for todo in todo_tool.state.todos]
                    plan_count = len(plan_todos)
                except Exception:
                    pass

            snapshot = SnapshotInfo(
                snapshot_id=str(uuid4()),
                session_id=self.session_id,
                message_index=self.message_index,
                user_question=self.user_msg[:150],
                timestamp=datetime.now().isoformat(),
                snapshot_path=str(self.snapshot_dir),
                created_files=sorted(created_files),
                modified_files=saved_files,
                git_commit=None,
                git_branch=None,
                git_was_dirty=False,
                total_size_bytes=total_size,
                file_count=len(saved_files),
                plan_todos=plan_todos,
                plan_count=plan_count,
            )

            # Write metadata atomically
            meta_file = self.snapshot_dir / ".snapshot_metadata.json"
            tmp_file = meta_file.with_suffix(".json.tmp")
            tmp_file.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
            tmp_file.rename(meta_file)

            self.snapshot_manager.snapshots.append(snapshot)

            _snapshot_debug(
                f"[turn_tracker] FINAL snapshot {self.message_index}: "
                f"created={sorted(created_files)}, modified={saved_files}"
            )

            if saved_files:
                logger.info(f"Created snapshot {self.message_index} with {len(saved_files)} file(s)")
            else:
                logger.info(f"Created snapshot {self.message_index} (chat only)")

        except Exception as e:
            logger.warning(f"Failed to create snapshot metadata: {e}")
            _snapshot_debug(f"[turn_tracker] finalize error: {e}")
