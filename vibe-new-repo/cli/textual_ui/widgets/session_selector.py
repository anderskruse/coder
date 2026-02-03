"""Interactive session selector widget for resuming previous sessions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Static


VISIBLE_ITEMS = 7  # Number of visible items in the list


class SessionSelector(Container):
    """Interactive session selector with preview."""

    can_focus = True
    can_focus_children = False

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("enter", "select_session", "Resume Session", show=False),
        Binding("d", "delete_session", "Delete", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    class SessionSelected(Message):
        """Posted when user selects a session to resume."""

        def __init__(self, session: dict[str, Any]) -> None:
            super().__init__()
            self.session = session

    class DeleteRequested(Message):
        """Posted when user wants to delete a session."""

        def __init__(self, session: dict[str, Any]) -> None:
            super().__init__()
            self.session = session

    class Cancelled(Message):
        """Posted when user cancels the selection."""

        pass

    def __init__(self, sessions: list[dict[str, Any]]) -> None:
        super().__init__(id="session-selector")
        self.sessions = sessions
        self.selected_index = 0  # Start at most recent
        self.list_widgets: list[Static] = []
        self.preview_widget: Static | None = None
        self.help_widget: Static | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="session-selector-content"):
            # Title
            yield Static("Select Session to Resume", id="session-title")

            # Main content: list + preview
            with Horizontal(id="session-main"):
                # Left: Session list
                with Vertical(id="session-list-container"):
                    yield Static("Sessions:", classes="session-section-title")
                    with VerticalScroll(id="session-list-scroll"):
                        for i in range(min(VISIBLE_ITEMS, max(len(self.sessions), 1))):
                            widget = Static("", classes="session-item")
                            self.list_widgets.append(widget)
                            yield widget

                # Right: Preview
                with Vertical(id="session-preview-container"):
                    yield Static("Details:", classes="session-section-title")
                    self.preview_widget = Static("", id="session-preview")
                    yield self.preview_widget

            # Help text
            self.help_widget = Static(
                "↑↓ navigate  Enter resume  D delete  ESC cancel",
                id="session-help"
            )
            yield self.help_widget

    def on_mount(self) -> None:
        self._update_list()
        self._update_preview()
        self.focus()

    def _format_session_item(self, session: dict[str, Any], is_selected: bool) -> str:
        """Format a session for display in the list."""
        # Parse timestamp
        try:
            start_time = session.get("start_time", "")
            if start_time:
                dt = datetime.fromisoformat(start_time)
                date_str = dt.strftime("%m/%d %H:%M")
            else:
                date_str = "??/?? ??:??"
        except Exception:
            date_str = "??/?? ??:??"

        # Message count indicator
        msg_count = session.get("message_count", 0)

        # Truncate first message
        first_msg = session.get("first_message", "")[:35]
        if len(session.get("first_message", "")) > 35:
            first_msg += "..."

        # Selection cursor
        cursor = "› " if is_selected else "  "

        return f"{cursor}[{date_str}] ({msg_count} msgs) {first_msg}"

    def _update_list(self) -> None:
        """Update the session list display."""
        if not self.sessions:
            if self.list_widgets:
                self.list_widgets[0].update("  No sessions available")
            return

        # Calculate visible range (center selected item)
        total = len(self.sessions)
        visible = len(self.list_widgets)
        half = visible // 2

        # Calculate start index to center the selected item
        if total <= visible:
            start = 0
        else:
            start = max(0, min(self.selected_index - half, total - visible))

        for i, widget in enumerate(self.list_widgets):
            sess_idx = start + i
            if sess_idx < total:
                session = self.sessions[sess_idx]
                is_selected = sess_idx == self.selected_index
                text = self._format_session_item(session, is_selected)
                widget.update(text)

                # Update classes
                widget.remove_class("selected")
                if is_selected:
                    widget.add_class("selected")
            else:
                widget.update("")
                widget.remove_class("selected")

    def _update_preview(self) -> None:
        """Update the preview panel with selected session details."""
        if not self.preview_widget or not self.sessions:
            if self.preview_widget:
                self.preview_widget.update("No sessions available.")
            return

        session = self.sessions[self.selected_index]

        # Parse timestamps
        try:
            start_time = session.get("start_time", "")
            if start_time:
                dt = datetime.fromisoformat(start_time)
                start_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                start_str = "Unknown"
        except Exception:
            start_str = "Unknown"

        try:
            end_time = session.get("end_time", "")
            if end_time:
                dt = datetime.fromisoformat(end_time)
                end_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                end_str = "In progress"
        except Exception:
            end_str = "Unknown"

        # Build preview text
        lines = [
            f"Session ID: {session.get('session_id', 'unknown')[:8]}",
            f"Started: {start_str}",
            f"Ended: {end_str}",
            "",
            f"Messages: {session.get('message_count', 0)}",
            f"Snapshots: {session.get('snapshot_count', 0)}",
            "",
        ]

        # Git info
        if session.get("git_branch"):
            lines.append(f"Git branch: {session.get('git_branch')}")
            lines.append("")

        # Stats
        stats = session.get("stats", {})
        if stats:
            input_tokens = stats.get("input_tokens", 0)
            output_tokens = stats.get("output_tokens", 0)
            if input_tokens or output_tokens:
                lines.append(f"Tokens: {input_tokens:,} in / {output_tokens:,} out")
                lines.append("")

        # First message preview
        first_msg = session.get("first_message", "")
        if first_msg:
            lines.append("First message:")
            # Word wrap at ~40 chars
            words = first_msg.split()
            line = "  "
            for word in words:
                if len(line) + len(word) > 45:
                    lines.append(line)
                    line = "  " + word
                else:
                    line += " " + word if line != "  " else word
            if line.strip():
                lines.append(line)

        self.preview_widget.update("\n".join(lines))

    def action_move_up(self) -> None:
        if self.sessions and self.selected_index > 0:
            self.selected_index -= 1
            self._update_list()
            self._update_preview()

    def action_move_down(self) -> None:
        if self.sessions and self.selected_index < len(self.sessions) - 1:
            self.selected_index += 1
            self._update_list()
            self._update_preview()

    def action_select_session(self) -> None:
        """Resume selected session."""
        if self.sessions:
            self.post_message(
                self.SessionSelected(session=self.sessions[self.selected_index])
            )

    def action_delete_session(self) -> None:
        """Request deletion of selected session."""
        if self.sessions:
            self.post_message(
                self.DeleteRequested(session=self.sessions[self.selected_index])
            )

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())

    def on_blur(self, event: events.Blur) -> None:
        # Keep focus on this widget
        self.call_after_refresh(self.focus)
