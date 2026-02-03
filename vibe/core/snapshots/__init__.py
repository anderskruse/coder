"""Snapshot management for session history and code restore functionality.

This module provides git-aware snapshot capabilities that allow users to:
- Automatically snapshot before each user question
- Restore both chat history and code to previous states
- Preview changes before restoring
- Separate restore of chat vs code

Snapshots are stored in the project's .kkcode/snapshots/ directory.
"""

from vibe.core.snapshots.snapshot_manager import SnapshotManager
from vibe.core.snapshots.types import RestorePreview, SnapshotInfo

__all__ = [
    "SnapshotManager",
    "SnapshotInfo",
    "RestorePreview",
]
