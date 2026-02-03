"""Type definitions for snapshot system."""

from __future__ import annotations

from pydantic import BaseModel


class SnapshotInfo(BaseModel):
    """Metadata for a single snapshot.

    Snapshots only store AI-modified files (delta approach).
    To restore, replay all snapshots up to the target snapshot.
    """

    # Identity
    snapshot_id: str  # UUID
    session_id: str  # Parent session
    message_index: int  # Position in message array

    # User context
    user_question: str  # First 150 chars of question
    timestamp: str  # ISO format

    # Storage
    snapshot_path: str  # Absolute path to snapshot directory
    files: list[str] = []  # Deprecated: kept for backwards compat with old snapshots
    created_files: list[str] = []  # Files created during this turn (to delete on restore)

    #### KK-code altercation ####
    modified_files: list[str] = []  # AI-modified files actually stored in this snapshot

    # Git metadata (for display only)
    git_commit: str | None = None  # HEAD at snapshot time
    git_branch: str | None = None  # Current branch
    git_was_dirty: bool = False  # Had uncommitted changes?

    # Stats
    total_size_bytes: int = 0  # Total size of snapshot
    file_count: int = 0  # Number of files
    
    # Plan/Todo state (for restoration)
    plan_todos: list[dict] = []  # Todo items at this snapshot
    plan_count: int = 0  # Number of todo items


class RestorePreview(BaseModel):
    """Preview of what will change during a restore operation."""

    files_to_delete: list[str]  # Files that exist now but not in snapshot
    files_to_modify: list[str]  # Files that will be overwritten
    files_unchanged: list[str]  # Files that already match snapshot
    total_files: int  # Total files in snapshot

    def has_changes(self) -> bool:
        """Check if restore would actually change anything."""
        return len(self.files_to_delete) > 0 or len(self.files_to_modify) > 0
