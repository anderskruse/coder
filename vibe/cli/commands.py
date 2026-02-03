from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Command:
    aliases: frozenset[str]
    description: str
    handler: str
    exits: bool = False


class CommandRegistry:
    def __init__(self, excluded_commands: list[str] | None = None) -> None:
        if excluded_commands is None:
            excluded_commands = []
        self.commands = {
            "help": Command(
                aliases=frozenset(["/help"]),
                description="Show help message",
                handler="_show_help",
            ),
            #### KK-code altercation BEGIN ####
            "messages": Command(
                aliases=frozenset(["/messages"]),
                description="List all saved messages for current session",
                handler="_show_snapshots",
            ),
            "sessions": Command(
                aliases=frozenset(["/sessions"]),
                description="List and resume previous sessions",
                handler="_show_sessions",
            ),
            #### KK-code altercation END ####
            "config": Command(
                aliases=frozenset(["/config", "/theme", "/model"]),
                description="Edit config settings",
                handler="_show_config",
            ),
            "exit": Command(
                aliases=frozenset(["/exit"]),
                description="Exit the application",
                handler="_exit_app",
                exits=True,
            ),
            "reload": Command(
                aliases=frozenset(["/reload"]),
                description="Reload configuration from disk",
                handler="_reload_config",
            ),
            "clear": Command(
                aliases=frozenset(["/clear"]),
                description="Clear conversation history",
                handler="_clear_history",
            ),
            "log": Command(
                aliases=frozenset(["/log"]),
                description="Show path to current interaction log file",
                handler="_show_log_path",
            ),
            "compact": Command(
                aliases=frozenset(["/compact"]),
                description="Compact conversation history by summarizing",
                handler="_compact_history",
            ),
            "terminal-setup": Command(
                aliases=frozenset(["/terminal-setup"]),
                description="Configure Shift+Enter for newlines",
                handler="_setup_terminal",
            ),
            "status": Command(
                aliases=frozenset(["/status"]),
                description="Display agent statistics",
                handler="_show_status",
            ),
            #### KK-code altercation BEGIN ####
            "restore": Command(
                aliases=frozenset(["/restore"]),
                description="Restore to a previous message (usage: /restore <N> [--code-only|--chat-only|--preview])",
                handler="_restore_snapshot",
            ),
            "undo": Command(
                aliases=frozenset(["/undo"]),
                description="Undo last change (restore to previous message)",
                handler="_undo_last",
            ),
            #### KK-code altercation END ####
        }

        for command in excluded_commands:
            self.commands.pop(command, None)

        self._alias_map = {}
        for cmd_name, cmd in self.commands.items():
            for alias in cmd.aliases:
                self._alias_map[alias] = cmd_name

    def find_command(self, user_input: str) -> Command | None:
        #### KK-code altercation BEGIN ####
        # Extract the first token (command) from user input to allow commands with arguments
        first_token = user_input.lower().strip().split()[0] if user_input.strip() else ""
        cmd_name = self._alias_map.get(first_token)
        #### KK-code altercation END ####
        return self.commands.get(cmd_name) if cmd_name else None

    def get_help_text(self) -> str:
        lines: list[str] = [
            "### Keyboard Shortcuts",
            "",
            "- `Enter` Submit message",
            "- `Ctrl+J` / `Shift+Enter` Insert newline",
            "- `Escape` Interrupt agent or close dialogs",
            "- `Ctrl+C` Quit (or clear input if text present)",
            "- `Ctrl+O` Toggle tool output view",
            "- `Ctrl+T` Toggle todo view",
            "- `Shift+Tab` Toggle auto-approve mode",
            "",
            "### Special Features",
            "",
            "- `!<command>` Execute bash command directly",
            "- `@path/to/file/` Autocompletes file paths",
            "",
            "### Commands",
            "",
        ]

        for cmd in self.commands.values():
            aliases = ", ".join(f"`{alias}`" for alias in sorted(cmd.aliases))
            lines.append(f"- {aliases}: {cmd.description}")
        return "\n".join(lines)
