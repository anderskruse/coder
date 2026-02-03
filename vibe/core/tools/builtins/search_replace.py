from __future__ import annotations

import difflib
import inspect
from pathlib import Path
import re
import shutil
from typing import ClassVar, NamedTuple, final

import aiofiles
from pydantic import BaseModel, Field

from vibe.core.tools.base import BaseTool, BaseToolConfig, BaseToolState, ToolError
from vibe.core.tools.ui import ToolCallDisplay, ToolResultDisplay, ToolUIData
from vibe.core.types import ToolCallEvent, ToolResultEvent

SEARCH_REPLACE_BLOCK_RE = re.compile(
    r"<{3,}\s*SEARCH\s*\r?\n(.*?)\r?\n?={3,}\s*\r?\n(.*?)\r?\n?>{3,}\s*REPLACE\s*", flags=re.DOTALL
)

SEARCH_REPLACE_BLOCK_WITH_FENCE_RE = re.compile(
    r"```[\s\S]*?\n<{3,}\s*SEARCH\s*\r?\n(.*?)\r?\n?={3,}\s*\r?\n(.*?)\r?\n?>{3,}\s*REPLACE\s*\n```",
    flags=re.DOTALL,
)

# XML format for Qwen models
XML_SEARCH_REPLACE_BLOCK_RE = re.compile(
    r"<search_replace>\s*<search>(.*?)</search>\s*<replace>(.*?)</replace>\s*</search_replace>",
    flags=re.DOTALL,
)

# XML format with code fence
XML_SEARCH_REPLACE_BLOCK_WITH_FENCE_RE = re.compile(
    r"```(?:xml)?\s*\n<search_replace>\s*<search>(.*?)</search>\s*<replace>(.*?)</replace>\s*</search_replace>\s*\n```",
    flags=re.DOTALL,
)


class SearchReplaceBlock(NamedTuple):
    search: str
    replace: str


class FuzzyMatch(NamedTuple):
    similarity: float
    start_line: int
    end_line: int
    text: str


class BlockApplyResult(NamedTuple):
    content: str
    applied: int
    errors: list[str]
    warnings: list[str]


#### KK-code altercation BEGIN ####
class SearchReplaceArgs(BaseModel):
    file_path: str
    content: str | None = None
    old_string: str | None = None
    new_string: str | None = None
#### KK-code altercation END ####


class SearchReplaceResult(BaseModel):
    file: str
    blocks_applied: int
    lines_changed: int
    content: str
    warnings: list[str] = Field(default_factory=list)


class SearchReplaceConfig(BaseToolConfig):
    max_content_size: int = 100_000
    create_backup: bool = False
    fuzzy_threshold: float = 0.9


class SearchReplaceState(BaseToolState):
    pass


class SearchReplace(
    BaseTool[
        SearchReplaceArgs, SearchReplaceResult, SearchReplaceConfig, SearchReplaceState
    ],
    ToolUIData[SearchReplaceArgs, SearchReplaceResult],
):
#### KK-code altercation BEGIN ####
    description: ClassVar[str] = (
        "Replace sections of files. Supports multiple formats based on model preference.\n\n"
        "Format 1 (Standard - Mistral/Codestral):\n"
        "Use `content` with SEARCH/REPLACE blocks:\n"
        "<<<<<<< SEARCH\n[exact text]\n=======\n[replacement]\n>>>>>>> REPLACE\n\n"
        "Format 2 (Atomic - Qwen):\n"
        "Use `old_string` and `new_string` arguments directly. "
        "`old_string` must match exactly with sufficient context.\n\n"
        "Format 3 (XML):\n"
        "Use `content` with <search_replace> tags."
    )
#### KK-code altercation END ####

    @classmethod
    def get_tool_prompt(cls, active_model: str | None = None, model_config: Any = None) -> str | None:
        """Return model-specific prompt for search_replace tool.

        Uses model_config.tool_format to determine which format to use.
        Defaults to STANDARD format if not specified.
        """
        from vibe.core.config import ToolFormat

        # Get tool_format from model_config, default to STANDARD
        tool_format = ToolFormat.STANDARD
        if model_config and hasattr(model_config, 'tool_format'):
            tool_format = model_config.tool_format

        #### KK-code altercation BEGIN ####
        if tool_format == ToolFormat.ATOMIC:
            return cls._load_prompt_file("search_replace_atomic.md")
        elif tool_format == ToolFormat.XML:
        #### KK-code altercation END ####
            return cls._load_prompt_file("search_replace_xml.md")
        else:
            return cls._load_prompt_file("search_replace_standard.md")

    @classmethod
    def _load_prompt_file(cls, filename: str) -> str | None:
        """Load a specific prompt file from the prompts directory."""
        try:
            class_file = inspect.getfile(cls)
            class_path = Path(class_file)
            prompt_dir = class_path.parent / "prompts"
            prompt_path = prompt_dir / filename
            return prompt_path.read_text("utf-8")
        except (FileNotFoundError, TypeError, OSError):
            return None

    @classmethod
    def get_call_display(cls, event: ToolCallEvent) -> ToolCallDisplay:
        if not isinstance(event.args, SearchReplaceArgs):
            return ToolCallDisplay(summary="Invalid arguments")

        args = event.args
        #### KK-code altercation BEGIN ####
        if args.old_string is not None:
            # Atomic format
            old_s = args.old_string
            new_s = args.new_string if args.new_string is not None else ""
            summary = f"Replacing text in {args.file_path}"
            if not old_s and new_s:
                summary = f"Creating/Appending to {args.file_path}"
            elif old_s and not new_s:
                summary = f"Deleting text from {args.file_path}"
            
            content_display = f"<<<<<<< SEARCH\n{old_s}\n=======\n{new_s}\n>>>>>>> REPLACE"
            return ToolCallDisplay(summary=summary, content=content_display)
        #### KK-code altercation END ####
        
        # Block format
        blocks = cls._parse_search_replace_blocks(args.content or "")
        return ToolCallDisplay(
            summary=f"Patching {args.file_path} ({len(blocks)} blocks)",
            content=args.content or "",
        )

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        if isinstance(event.result, SearchReplaceResult):
            return ToolResultDisplay(
                success=True,
                message=f"Applied {event.result.blocks_applied} block{'' if event.result.blocks_applied == 1 else 's'}",
                warnings=event.result.warnings,
            )

        return ToolResultDisplay(success=True, message="Patch applied")

    @classmethod
    def get_status_text(cls) -> str:
        return "Editing files"

    @final
    async def run(self, args: SearchReplaceArgs) -> SearchReplaceResult:
        file_path, search_replace_blocks = self._prepare_and_validate_args(args)

        original_content = await self._read_file(file_path)

        block_result = self._apply_blocks(
            original_content,
            search_replace_blocks,
            file_path,
            self.config.fuzzy_threshold,
        )

        if block_result.errors:
            error_message = "SEARCH/REPLACE blocks failed:\n" + "\n\n".join(
                block_result.errors
            )
            if block_result.warnings:
                error_message += "\n\nWarnings encountered:\n" + "\n".join(
                    block_result.warnings
                )
            raise ToolError(error_message)

        modified_content = block_result.content

        # Calculate line changes
        if modified_content == original_content:
            lines_changed = 0
        else:
            original_lines = len(original_content.splitlines())
            new_lines = len(modified_content.splitlines())
            lines_changed = new_lines - original_lines

            try:
                if self.config.create_backup:
                    await self._backup_file(file_path)
            except Exception:
                pass

            await self._write_file(file_path, modified_content)

        # Construct content for result
        #### KK-code altercation BEGIN ####
        if args.old_string is not None:
             content_used = f"<<<<<<< SEARCH\n{args.old_string}\n=======\n{args.new_string or ''}\n>>>>>>> REPLACE"
        else:
        #### KK-code altercation END ####
             content_used = args.content or ""

        return SearchReplaceResult(
            file=str(file_path),
            blocks_applied=block_result.applied,
            lines_changed=lines_changed,
            warnings=block_result.warnings,
            content=content_used,
        )

    #### KK-code altercation BEGIN #####
    @final
    async def get_preview(self, args: SearchReplaceArgs) -> tuple[Path, str] | None:
        """Generate preview of what the file will look like after applying changes.

        This is used for showing diffs before approval. Returns (file_path, preview_content)
        or None if preview cannot be generated.
        """
        try:
            # Prepare and validate arguments (same as run())
            file_path, search_replace_blocks = self._prepare_and_validate_args(args)

            # Read the original file content
            original_content = await self._read_file(file_path)

            # Apply blocks to generate preview (without writing to disk)
            block_result = self._apply_blocks(
                original_content,
                search_replace_blocks,
                file_path,
                self.config.fuzzy_threshold,
            )

            # If there are errors, we can't generate a reliable preview
            if block_result.errors:
                return None

            # Return the file path and the preview content
            return (file_path, block_result.content)

        except Exception:
            # If preview generation fails, return None (approval will work without preview)
            return None
    #### KK-code altercation END #####

    @final
    def _prepare_and_validate_args(
        self, args: SearchReplaceArgs
    ) -> tuple[Path, list[SearchReplaceBlock]]:
        file_path_str = args.file_path.strip()
        
        if not file_path_str:
            raise ToolError("File path cannot be empty")
        
        #### KK-code altercation BEGIN ####
        # 1. Handle Atomic Format (old_string / new_string)
        if args.old_string is not None:
            if args.content:
                raise ToolError("Cannot specify both `content` and `old_string`/`new_string`.")
            
            # Treat empty new_string as deletion (empty string)
            new_str = args.new_string if args.new_string is not None else ""
            
            # Note: We treat old_string="" as a "create new file" request or "append" request 
            # if we wanted to mimic opencode strictly, but here we just pass it as a block.
            # Ideally, empty old_string implies we are matching "nothing" to insert "something".
            # The _apply_blocks logic might need adjustment if we want to support file creation/append
            # via empty old_string, but `_read_file` would fail if file doesn't exist.
            # For now, let's assume the file exists and we are doing a replacement.
            # If the user wants to create a file, they usually use write_file tool or we handle it here.
            # For now, we map it to a Block.
            
            search_replace_blocks = [SearchReplaceBlock(search=args.old_string, replace=new_str)]
            
        # 2. Handle Block Format (content)
        elif args.content:
        #### KK-code altercation END ####
             content = args.content.strip()
             if len(content) > self.config.max_content_size:
                raise ToolError(
                    f"Content size ({len(content)} bytes) exceeds max_content_size "
                    f"({self.config.max_content_size} bytes)"
                )
             if not content:
                raise ToolError("Empty content provided")
             
             search_replace_blocks = self._parse_search_replace_blocks(content)
             if not search_replace_blocks:
                raise ToolError(
                    "No valid SEARCH/REPLACE blocks found in content.\n\n"
                    "Expected format (Standard):\n"
                    "<<<<<<< SEARCH\n"
                    "[exact content to find]\n"
                    "=======\n"
                    "[new content to replace with]\n"
                    ">>>>>>> REPLACE\n\n"
                    "OR (XML format):\n"
                    "<search_replace>\n"
                    "  <search>[exact content to find]</search>\n"
                    "  <replace>[new content to replace with]</replace>\n"
                    "</search_replace>"
                )
        else:
             raise ToolError("Must provide either `content` or `old_string`.")


        project_root = self.config.effective_workdir
        file_path = Path(file_path_str).expanduser()
        if not file_path.is_absolute():
            file_path = project_root / file_path
        file_path = file_path.resolve()
        
        # Check existence - NOTE: If we want to support file creation via empty old_string,
        # we might need to relax this check. But standard search_replace requires file to exist.
        if not file_path.exists():
             # If using atomic mode and old_string is empty, maybe allow creation?
             # For now, let's stick to existing behavior: file must exist.
            raise ToolError(f"File does not exist: {file_path}")

        if not file_path.is_file():
            raise ToolError(f"Path is not a file: {file_path}")

        return file_path, search_replace_blocks

    async def _read_file(self, file_path: Path) -> str:
        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                return await f.read()
        except UnicodeDecodeError as e:
            raise ToolError(f"Unicode decode error reading {file_path}: {e}") from e
        except PermissionError:
            raise ToolError(f"Permission denied reading file: {file_path}")
        except Exception as e:
            raise ToolError(f"Unexpected error reading {file_path}: {e}") from e

    async def _backup_file(self, file_path: Path) -> None:
        shutil.copy2(file_path, file_path.with_suffix(file_path.suffix + ".bak"))

    async def _write_file(self, file_path: Path, content: str) -> None:
        try:
            async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
                await f.write(content)
        except PermissionError:
            raise ToolError(f"Permission denied writing to file: {file_path}")
        except OSError as e:
            raise ToolError(f"OS error writing to {file_path}: {e}") from e
        except Exception as e:
            raise ToolError(f"Unexpected error writing to {file_path}: {e}") from e

    @final
    @staticmethod
    def _apply_blocks(
        content: str,
        blocks: list[SearchReplaceBlock],
        filepath: Path,
        fuzzy_threshold: float = 0.9,
    ) -> BlockApplyResult:
        applied = 0
        errors: list[str] = []
        warnings: list[str] = []
        current_content = content

        for i, (search, replace) in enumerate(blocks, 1):
            if search not in current_content:
                context = SearchReplace._find_search_context(current_content, search)
                fuzzy_context = SearchReplace._find_fuzzy_match_context(
                    current_content, search, fuzzy_threshold
                )

                error_msg = (
                    f"SEARCH/REPLACE block {i} failed: Search text not found in {filepath}\n"
                    f"Search text was:\n{search!r}\n"
                    f"Context analysis:\n{context}"
                )

                if fuzzy_context:
                    error_msg += f"\n{fuzzy_context}"

                error_msg += (
                    "\nDebugging tips:\n"
                    "1. Check for exact whitespace/indentation match\n"
                    "2. Verify line endings match the file exactly (\\r\\n vs \\n)\n"
                    "3. Ensure the search text hasn't been modified by previous blocks or user edits\n"
                    "4. Check for typos or case sensitivity issues"
                )

                errors.append(error_msg)
                continue

            occurrences = current_content.count(search)
            if occurrences > 1:
                warning_msg = (
                    f"Search text in block {i} appears {occurrences} times in the file. "
                    f"Only the first occurrence will be replaced. Consider making your "
                    f"search pattern more specific to avoid unintended changes."
                )
                warnings.append(warning_msg)

            current_content = current_content.replace(search, replace, 1)
            applied += 1

        return BlockApplyResult(
            content=current_content, applied=applied, errors=errors, warnings=warnings
        )

    @final
    @staticmethod
    def _find_fuzzy_match_context(
        content: str, search_text: str, threshold: float = 0.9
    ) -> str | None:
        best_match = SearchReplace._find_best_fuzzy_match(
            content, search_text, threshold
        )

        if not best_match:
            return None

        diff = SearchReplace._create_unified_diff(
            search_text, best_match.text, "SEARCH", "CLOSEST MATCH"
        )

        similarity_pct = best_match.similarity * 100

        return (
            f"Closest fuzzy match (similarity {similarity_pct:.1f}%) "
            f"at lines {best_match.start_line}–{best_match.end_line}:\n"
            f"```diff\n{diff}\n```"
        )

    @final
    @staticmethod
    def _find_best_fuzzy_match(  # noqa: PLR0914
        content: str, search_text: str, threshold: float = 0.9
    ) -> FuzzyMatch | None:
        content_lines = content.split("\n")
        search_lines = search_text.split("\n")
        window_size = len(search_lines)

        if window_size == 0:
            return None

        non_empty_search = [line for line in search_lines if line.strip()]
        if not non_empty_search:
            return None

        first_anchor = non_empty_search[0]
        last_anchor = (
            non_empty_search[-1] if len(non_empty_search) > 1 else first_anchor
        )

        candidate_starts = set()
        spread = 5

        for i, line in enumerate(content_lines):
            if first_anchor in line or last_anchor in line:
                start_min = max(0, i - spread)
                start_max = min(len(content_lines) - window_size + 1, i + spread + 1)
                for s in range(start_min, start_max):
                    candidate_starts.add(s)

        if not candidate_starts:
            max_positions = min(len(content_lines) - window_size + 1, 100)
            candidate_starts = set(range(0, max_positions))

        best_match = None
        best_similarity = 0.0

        for start in candidate_starts:
            end = start + window_size
            window_text = "\n".join(content_lines[start:end])

            matcher = difflib.SequenceMatcher(None, search_text, window_text)
            similarity = matcher.ratio()

            if similarity >= threshold and similarity > best_similarity:
                best_similarity = similarity
                best_match = FuzzyMatch(
                    similarity=similarity,
                    start_line=start + 1,  # 1-based line numbers
                    end_line=end,
                    text=window_text,
                )

        return best_match

    @final
    @staticmethod
    def _create_unified_diff(
        text1: str, text2: str, label1: str = "SEARCH", label2: str = "CLOSEST MATCH"
    ) -> str:
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)

        lines1 = [line if line.endswith("\n") else line + "\n" for line in lines1]
        lines2 = [line if line.endswith("\n") else line + "\n" for line in lines2]

        diff = difflib.unified_diff(
            lines1, lines2, fromfile=label1, tofile=label2, lineterm="", n=3
        )

        diff_lines = list(diff)

        if diff_lines and not diff_lines[0].startswith("==="):
            diff_lines.insert(2, "=" * 67 + "\n")

        result = "".join(diff_lines)

        max_chars = 2000
        if len(result) > max_chars:
            result = result[:max_chars] + "\n...(diff truncated)"

        return result.rstrip()

    @final
    @staticmethod
    def _parse_search_replace_blocks(content: str) -> list[SearchReplaceBlock]:
        """Parse SEARCH/REPLACE blocks from content.

        Supports multiple formats:
        1. Standard with fence: ```...<<<<<<< SEARCH...```
        2. Standard without fence: <<<<<<< SEARCH...
        3. XML with fence: ```xml<search_replace>...```
        4. XML without fence: <search_replace><search>...</search><replace>...</replace></search_replace>
        """
        # Try fenced formats first
        matches = SEARCH_REPLACE_BLOCK_WITH_FENCE_RE.findall(content)

        if not matches:
            matches = XML_SEARCH_REPLACE_BLOCK_WITH_FENCE_RE.findall(content)

        # Try standard format without fence
        if not matches:
            matches = SEARCH_REPLACE_BLOCK_RE.findall(content)

        # Try XML format without fence (for Qwen models)
        if not matches:
            matches = XML_SEARCH_REPLACE_BLOCK_RE.findall(content)

        return [
            SearchReplaceBlock(
                search=search.rstrip("\r\n"), replace=replace.rstrip("\r\n")
            )
            for search, replace in matches
        ]

    @final
    @staticmethod
    def _find_search_context(
        content: str, search_text: str, max_context: int = 5
    ) -> str:
        lines = content.split("\n")
        search_lines = search_text.split("\n")

        if not search_lines:
            return "Search text is empty"

        first_search_line = search_lines[0].strip()
        if not first_search_line:
            return "First line of search text is empty or whitespace only"

        matches = []
        for i, line in enumerate(lines):
            if first_search_line in line:
                matches.append(i)

        if not matches:
            return f"First search line '{first_search_line}' not found anywhere in file"

        context_lines = []
        for match_idx in matches[:3]:
            start = max(0, match_idx - max_context)
            end = min(len(lines), match_idx + max_context + 1)

            context_lines.append(f"\nPotential match area around line {match_idx + 1}:")
            for i in range(start, end):
                marker = ">>>" if i == match_idx else "   "
                context_lines.append(f"{marker} {i + 1:3d}: {lines[i]}")

        return "\n".join(context_lines)
