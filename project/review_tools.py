"""Read-only file tools the review agent can call.

The model chooses every path and glob pattern, so each one is resolved and
checked against the review target before anything is read.
"""

import glob
import json
import re
from pathlib import Path

MAX_FILES = 100
MAX_LINES = 500
MAX_MATCHES = 50

# Stable order and content keep the prompt cache prefix identical between calls.
TOOLS = [
    {
        "name": "list_files",
        "description": (
            "List files in a directory. Use this first to understand what files exist "
            "in the review target. Returns file paths relative to the target."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list. Use '.' for the review target root.",
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter files, e.g. '*.py' or '**/*.js'",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read the contents of a file. Returns the file content with line numbers. "
            "Use this to review code in a file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read, relative to the review target.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_pattern",
        "description": (
            "Search for a regex pattern across files. Use this to find specific code "
            "patterns like 'eval(', 'SELECT.*FROM', hardcoded passwords, or to trace "
            "how a function is used."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for"},
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern to limit which files to search, e.g. '*.py'",
                },
            },
            "required": ["pattern"],
        },
    },
]


def _error(message: str) -> str:
    return json.dumps({"error": message})


class ReviewTarget:
    """A file or directory under review. Nothing outside it can be read."""

    def __init__(self, target: str):
        resolved = Path(target).resolve()
        self.single_file = resolved if resolved.is_file() else None
        self.root = resolved.parent if self.single_file else resolved

    def allows(self, path: Path) -> bool:
        """True if the path, after following '..' and symlinks, is in scope."""
        resolved = path.resolve()
        if self.single_file:
            return resolved == self.single_file
        return resolved.is_relative_to(self.root)

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def files(self, directory: Path, pattern: str) -> list[Path]:
        """In-scope files under a directory that match a glob pattern."""
        if self.single_file:
            return [self.single_file]
        matches = glob.glob(pattern, root_dir=directory, recursive=True)
        paths = (directory / match for match in matches)
        return sorted(p for p in paths if p.is_file() and self.allows(p))


def list_files(args: dict, target: ReviewTarget) -> str:
    requested = args.get("path", ".")
    path = target.root / requested

    if path.resolve() != target.root and not target.allows(path):
        return _error(f"Path is outside the review target: {requested}")
    if not path.exists():
        return _error(f"Path does not exist: {requested}")
    if path.is_file():
        return json.dumps({"files": [target.relative(path)]})

    files = target.files(path, args.get("pattern", "*"))
    return json.dumps(
        {
            "files": [target.relative(f) for f in files[:MAX_FILES]],
            "truncated": len(files) > MAX_FILES,
        }
    )


def read_file(args: dict, target: ReviewTarget) -> str:
    requested = args["path"]
    path = target.root / requested

    if not target.allows(path):
        return _error(f"Path is outside the review target: {requested}")
    if not path.is_file():
        return _error(f"File not found: {requested}")

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError as e:
        return _error(f"Could not read file: {e}")

    content = "".join(f"{i}\t{line}" for i, line in enumerate(lines[:MAX_LINES], 1))
    if len(lines) > MAX_LINES:
        content += f"\n... ({len(lines) - MAX_LINES} more lines truncated)"

    return json.dumps({"path": requested, "lines": len(lines), "content": content})


def search_pattern(args: dict, target: ReviewTarget) -> str:
    try:
        regex = re.compile(args["pattern"], re.IGNORECASE)
    except re.error as e:
        return _error(f"Invalid regex: {e}")

    matches = []
    for path in target.files(target.root, args.get("file_pattern", "**/*")):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, 1):
            if regex.search(line):
                matches.append(
                    {"file": target.relative(path), "line": number, "text": line.strip()[:200]}
                )
                if len(matches) >= MAX_MATCHES:
                    return json.dumps({"matches": matches, "truncated": True})

    return json.dumps({"matches": matches, "truncated": False})


HANDLERS = {
    "list_files": list_files,
    "read_file": read_file,
    "search_pattern": search_pattern,
}


def execute_tool(name: str, tool_input: dict, target: ReviewTarget) -> str:
    """Run one tool call and return its result as a JSON string."""
    handler = HANDLERS.get(name)
    if handler is None:
        return _error(f"Unknown tool: {name}")
    try:
        return handler(tool_input, target)
    except (KeyError, TypeError, ValueError, OSError, NotImplementedError) as e:
        return _error(f"Invalid input for {name}: {e}")
