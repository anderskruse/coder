"""Display formatting utilities for snapshot system."""

from __future__ import annotations

from datetime import datetime

from vibe.core.snapshots.constants import PREVIEW_FILE_DISPLAY_LIMIT
from vibe.core.snapshots.types import RestorePreview, SnapshotInfo


def format_snapshot_list(snapshots: list[SnapshotInfo], current_index: int | None = None) -> str:
    """Format snapshot list for CLI display.

    Args:
        snapshots: List of snapshots
        current_index: Optional index of current position

    Returns:
        Formatted string for display
    """
    if not snapshots:
        return "No messages available for this session."

    lines = []

    for i, snapshot in enumerate(snapshots):
        # Parse timestamp
        try:
            dt = datetime.fromisoformat(snapshot.timestamp)
            time_str = dt.strftime("%H:%M:%S")
        except Exception:
            time_str = snapshot.timestamp[:8]

        # Mark current position
        marker = " ← You are here" if i == current_index else ""

        # Extract first line of user question (before \n\n)
        user_question_short = snapshot.user_question.split("\n\n")[0]

        # Indicate if snapshot has file changes or is chat-only
        has_modified = bool(snapshot.modified_files)
        has_created = bool(snapshot.created_files)
        has_files = has_modified or has_created
        type_indicator = "📁" if has_files else "💬"  # 📁 = has files, 💬 = chat only

        # Format snapshot entry
        lines.append(f"{type_indicator} {i}. [{time_str}] {user_question_short}{marker}")

        # Show modified/created files or indicate chat-only
        if has_files:
            all_changed = list(snapshot.modified_files) + [
                f"+ {f}" for f in snapshot.created_files
            ]
            files_display = ", ".join(all_changed[:5])
            if len(all_changed) > 5:
                files_display += f" (+{len(all_changed) - 5} more)"
            lines.append(f"   Files: {files_display}")
        else:
            lines.append("   (chat only - no file changes)")

        lines.append("")

    lines.append("─" * 80)
    lines.append("")
    lines.append("Legend: 📁 = has file changes, 💬 = chat only (no files)")
    lines.append("")
    lines.append("📝 Available Commands:")
    lines.append("")
    lines.append("  /restore N               → Restore both chat history and code to message N")
    lines.append("")
    lines.append("  /restore N --chat-only   → Restore only the chat history (works for all messages)")
    lines.append("")
    lines.append("  /restore N --code-only   → Restore only the code files")
    lines.append("")
    lines.append("  /restore N --preview     → Preview changes without applying them")
    lines.append("")
    lines.append("  /undo                    → Quick restore to previous message")
    lines.append("")

    return "\n".join(lines)


def format_restore_preview(preview: RestorePreview, snapshot: SnapshotInfo) -> str:
    """Format restore preview for CLI display.

    Args:
        preview: Preview information
        snapshot: Snapshot being restored

    Returns:
        Formatted string for display
    """
    lines = [
        "",
        f"Preview restore to snapshot {snapshot.message_index}",
        f"   {snapshot.user_question}",
        f"   {snapshot.timestamp}",
        "",
    ]

    if not preview.has_changes():
        lines.append("No changes - your files already match this snapshot.")
        return "\n".join(lines)

    # Files to be modified
    if preview.files_to_modify:
        lines.append(f"{len(preview.files_to_modify)} files will be modified:")
        for f in preview.files_to_modify[:PREVIEW_FILE_DISPLAY_LIMIT]:
            lines.append(f"   • {f}")
        if len(preview.files_to_modify) > PREVIEW_FILE_DISPLAY_LIMIT:
            lines.append(f"   ... and {len(preview.files_to_modify) - PREVIEW_FILE_DISPLAY_LIMIT} more")
        lines.append("")

    # Files to be deleted
    if preview.files_to_delete:
        lines.append(f"❌ {len(preview.files_to_delete)} files will be DELETED:")
        for f in preview.files_to_delete[:PREVIEW_FILE_DISPLAY_LIMIT]:
            lines.append(f"   • {f}")
        if len(preview.files_to_delete) > PREVIEW_FILE_DISPLAY_LIMIT:
            lines.append(f"   ... and {len(preview.files_to_delete) - PREVIEW_FILE_DISPLAY_LIMIT} more")
        lines.append("")

    # Unchanged files
    if preview.files_unchanged:
        lines.append(f"✓ {len(preview.files_unchanged)} files already match snapshot")
        lines.append("")

    lines.append(
        f"Total: {preview.total_files} files in snapshot"
    )
    lines.append("")

    return "\n".join(lines)


def format_size_warning(size_bytes: int, file_count: int) -> str:
    """Format warning message for large snapshots.

    Args:
        size_bytes: Total size in bytes
        file_count: Number of files

    Returns:
        Warning message
    """
    size_mb = size_bytes / (1024 * 1024)
    return (
        f"⚠️  Project is {size_mb:.0f}MB ({file_count} files). "
        f"Snapshot will use significant disk space."
    )
