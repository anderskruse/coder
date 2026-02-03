"""Core snapshot management functionality."""

from __future__ import annotations

import filecmp
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from vibe.core.snapshots.constants import (
    DEFAULT_CLEANUP_AGE_DAYS,
    DEFAULT_SIZE_WARNING_MB,
    EMERGENCY_BACKUP_PREFIX,
    KKCODE_DIR_NAME,
    SNAPSHOT_DIR_NAME,
    USER_QUESTION_MAX_LENGTH,
)
from vibe.core.snapshots.file_utils import (
    calculate_directory_size,
    copy_file_or_symlink,
    get_git_info,
    get_project_files,
)
from vibe.core.snapshots.types import RestorePreview, SnapshotInfo

logger = logging.getLogger(__name__)


class SnapshotError(Exception):
    """Raised when snapshot operations fail."""

    pass


class RestoreError(Exception):
    """Raised when restore operations fail."""

    pass


class SnapshotManager:
    """Manages file-based snapshots for session restore.

    Snapshots only store AI-modified files to minimize disk usage.
    Restore is performed by replaying all snapshots up to the target.
    Snapshots are stored in .kkcode/snapshots/<session_id>/ directory.
    """

    def __init__(
        self,
        session_id: str,
        workdir: Path,
        respect_gitignore: bool = True,
        size_warning_mb: int = DEFAULT_SIZE_WARNING_MB,
    ):
        """Initialize snapshot manager.

        Args:
            session_id: Unique session identifier
            workdir: Project working directory
            respect_gitignore: Whether to respect .gitignore
            size_warning_mb: Warn if snapshot size exceeds this (0 to disable)
        """
        self.session_id = session_id
        self.workdir = workdir
        self.respect_gitignore = respect_gitignore
        self.size_warning_mb = size_warning_mb

        # Store snapshots in project's .kkcode directory
        self.snapshot_base = workdir / KKCODE_DIR_NAME / SNAPSHOT_DIR_NAME / session_id
        self.snapshots: list[SnapshotInfo] = []

        # Load existing snapshots
        self._load_snapshots()

    def _load_snapshots(self) -> None:
        """Load snapshot metadata from filesystem."""
        if not self.snapshot_base.exists():
            return

        for snapshot_dir in sorted(self.snapshot_base.glob("msg-*")):
            meta_file = snapshot_dir / ".snapshot_metadata.json"
            if meta_file.exists():
                try:
                    data = json.loads(meta_file.read_text(encoding="utf-8"))
                    snapshot = SnapshotInfo.model_validate(data)
                    self.snapshots.append(snapshot)
                except Exception as e:
                    logger.warning(
                        f"Failed to load snapshot metadata from {meta_file}: {e}. "
                        f"This snapshot will be skipped. Consider running cleanup."
                    )

        # Sort by message index
        self.snapshots.sort(key=lambda s: s.message_index)
        logger.info(f"Loaded {len(self.snapshots)} snapshots for session {self.session_id}")

    async def create_snapshot(
        self,
        message_index: int,
        user_question: str,
        modified_files_list: list[str] | None = None,  #### KK-code altercation
        confirm_large: callable | None = None,
    ) -> SnapshotInfo | None:
        """Create a snapshot by copying AI-modified files.

        Only files modified by the AI are copied to the snapshot.
        To restore, all snapshots up to the target are replayed in order.

        Args:
            message_index: Index in message array
            user_question: User's question (will be truncated to 150 chars)
            modified_files_list: List of files modified by AI tools
            confirm_large: Optional async function to confirm large snapshots

        Returns:
            SnapshotInfo if successful, None if cancelled or no files modified
        """
        try:
            # Get complete list of files in working directory
            all_files = await get_project_files(self.workdir, self.respect_gitignore)

            if not all_files:
                logger.info("No files to snapshot - project state unchanged since last snapshot")
                return None

            #### KK-code altercation BEGIN ####
            # Get AI-modified files (can be empty for chat-only snapshots)
            files_to_copy = modified_files_list or []

            # Always create snapshot metadata, even without file changes
            # This allows users to restore chat history to any point
            logger.info(f"Creating snapshot {message_index} with {len(files_to_copy)} AI-modified files")
            #### KK-code altercation END ####

            # Calculate total size of files to copy (0 if no files)
            total_size = sum(
                (self.workdir / f).stat().st_size
                for f in files_to_copy
                if (self.workdir / f).exists()
            ) if files_to_copy else 0

            # Warn about large snapshots (skip if no files)
            if files_to_copy and self.size_warning_mb > 0 and total_size > self.size_warning_mb * 1024 * 1024:  #### KK-code altercation
                if confirm_large:
                    size_mb = total_size / (1024 * 1024)
                    confirmed = await confirm_large(size_mb, len(files_to_copy))
                    if not confirmed:
                        logger.info(f"Snapshot skipped by user (size: {size_mb:.0f}MB)")
                        return None

            # Create snapshot directory
            snapshot_id = str(uuid4())
            snapshot_path = self.snapshot_base / f"msg-{message_index}"
            snapshot_path.mkdir(parents=True, exist_ok=True)

            # Get git metadata
            git_info = await get_git_info(self.workdir)

            # Copy AI-modified files
            for rel_path in files_to_copy:
                src = self.workdir / rel_path
                dest = snapshot_path / rel_path

                try:
                    await copy_file_or_symlink(src, dest)
                except Exception as e:
                    logger.warning(f"Failed to copy {rel_path}: {e}")
                    continue

            # Create snapshot metadata
            snapshot = SnapshotInfo(
                snapshot_id=snapshot_id,
                session_id=self.session_id,
                message_index=message_index,
                user_question=user_question[:USER_QUESTION_MAX_LENGTH],
                timestamp=datetime.now().isoformat(),
                snapshot_path=str(snapshot_path),
                created_files=[],  # create_snapshot doesn't track created files
                modified_files=sorted(files_to_copy),  #### KK-code altercation
                git_commit=git_info.get("commit"),
                git_branch=git_info.get("branch"),
                git_was_dirty=git_info.get("dirty", False),
                total_size_bytes=total_size,
                file_count=len(files_to_copy),
            )

            # Write metadata atomically
            meta_file = snapshot_path / ".snapshot_metadata.json"
            tmp_file = meta_file.with_suffix(".json.tmp")
            tmp_file.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
            tmp_file.rename(meta_file)  # Atomic on POSIX

            self.snapshots.append(snapshot)
            logger.info(f"Snapshot {message_index} created successfully")

            return snapshot

        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            raise SnapshotError(f"Failed to create snapshot: {e}")

    def _get_files_to_delete(self, target_snapshot: SnapshotInfo) -> list[str]:
        """Collect files created in the target turn and all later turns.

        These files did not exist before the target turn, so restoring to
        'before that turn' means they should be deleted.

        Returns only files that currently exist on disk.
        """
        files_to_delete: set[str] = set()
        for snap in self.snapshots:
            if snap.message_index >= target_snapshot.message_index:
                files_to_delete.update(snap.created_files)
                # Backwards compat: old snapshots that used the full-repo
                # 'files' field won't have created_files populated, but
                # that's fine — they'll just contribute nothing here.
        # Only include files that actually exist right now
        return sorted(
            f for f in files_to_delete if (self.workdir / f).exists()
        )

    async def get_restore_preview(self, snapshot: SnapshotInfo) -> RestorePreview:
        """Preview what will change during a restore.

        Args:
            snapshot: Snapshot to preview

        Returns:
            RestorePreview with details of changes
        """
        snapshot_path = Path(snapshot.snapshot_path)

        if not snapshot_path.exists():
            raise RestoreError(f"Snapshot directory not found: {snapshot_path}")

        # Files created in this turn or later — they need to be deleted
        files_to_delete = self._get_files_to_delete(snapshot)

        # Check which modified files in the snapshot actually differ from current
        modified_files = []
        for snap in self.snapshots:
            if snap.message_index >= snapshot.message_index:
                snap_path = Path(snap.snapshot_path)
                for f in snap.modified_files:
                    current_file = self.workdir / f
                    snapshot_file = snap_path / f
                    if not current_file.exists() or not snapshot_file.exists():
                        continue
                    try:
                        if not filecmp.cmp(current_file, snapshot_file, shallow=False):
                            modified_files.append(f)
                    except Exception as e:
                        logger.warning(f"Failed to compare {f}: {e}")
                        modified_files.append(f)

        # Deduplicate (a file may appear in multiple snapshots)
        modified_files = sorted(set(modified_files) - set(files_to_delete))

        return RestorePreview(
            files_to_delete=files_to_delete,
            files_to_modify=modified_files,
            files_unchanged=[],
            total_files=len(files_to_delete) + len(modified_files),
        )

    async def restore_snapshot(
        self,
        snapshot: SnapshotInfo,
        preview_only: bool = False,
        confirm_restore: callable | None = None,
    ) -> RestorePreview | None:
        """Restore project to snapshot state by replaying all prior snapshots.

        Restores by applying all snapshots from the first up to the target snapshot.
        Files created after the target snapshot are deleted.

        Args:
            snapshot: Target snapshot to restore to
            preview_only: If True, only return preview without restoring
            confirm_restore: Optional async function to confirm restore

        Returns:
            RestorePreview if preview_only, None if restored successfully
        """
        snapshot_path = Path(snapshot.snapshot_path)

        if not snapshot_path.exists():
            raise RestoreError(f"Snapshot directory not found: {snapshot_path}")

        # Get preview of changes
        preview = await self.get_restore_preview(snapshot)

        if preview_only:
            return preview

        # If no changes, nothing to do
        if not preview.has_changes():
            logger.info("No changes to restore")
            return None

        # Confirm with user
        if confirm_restore:
            confirmed = await confirm_restore(preview, snapshot)
            if not confirmed:
                logger.info("Restore cancelled by user")
                return None

        # Create emergency backup before destructive operations
        emergency_backup = await self._create_emergency_backup()

        try:
            # Delete files that were created in the target turn or later
            for f in preview.files_to_delete:
                file_path = self.workdir / f
                try:
                    if file_path.exists() or file_path.is_symlink():
                        file_path.unlink()
                        logger.debug(f"Deleted created file: {f}")
                except Exception as e:
                    logger.warning(f"Failed to delete {f}: {e}")

            #### KK-code altercation BEGIN ####
            # Restore modified files from the target snapshot and later.
            # Each snapshot stores the BEFORE state of files it modified.
            # Restoring the before-state from snapshot N undoes turn N's changes.
            # We process from the target forward; earliest before-state wins
            # (a file modified in turns 3 and 5: snapshot 3's before-state is
            # the correct pre-turn-3 state).
            restored_files: set[str] = set()
            snapshots_to_undo = [
                s for s in self.snapshots
                if s.message_index >= snapshot.message_index
            ]
            snapshots_to_undo.sort(key=lambda s: s.message_index)

            deleted_set = set(preview.files_to_delete)
            logger.info(f"Undoing {len(snapshots_to_undo)} snapshots...")
            for snap in snapshots_to_undo:
                snap_path = Path(snap.snapshot_path)
                if not snap_path.exists():
                    logger.warning(f"Snapshot not found: {snap_path}")
                    continue

                logger.debug(f"  → Reverting snapshot {snap.message_index} ({len(snap.modified_files)} files)")
                for f in snap.modified_files:
                    # Skip files already restored (earliest before-state wins)
                    # and skip created files (already deleted above)
                    if f in restored_files or f in deleted_set:
                        continue

                    src = snap_path / f
                    dest = self.workdir / f

                    if not src.exists():
                        continue

                    try:
                        await copy_file_or_symlink(src, dest)
                        restored_files.add(f)
                    except Exception as e:
                        logger.warning(f"Failed to restore {f}: {e}")
            #### KK-code altercation END ####

            logger.info(f"Restored {len(restored_files)} files, deleted {len(preview.files_to_delete)} created files")
            return None

        except Exception as e:
            # Rollback on failure
            logger.error(f"Restore failed: {e}")
            logger.info("Rolling back to pre-restore state...")

            try:
                await self._restore_from_emergency_backup(emergency_backup)
                logger.info("Rollback complete")
            except Exception as rollback_error:
                logger.critical(f"Rollback failed: {rollback_error}")
                raise RestoreError(
                    f"Restore failed and rollback also failed. "
                    f"Emergency backup at: {emergency_backup}"
                )

            raise RestoreError(f"Restore failed: {e}")

        finally:
            # Clean up emergency backup
            if emergency_backup and emergency_backup.exists():
                try:
                    shutil.rmtree(emergency_backup)
                    logger.debug("Cleaned up emergency backup")
                except Exception as e:
                    logger.warning(f"Failed to clean up emergency backup: {e}")

    async def _create_emergency_backup(self) -> Path:
        """Create emergency backup before destructive restore.

        Returns:
            Path to emergency backup directory
        """
        backup_path = self.snapshot_base / f"{EMERGENCY_BACKUP_PREFIX}{uuid4().hex[:8]}"
        backup_path.mkdir(parents=True, exist_ok=True)

        files = await get_project_files(self.workdir, self.respect_gitignore)

        for f in files:
            src = self.workdir / f
            dest = backup_path / f

            if not src.exists():
                continue

            try:
                await copy_file_or_symlink(src, dest)
            except Exception as e:
                logger.warning(f"Failed to backup {f}: {e}")

        logger.debug(f"Created emergency backup at {backup_path}")
        return backup_path

    async def _restore_from_emergency_backup(self, backup_path: Path) -> None:
        """Restore from emergency backup.

        Args:
            backup_path: Path to emergency backup directory
        """
        if not backup_path.exists():
            raise RestoreError(f"Emergency backup not found: {backup_path}")

        for item in backup_path.rglob("*"):
            if item.is_file() or item.is_symlink():
                rel_path = item.relative_to(backup_path)
                dest = self.workdir / rel_path

                await copy_file_or_symlink(item, dest)

        logger.info("Restored from emergency backup")

    def get_snapshots(self) -> list[SnapshotInfo]:
        """Get list of all snapshots for this session.

        Returns:
            List of snapshots sorted by message index
        """
        return sorted(self.snapshots, key=lambda s: s.message_index)

    def get_snapshot_by_index(self, message_index: int) -> SnapshotInfo | None:
        """Get snapshot by message index.

        Args:
            message_index: Message index to find

        Returns:
            SnapshotInfo if found, None otherwise
        """
        for snapshot in self.snapshots:
            if snapshot.message_index == message_index:
                return snapshot
        return None

    async def cleanup_old_snapshots(self, max_age_days: int = DEFAULT_CLEANUP_AGE_DAYS) -> int:
        """Clean up snapshots older than specified days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of snapshots deleted
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=max_age_days)
        deleted = 0

        for snapshot in list(self.snapshots):
            try:
                snapshot_time = datetime.fromisoformat(snapshot.timestamp)
                if snapshot_time < cutoff:
                    snapshot_path = Path(snapshot.snapshot_path)
                    if snapshot_path.exists():
                        shutil.rmtree(snapshot_path)
                        self.snapshots.remove(snapshot)
                        deleted += 1
                        logger.info(f"Deleted old snapshot: {snapshot.message_index}")
            except Exception as e:
                logger.warning(f"Failed to delete snapshot {snapshot.message_index}: {e}")

        return deleted

    def delete_snapshots_after(self, message_index: int) -> int:
        """Delete all snapshots after the given message index.

        Used when restoring to a previous point - later snapshots become invalid.

        Args:
            message_index: Delete snapshots with index > this value

        Returns:
            Number of snapshots deleted
        """
        deleted = 0
        snapshots_to_delete = [
            s for s in self.snapshots if s.message_index > message_index
        ]

        for snapshot in snapshots_to_delete:
            try:
                snapshot_path = Path(snapshot.snapshot_path)
                if snapshot_path.exists():
                    shutil.rmtree(snapshot_path)
                self.snapshots.remove(snapshot)
                deleted += 1
                logger.info(f"Deleted snapshot {snapshot.message_index} (after restore to {message_index})")
            except Exception as e:
                logger.warning(f"Failed to delete snapshot {snapshot.message_index}: {e}")

        return deleted
