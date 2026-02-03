"""Interactive message selector widget for restore functionality."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Static

from vibe.core.snapshots.types import SnapshotInfo


VISIBLE_ITEMS = 7  # Number of visible items in the list


class SnapshotSelector(Container):
    """Interactive message selector with preview."""

    can_focus = True
    can_focus_children = False

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("enter", "select_full", "Restore All", show=False),
        Binding("c", "select_chat", "Chat Only", show=False),
        Binding("f", "select_files", "Files Only", show=False),
        Binding("p", "preview", "Preview", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    class RestoreRequested(Message):
        """Posted when user requests a restore."""

        def __init__(
            self,
            snapshot: SnapshotInfo,
            mode: str,  # "full", "chat", "files", "preview"
        ) -> None:
            super().__init__()
            self.snapshot = snapshot
            self.mode = mode

    class Cancelled(Message):
        """Posted when user cancels the selection."""

        pass

    def __init__(self, snapshots: list[SnapshotInfo], current_message_index: int) -> None:
        super().__init__(id="snapshot-selector")
        self.snapshots = snapshots
        self.current_message_index = current_message_index
        self.selected_index = len(snapshots) - 1 if snapshots else 0  # Start at most recent
        self.list_widgets: list[Static] = []
        self.preview_widget: Static | None = None
        self.help_widget: Static | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="snapshot-selector-content"):
            # Title
            yield Static("Select Message to Restore", id="snapshot-title")

            # Main content: list + preview
            with Horizontal(id="snapshot-main"):
                # Left: Message list
                with Vertical(id="snapshot-list-container"):
                    yield Static("Messages:", classes="snapshot-section-title")
                    with VerticalScroll(id="snapshot-list-scroll"):
                        for i in range(min(VISIBLE_ITEMS, max(len(self.snapshots), 1))):
                            widget = Static("", classes="snapshot-item")
                            self.list_widgets.append(widget)
                            yield widget

                # Right: Preview
                with Vertical(id="snapshot-preview-container"):
                    yield Static("Details:", classes="snapshot-section-title")
                    self.preview_widget = Static("", id="snapshot-preview")
                    yield self.preview_widget

            # Help text
            self.help_widget = Static(
                "↑↓ navigate  Enter restore  C chat-only  F files-only  P preview  ESC cancel",
                id="snapshot-help"
            )
            yield self.help_widget

    def on_mount(self) -> None:
        self._update_list()
        self._update_preview()
        self.focus()

    def _format_snapshot_item(self, snapshot: SnapshotInfo, is_selected: bool) -> str:
        """Format a snapshot for display in the list."""
        # Parse timestamp
        try:
            dt = datetime.fromisoformat(snapshot.timestamp)
            time_str = dt.strftime("%H:%M")
        except Exception:
            time_str = snapshot.timestamp[:5]

        # Type indicator
        has_files = bool(snapshot.modified_files)
        icon = "📁" if has_files else "💬"

        # Truncate question
        question = snapshot.user_question.split("\n\n")[0][:40]
        if len(snapshot.user_question.split("\n\n")[0]) > 40:
            question += "..."

        # Selection cursor
        cursor = "› " if is_selected else "  "

        return f"{cursor}{icon} {snapshot.message_index}. [{time_str}] {question}"

    def _update_list(self) -> None:
        """Update the message list display."""
        if not self.snapshots:
            if self.list_widgets:
                self.list_widgets[0].update("  No messages available")
            return

        # Calculate visible range (center selected item)
        total = len(self.snapshots)
        visible = len(self.list_widgets)
        half = visible // 2

        # Calculate start index to center the selected item
        if total <= visible:
            start = 0
        else:
            start = max(0, min(self.selected_index - half, total - visible))

        for i, widget in enumerate(self.list_widgets):
            snap_idx = start + i
            if snap_idx < total:
                snapshot = self.snapshots[snap_idx]
                is_selected = snap_idx == self.selected_index
                text = self._format_snapshot_item(snapshot, is_selected)
                widget.update(text)

                # Update classes
                widget.remove_class("selected", "has-files", "chat-only")
                if is_selected:
                    widget.add_class("selected")
                if snapshot.modified_files:
                    widget.add_class("has-files")
                else:
                    widget.add_class("chat-only")
            else:
                widget.update("")
                widget.remove_class("selected", "has-files", "chat-only")

    def _update_preview(self) -> None:
        """Update the preview panel with selected message details."""
        if not self.preview_widget or not self.snapshots:
            if self.preview_widget:
                self.preview_widget.update("No messages available.")
            return

        snapshot = self.snapshots[self.selected_index]

        # Parse timestamp
        try:
            dt = datetime.fromisoformat(snapshot.timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            time_str = snapshot.timestamp

        # Build preview text
        lines = [
            f"Message: {snapshot.message_index}",
            f"Time: {time_str}",
            "",
            "Question:",
            f"  {snapshot.user_question.split(chr(10) + chr(10))[0][:80]}",
            "",
        ]

        # File info
        if snapshot.modified_files:
            lines.append(f"Files modified: {len(snapshot.modified_files)}")
            for f in snapshot.modified_files[:8]:
                lines.append(f"  • {f}")
            if len(snapshot.modified_files) > 8:
                lines.append(f"  ... +{len(snapshot.modified_files) - 8} more")
        else:
            lines.append("Files: None (chat only)")

        # Git info
        if snapshot.git_branch:
            lines.append("")
            lines.append(f"Git: {snapshot.git_branch}")
            if snapshot.git_commit:
                lines.append(f"      {snapshot.git_commit[:8]}")

        self.preview_widget.update("\n".join(lines))

    def action_move_up(self) -> None:
        if self.snapshots and self.selected_index > 0:
            self.selected_index -= 1
            self._update_list()
            self._update_preview()

    def action_move_down(self) -> None:
        if self.snapshots and self.selected_index < len(self.snapshots) - 1:
            self.selected_index += 1
            self._update_list()
            self._update_preview()

    def action_select_full(self) -> None:
        """Restore both chat and files."""
        if self.snapshots:
            self.post_message(
                self.RestoreRequested(
                    snapshot=self.snapshots[self.selected_index],
                    mode="full"
                )
            )

    def action_select_chat(self) -> None:
        """Restore chat only."""
        if self.snapshots:
            self.post_message(
                self.RestoreRequested(
                    snapshot=self.snapshots[self.selected_index],
                    mode="chat"
                )
            )

    def action_select_files(self) -> None:
        """Restore files only."""
        if self.snapshots:
            snapshot = self.snapshots[self.selected_index]
            if not snapshot.modified_files:
                # Can't restore files from a chat-only snapshot
                return
            self.post_message(
                self.RestoreRequested(
                    snapshot=snapshot,
                    mode="files"
                )
            )

    def action_preview(self) -> None:
        """Show preview of what would be restored."""
        if self.snapshots:
            self.post_message(
                self.RestoreRequested(
                    snapshot=self.snapshots[self.selected_index],
                    mode="preview"
                )
            )

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())

    def on_blur(self, event: events.Blur) -> None:
        # Keep focus on this widget
        self.call_after_refresh(self.focus)
