from __future__ import annotations

from datetime import datetime
import getpass
import json
import logging  #### KK-code altercation
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING, Any

from vibe.core.snapshots.constants import KKCODE_DIR_NAME, SESSION_LOG_DIR_NAME

import aiofiles

from vibe.core.llm.format import get_active_tool_classes
from vibe.core.types import AgentStats, LLMMessage, SessionInfo, SessionMetadata
from vibe.core.utils import is_windows

if TYPE_CHECKING:
    from vibe.core.config import SessionLoggingConfig, VibeConfig
    from vibe.core.tools.manager import ToolManager


#### KK-code altercation ####
logger = logging.getLogger(__name__)


class InteractionLogger:
    def __init__(
        self,
        session_config: SessionLoggingConfig,
        session_id: str,
        auto_approve: bool = False,
        workdir: Path | None = None,
    ) -> None:
        if workdir is None:
            workdir = Path.cwd()
        self.session_config = session_config
        self.enabled = session_config.enabled
        self.auto_approve = auto_approve
        self.workdir = workdir

        if not self.enabled:
            self.save_dir: Path | None = None
            self.session_prefix: str | None = None
            self.session_id: str = "disabled"
            self.session_start_time: str = "N/A"
            self.filepath: Path | None = None
            self.session_metadata: SessionMetadata | None = None
            return

        #### KK-code altercation BEGIN ####
        # Use project-local storage by default instead of global
        from vibe.core.paths.global_paths import SESSION_LOG_DIR

        configured_save_dir = Path(session_config.save_dir)

        # If using default global location, switch to project-local
        if str(configured_save_dir) == str(SESSION_LOG_DIR.path):
            self.save_dir = workdir / KKCODE_DIR_NAME / SESSION_LOG_DIR_NAME
            logger.debug(f"Using project-local session logs: {self.save_dir}")
        else:
            # User explicitly configured a custom location, respect it
            self.save_dir = configured_save_dir
        #### KK-code altercation END ####

        self.session_prefix = session_config.session_prefix
        self.session_id = session_id
        self.session_start_time = datetime.now().isoformat()

        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.filepath = self._get_save_filepath()
        self.session_metadata = self._initialize_session_metadata()

    def _get_save_filepath(self) -> Path:
        if self.save_dir is None or self.session_prefix is None:
            raise RuntimeError("Cannot get filepath when logging is disabled")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.session_prefix}_{timestamp}_{self.session_id[:8]}.json"
        return self.save_dir / filename

    def _get_git_commit(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                cwd=self.workdir,
                stdin=subprocess.DEVNULL if is_windows() else None,
                text=True,
                timeout=5.0,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            pass
        return None

    def _get_git_branch(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                cwd=self.workdir,
                stdin=subprocess.DEVNULL if is_windows() else None,
                text=True,
                timeout=5.0,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            pass
        return None

    def _get_username(self) -> str:
        try:
            return getpass.getuser()
        except Exception:
            return "unknown"

    def _initialize_session_metadata(self) -> SessionMetadata:
        git_commit = self._get_git_commit()
        git_branch = self._get_git_branch()
        user_name = self._get_username()

        return SessionMetadata(
            session_id=self.session_id,
            start_time=self.session_start_time,
            end_time=None,
            git_commit=git_commit,
            git_branch=git_branch,
            auto_approve=self.auto_approve,
            username=user_name,
            environment={"working_directory": str(self.workdir)},
        )

    async def save_interaction(
        self,
        messages: list[LLMMessage],
        stats: AgentStats,
        config: VibeConfig,
        tool_manager: ToolManager,
        snapshot_manager=None,  #### KK-code altercation
    ) -> str | None:
        if not self.enabled or self.filepath is None:
            return None

        if self.session_metadata is None:
            return None

        #### KK-code altercation BEGIN ####
        # Update snapshot count in metadata
        if snapshot_manager:
            self.session_metadata.snapshot_count = len(snapshot_manager.get_snapshots())
        #### KK-code altercation END ####

        active_tools = get_active_tool_classes(tool_manager, config)

        tools_available = [
            {
                "type": "function",
                "function": {
                    "name": tool_class.get_name(),
                    "description": tool_class.description,
                    "parameters": tool_class.get_parameters(),
                },
            }
            for tool_class in active_tools
        ]

        interaction_data = {
            "metadata": {
                **self.session_metadata.model_dump(),
                "end_time": datetime.now().isoformat(),
                "stats": stats.model_dump(),
                "total_messages": len(messages),
                "tools_available": tools_available,
                "agent_config": config.model_dump(mode="json"),
            },
            "messages": [m.model_dump(exclude_none=True) for m in messages],
        }

        try:
            json_content = json.dumps(interaction_data, indent=2, ensure_ascii=False)

            async with aiofiles.open(self.filepath, "w", encoding="utf-8") as f:
                await f.write(json_content)

            return str(self.filepath)
        except Exception as e:
            logger.exception(f"Failed to save interaction log to {self.filepath}: {e}")
            return None

    def reset_session(self, session_id: str) -> None:
        if not self.enabled:
            return

        self.session_id = session_id
        self.session_start_time = datetime.now().isoformat()
        self.filepath = self._get_save_filepath()
        self.session_metadata = self._initialize_session_metadata()

    def get_session_info(
        self, messages: list[dict[str, Any]], stats: AgentStats
    ) -> SessionInfo:
        if not self.enabled or self.save_dir is None:
            return SessionInfo(
                session_id="disabled",
                start_time="N/A",
                message_count=len(messages),
                stats=stats,
                save_dir="N/A",
            )

        return SessionInfo(
            session_id=self.session_id,
            start_time=self.session_start_time,
            message_count=len(messages),
            stats=stats,
            save_dir=str(self.save_dir),
        )

    @staticmethod
    def find_latest_session(config: SessionLoggingConfig, workdir: Path | None = None) -> Path | None:  #### KK-code altercation
        #### KK-code altercation BEGIN ####
        # Use project-local storage by default
        from vibe.core.paths.global_paths import SESSION_LOG_DIR

        configured_save_dir = Path(config.save_dir)

        # If using default global location, switch to project-local
        if str(configured_save_dir) == str(SESSION_LOG_DIR.path) and workdir:
            save_dir = workdir / ".kkcode" / "logs" / "session"
        else:
            save_dir = configured_save_dir
        #### KK-code altercation END ####

        if not save_dir.exists():
            return None

        pattern = f"{config.session_prefix}_*.json"
        session_files = list(save_dir.glob(pattern))

        if not session_files:
            return None

        return max(session_files, key=lambda p: p.stat().st_mtime)

    @staticmethod
    def find_session_by_id(
        session_id: str, config: SessionLoggingConfig, workdir: Path | None = None  #### KK-code altercation
    ) -> Path | None:
        #### KK-code altercation BEGIN ####
        # Use project-local storage by default
        from vibe.core.paths.global_paths import SESSION_LOG_DIR

        configured_save_dir = Path(config.save_dir)

        # If using default global location, switch to project-local
        if str(configured_save_dir) == str(SESSION_LOG_DIR.path) and workdir:
            save_dir = workdir / ".kkcode" / "logs" / "session"
        else:
            save_dir = configured_save_dir
        #### KK-code altercation END ####

        if not save_dir.exists():
            return None

        # If it's a full UUID, extract the short form (first 8 chars)
        short_id = session_id.split("-")[0] if "-" in session_id else session_id

        # Try exact match first, then partial
        patterns = [
            f"{config.session_prefix}_*_{short_id}.json",  # Exact short UUID
            f"{config.session_prefix}_*_{short_id}*.json",  # Partial UUID
        ]

        for pattern in patterns:
            matches = list(save_dir.glob(pattern))
            if matches:
                return (
                    max(matches, key=lambda p: p.stat().st_mtime)
                    if len(matches) > 1
                    else matches[0]
                )

        return None

    @staticmethod
    def load_session(filepath: Path) -> tuple[list[LLMMessage], dict[str, Any]]:
        with filepath.open("r", encoding="utf-8") as f:
            content = f.read()

        data = json.loads(content)
        messages = [LLMMessage.model_validate(msg) for msg in data.get("messages", [])]
        metadata = data.get("metadata", {})

        return messages, metadata

    #### KK-code altercation BEGIN ####
    @staticmethod
    def list_sessions(config: SessionLoggingConfig, workdir: Path | None = None) -> list[dict[str, Any]]:
        """List all available sessions with their metadata.

        Args:
            config: Session logging configuration
            workdir: Working directory for project-local sessions

        Returns:
            List of session info dicts sorted by modification time (newest first)
        """
        from vibe.core.paths.global_paths import SESSION_LOG_DIR

        configured_save_dir = Path(config.save_dir)

        # If using default global location, switch to project-local
        if str(configured_save_dir) == str(SESSION_LOG_DIR.path) and workdir:
            save_dir = workdir / KKCODE_DIR_NAME / SESSION_LOG_DIR_NAME
        else:
            save_dir = configured_save_dir

        if not save_dir.exists():
            return []

        pattern = f"{config.session_prefix}_*.json"
        session_files = list(save_dir.glob(pattern))

        if not session_files:
            return []

        sessions = []
        for filepath in session_files:
            try:
                with filepath.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                metadata = data.get("metadata", {})
                messages = data.get("messages", [])

                # Extract first user message as summary
                first_user_msg = ""
                for msg in messages:
                    if msg.get("role") == "user":
                        content = msg.get("content", "")
                        if isinstance(content, str):
                            first_user_msg = content[:100]
                        elif isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    first_user_msg = item.get("text", "")[:100]
                                    break
                        break

                sessions.append({
                    "filepath": filepath,
                    "session_id": metadata.get("session_id", "unknown"),
                    "start_time": metadata.get("start_time", ""),
                    "end_time": metadata.get("end_time", ""),
                    "message_count": metadata.get("total_messages", len(messages)),
                    "git_branch": metadata.get("git_branch"),
                    "first_message": first_user_msg,
                    "snapshot_count": metadata.get("snapshot_count", 0),
                    "stats": metadata.get("stats", {}),
                    "mtime": filepath.stat().st_mtime,
                })
            except Exception as e:
                logger.debug(f"Failed to read session file {filepath}: {e}")
                continue

        # Sort by modification time (newest first)
        sessions.sort(key=lambda s: s["mtime"], reverse=True)
        return sessions
    #### KK-code altercation END ####
