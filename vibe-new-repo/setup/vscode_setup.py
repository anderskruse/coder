from __future__ import annotations

import shutil
import sys
from pathlib import Path

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()

# VS Code expects folder name: publisher.name-version
EXTENSION_PUBLISHER = "kkcode"
EXTENSION_NAME = "kk-code-vsc"
EXTENSION_VERSION = "1.0.0"
EXTENSION_FOLDER = f"{EXTENSION_PUBLISHER}.{EXTENSION_NAME}-{EXTENSION_VERSION}"


def is_wsl() -> bool:
    """Check if running in WSL."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


def get_extensions_dir(editor_cmd: str) -> Path | None:
    """Get the VS Code/Cursor extensions directory."""
    home = Path.home()

    if sys.platform == "win32":
        if editor_cmd == "cursor":
            extensions_dir = home / ".cursor" / "extensions"
        else:
            extensions_dir = home / ".vscode" / "extensions"
    elif sys.platform == "darwin":
        if editor_cmd == "cursor":
            extensions_dir = home / ".cursor" / "extensions"
        else:
            extensions_dir = home / ".vscode" / "extensions"
    else:  # Linux
        if editor_cmd == "cursor":
            extensions_dir = home / ".cursor-server" / "extensions" if is_wsl() else home / ".cursor" / "extensions"
        else:
            # WSL uses .vscode-server, native Linux uses .vscode
            extensions_dir = home / ".vscode-server" / "extensions" if is_wsl() else home / ".vscode" / "extensions"

    return extensions_dir


def check_vscode_installed() -> tuple[bool, str | None]:
    """Check if VS Code or Cursor is installed."""
    if shutil.which("code"):
        return True, "code"

    if shutil.which("cursor"):
        return True, "cursor"

    return False, None


def get_extension_source_dir() -> Path:
    """Get the path to the bundled extension source."""
    # The extension is in vibe/vsc/ relative to this file
    setup_dir = Path(__file__).parent
    vibe_dir = setup_dir.parent
    return vibe_dir / "vsc"


def install_extension(editor_cmd: str) -> bool:
    """Install the internal KK-Code extension."""
    try:
        extensions_dir = get_extensions_dir(editor_cmd)
        if not extensions_dir:
            rprint("[red]Could not determine extensions directory[/]")
            return False

        # Create extensions directory if it doesn't exist
        extensions_dir.mkdir(parents=True, exist_ok=True)

        # Extension destination (VS Code expects: publisher.name-version)
        ext_dest = extensions_dir / EXTENSION_FOLDER

        # Get source directory
        ext_source = get_extension_source_dir()

        if not ext_source.exists():
            rprint(f"[red]Extension source not found at {ext_source}[/]")
            return False

        # Remove existing installation if present
        if ext_dest.exists():
            rprint("[dim]Removing existing installation...[/]")
            shutil.rmtree(ext_dest)

        # Copy extension files
        rprint(f"[blue]Installing extension to {ext_dest}...[/]")
        shutil.copytree(ext_source, ext_dest)

        rprint("[green]Extension installed successfully![/]")
        return True

    except PermissionError:
        rprint("[red]Permission denied. Try running with elevated privileges.[/]")
        return False
    except Exception as e:
        rprint(f"[red]Error installing extension: {e}[/]")
        return False


def uninstall_extension(editor_cmd: str) -> bool:
    """Uninstall the internal KK-Code extension."""
    try:
        extensions_dir = get_extensions_dir(editor_cmd)
        if not extensions_dir:
            return False

        ext_dest = extensions_dir / EXTENSION_FOLDER

        if ext_dest.exists():
            shutil.rmtree(ext_dest)
            rprint("[green]Extension uninstalled successfully![/]")
            return True
        else:
            rprint("[yellow]Extension not found.[/]")
            return False

    except Exception as e:
        rprint(f"[red]Error uninstalling extension: {e}[/]")
        return False


def show_usage_instructions() -> None:
    """Show instructions for using the extension."""
    instructions = """[bold cyan]KK-Code VSC Installed[/]

The extension is now active and will:

[bold]Features:[/]
- Open diff views without stealing focus from your terminal
- Automatically close diff tabs when changes are approved/rejected
- Watch for commands from KK-Code CLI

[bold]How it works:[/]
The extension watches for command files in [cyan].kkcode/.vscode-commands/[/]
KK-Code CLI writes commands there, and the extension executes them.

[bold]Restart Required:[/]
Please restart VS Code/Cursor to activate the extension.
"""

    console.print(Panel(instructions, border_style="cyan", padding=(1, 2)))


def main() -> None:
    """Main setup function for VS Code integration."""
    console.print(
        Panel.fit(
            "[bold cyan]KK-Code VS Code Setup[/]\n\n"
            "This will install the KK-Code VSC extension.\n"
            "It enables opening diffs without stealing focus from terminal.",
            border_style="cyan",
        )
    )

    # Check if VS Code/Cursor is installed
    is_installed, editor_cmd = check_vscode_installed()

    if not is_installed:
        rprint(
            "\n[yellow]VS Code or Cursor not found on your system.[/]\n"
            "[dim]Please install VS Code or Cursor first, or make sure the 'code' "
            "or 'cursor' command is in your PATH.[/]"
        )
        sys.exit(1)

    editor_name = "Cursor" if editor_cmd == "cursor" else "VS Code"
    rprint(f"\n[green]{editor_name} detected[/]")

    # Ask for confirmation
    if not Confirm.ask(
        f"\nInstall internal KK-Code extension for {editor_name}?", default=True
    ):
        rprint("\n[yellow]Setup cancelled.[/]")
        sys.exit(0)

    # Install extension
    success = install_extension(editor_cmd)

    if success:
        show_usage_instructions()
    else:
        rprint(
            "\n[red]Failed to install extension.[/]\n"
            "[dim]Please check the error messages above.[/]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
