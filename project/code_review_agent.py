"""
==============================================================================
CODE REVIEW AGENT — A Real Project Tying Everything Together
==============================================================================

This agent combines every Module 2 concept:
  - Extended Thinking:   adaptive thinking for deep code analysis
  - Tool Use:            tools for reading files, listing files, searching
  - Tool Schema Design:  well-defined schemas with strict mode
  - Streaming:           streamed responses for real-time feedback
  - Production Agent:    the while loop with error handling and max iterations
  - Prompt Caching:      cache system prompt + tools across multi-file reviews
  - Structured Outputs:  JSON review findings via output_config.format
  - Error Handling:      proper exception chain with retry logic

USAGE:
  python code_review_agent.py <file_or_directory>
  python code_review_agent.py my_script.py
  python code_review_agent.py src/

OFFICIAL DOCUMENTATION:
  - Messages API:        https://platform.claude.com/docs/en/api/messages.md
  - Tool Use:            https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md
  - Structured Outputs:  https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
  - Prompt Caching:      https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
  - Extended Thinking:   https://platform.claude.com/docs/en/build-with-claude/extended-thinking.md
  - Streaming:           https://platform.claude.com/docs/en/api/streaming.md
  - Errors:              https://platform.claude.com/docs/en/api/errors.md

==============================================================================
"""

import anthropic
import json
import os
import sys
import time
import random
import glob as glob_module


# =============================================================================
# CLIENT SETUP — with retry config
# =============================================================================

client = anthropic.Anthropic(max_retries=3)

MODEL = "claude-opus-5-5"

# =============================================================================
# SYSTEM PROMPT — frozen for caching
# =============================================================================

SYSTEM_PROMPT = """You are an expert code reviewer. You review code for:
- Bugs and correctness issues
- Security vulnerabilities (SQL injection, XSS, command injection, hardcoded secrets)
- Performance problems (N+1 queries, unnecessary allocations, missing indexes)
- Maintainability (naming, complexity, dead code, missing error handling)

When reviewing, use the tools to:
1. First, list files in the target to understand the scope
2. Read each file that needs review
3. Search for specific patterns when investigating a concern

Be thorough but practical. Focus on issues that matter, not style nitpicks.
When you have reviewed all relevant files, stop using tools and provide your final review."""


# =============================================================================
# TOOL DEFINITIONS — stable order for caching
# =============================================================================

TOOLS = [
    {
        "name": "list_files",
        "description": "List files in a directory. Use this first to understand what files exist in the review target. Returns file paths relative to the target.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list. Use '.' for the review target root."
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter files, e.g. '*.py' or '**/*.js'"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file. Returns the file content with line numbers. Use this to review code in a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read, relative to the review target."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "search_pattern",
        "description": "Search for a regex pattern across files. Use this to find specific code patterns like 'eval(', 'SELECT.*FROM', hardcoded passwords, or to trace how a function is used.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern to limit which files to search, e.g. '*.py'"
                }
            },
            "required": ["pattern"]
        }
    }
]


# =============================================================================
# STRUCTURED OUTPUT SCHEMA — for final review
# =============================================================================

REVIEW_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "code_review",
        "schema": {
            "type": "object",
            "properties": {
                "overall_quality": {
                    "type": "string",
                    "enum": ["excellent", "good", "needs_improvement", "poor"]
                },
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "severity": {
                                "type": "string",
                                "enum": ["critical", "warning", "info"]
                            },
                            "category": {
                                "type": "string",
                                "enum": ["bug", "security", "performance", "style", "maintainability"]
                            },
                            "file": {
                                "type": "string"
                            },
                            "line": {
                                "type": "integer"
                            },
                            "description": {
                                "type": "string"
                            },
                            "suggestion": {
                                "type": "string"
                            }
                        },
                        "required": ["severity", "category", "file", "line", "description", "suggestion"],
                        "additionalProperties": False
                    }
                },
                "summary": {
                    "type": "string"
                }
            },
            "required": ["overall_quality", "findings", "summary"],
            "additionalProperties": False
        }
    }
}


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

def execute_tool(tool_name: str, tool_input: dict, review_target: str) -> str:
    """Execute a tool and return the result as a string."""

    if tool_name == "list_files":
        return tool_list_files(tool_input, review_target)
    elif tool_name == "read_file":
        return tool_read_file(tool_input, review_target)
    elif tool_name == "search_pattern":
        return tool_search_pattern(tool_input, review_target)
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def tool_list_files(args: dict, review_target: str) -> str:
    """List files in a directory with optional glob filtering."""
    path = os.path.join(review_target, args.get("path", "."))
    pattern = args.get("pattern", "*")

    if not os.path.exists(path):
        return json.dumps({"error": f"Path does not exist: {args.get('path')}"})

    if os.path.isfile(path):
        return json.dumps({"files": [os.path.relpath(path, review_target)]})

    full_pattern = os.path.join(path, pattern)
    files = []
    for match in glob_module.glob(full_pattern, recursive=True):
        if os.path.isfile(match):
            files.append(os.path.relpath(match, review_target))

    files.sort()
    return json.dumps({"files": files[:100]})  # cap at 100


def tool_read_file(args: dict, review_target: str) -> str:
    """Read a file's contents with line numbers."""
    path = os.path.join(review_target, args["path"])

    if not os.path.exists(path):
        return json.dumps({"error": f"File not found: {args['path']}"})

    if not os.path.isfile(path):
        return json.dumps({"error": f"Not a file: {args['path']}"})

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return json.dumps({"error": f"Could not read file: {str(e)}"})

    if len(lines) > 500:
        numbered = [f"{i+1}\t{line}" for i, line in enumerate(lines[:500])]
        content = "".join(numbered) + f"\n... ({len(lines) - 500} more lines truncated)"
    else:
        numbered = [f"{i+1}\t{line}" for i, line in enumerate(lines)]
        content = "".join(numbered)

    return json.dumps({"path": args["path"], "lines": len(lines), "content": content})


def tool_search_pattern(args: dict, review_target: str) -> str:
    """Search for a regex pattern across files."""
    import re

    pattern = args["pattern"]
    file_pattern = args.get("file_pattern", "**/*")

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return json.dumps({"error": f"Invalid regex: {str(e)}"})

    full_pattern = os.path.join(review_target, file_pattern)
    matches = []

    for filepath in glob_module.glob(full_pattern, recursive=True):
        if not os.path.isfile(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if regex.search(line):
                        rel_path = os.path.relpath(filepath, review_target)
                        matches.append({"file": rel_path, "line": i, "text": line.strip()[:200]})
                        if len(matches) >= 50:
                            return json.dumps({"matches": matches, "truncated": True})
        except Exception:
            continue

    return json.dumps({"matches": matches, "truncated": False})


# =============================================================================
# PHASE 1: AGENT LOOP — tools + streaming + caching + error handling
# =============================================================================

def run_review_agent(review_target: str) -> list:
    """
    Phase 1: Let Claude explore the code using tools.
    Returns the full conversation history for Phase 2.

    Concepts used:
    - Tool use: the agent loop (while stop_reason == "tool_use")
    - Streaming: real-time output with get_final_message()
    - Prompt caching: system prompt + tools cached via cache_control
    - Error handling: specific exception chain + consecutive error tracking
    - Extended thinking: adaptive thinking for analysis
    """
    messages = [
        {"role": "user", "content": f"Review the code at: {review_target}\n\nStart by listing the files, then read and review each one."}
    ]

    max_iterations = 20
    iterations = 0
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 3

    print("\n--- Phase 1: Agent exploring code with tools ---\n")

    while iterations < max_iterations:
        iterations += 1

        try:
            # STREAMING + CACHING: stream for real-time feedback,
            # cache system + tools prefix across iterations
            with client.messages.stream(
                model=MODEL,
                max_tokens=8000,
                thinking={"type": "adaptive"},  # EXTENDED THINKING
                tools=TOOLS,                     # stable tool list (cacheable)
                system=[{                        # PROMPT CACHING: breakpoint caches tools + system
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=messages,
            ) as stream:
                # Print streamed text in real-time
                for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_start" and hasattr(event, "content_block"):
                            if event.content_block.type == "text":
                                pass  # text block starting
                            elif event.content_block.type == "tool_use":
                                print(f"  [tool] {event.content_block.name}", end="", flush=True)
                        elif event.type == "content_block_delta":
                            if hasattr(event, "delta"):
                                if event.delta.type == "text_delta":
                                    print(event.delta.text, end="", flush=True)
                                elif event.delta.type == "input_json_delta":
                                    pass  # tool input streaming

                response = stream.get_final_message()

            consecutive_errors = 0  # reset on success

            # Print cache stats
            usage = response.usage
            if hasattr(usage, "cache_read_input_tokens") and usage.cache_read_input_tokens:
                print(f"\n  [cache hit: {usage.cache_read_input_tokens} tokens read from cache]")

        except anthropic.RateLimitError:
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                print("\nRate limited too many times. Stopping.")
                break
            wait = 30
            print(f"\n  [rate limited, waiting {wait}s...]")
            time.sleep(wait)
            continue

        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print(f"\nServer errors ({e.status_code}). Stopping.")
                    break
                time.sleep(5)
                continue
            else:
                print(f"\nAPI error ({e.status_code}): {e.message}")
                break

        except anthropic.APIConnectionError:
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                print("\nConnection errors. Stopping.")
                break
            time.sleep(5)
            continue

        # AGENT LOOP: process response
        if response.stop_reason == "end_turn":
            print("\n\n  [Agent finished exploring]\n")
            messages.append({"role": "assistant", "content": response.content})
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"({block.name}...", end="", flush=True)
                    result = execute_tool(block.name, block.input, review_target)
                    print(" done)", flush=True)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "max_tokens":
            print("\n  [Hit max tokens, wrapping up]")
            messages.append({"role": "assistant", "content": response.content})
            break

    if iterations >= max_iterations:
        print(f"\n  [Hit max iterations ({max_iterations})]")

    return messages


# =============================================================================
# PHASE 2: STRUCTURED OUTPUT — final review as JSON
# =============================================================================

def get_structured_review(messages: list) -> dict:
    """
    Phase 2: Ask Claude to produce a structured JSON review.

    Concepts used:
    - Structured outputs: output_config.format with json_schema
    - Prompt caching: same system prefix = cache hit from Phase 1
    - Error handling: retry on transient failures
    """
    print("--- Phase 2: Generating structured review ---\n")

    messages.append({
        "role": "user",
        "content": "Now produce your final code review as structured JSON. Include all findings."
    })

    last_exception = None
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=16000,
                thinking={"type": "adaptive"},
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}  # same prefix = cache hit
                }],
                output_config={"format": REVIEW_SCHEMA},  # STRUCTURED OUTPUT
                messages=messages,
            )

            # Print cache stats
            usage = response.usage
            if hasattr(usage, "cache_read_input_tokens") and usage.cache_read_input_tokens:
                print(f"  [cache hit: {usage.cache_read_input_tokens} tokens read from cache]")

            # Parse the structured JSON
            text_block = next((b for b in response.content if b.type == "text"), None)
            if text_block:
                return json.loads(text_block.text)
            return {"error": "No text block in response"}

        except anthropic.RateLimitError as e:
            last_exception = e
            retry_after = int(e.response.headers.get("retry-after", "30"))
            delay = max(retry_after, 2 ** attempt) + random.uniform(0, 1)
            print(f"  [rate limited, retry {attempt+1}/3 after {delay:.0f}s]")
            time.sleep(delay)

        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                last_exception = e
                time.sleep(2 ** attempt)
                continue
            raise

    print(f"  [Failed after 3 retries]")
    return {"error": str(last_exception)}


# =============================================================================
# OUTPUT — pretty-print the review
# =============================================================================

SEVERITY_COLORS = {"critical": "\033[91m", "warning": "\033[93m", "info": "\033[94m"}
RESET = "\033[0m"


def print_review(review: dict):
    """Pretty-print the structured review to the terminal."""
    print("=" * 60)
    print("CODE REVIEW RESULTS")
    print("=" * 60)

    quality = review.get("overall_quality", "unknown")
    print(f"\nOverall Quality: {quality.upper()}\n")

    findings = review.get("findings", [])
    if not findings:
        print("No findings!")
    else:
        for i, f in enumerate(findings, 1):
            severity = f["severity"]
            color = SEVERITY_COLORS.get(severity, "")
            print(f"  {color}[{severity.upper()}]{RESET} {f['category']} — {f['file']}:{f['line']}")
            print(f"    {f['description']}")
            print(f"    Fix: {f['suggestion']}")
            print()

    print(f"Summary: {review.get('summary', 'N/A')}")
    print("=" * 60)

    # Stats
    by_severity = {}
    for f in findings:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
    if by_severity:
        parts = [f"{count} {sev}" for sev, count in sorted(by_severity.items())]
        print(f"Findings: {', '.join(parts)}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python code_review_agent.py <file_or_directory>")
        print("Example: python code_review_agent.py my_script.py")
        print("         python code_review_agent.py src/")
        sys.exit(1)

    target = sys.argv[1]

    if not os.path.exists(target):
        print(f"Error: '{target}' does not exist")
        sys.exit(1)

    target = os.path.abspath(target)
    print(f"Reviewing: {target}")

    # Phase 1: Agent explores code with tools (streaming + caching)
    messages = run_review_agent(target)

    # Phase 2: Structured JSON output
    review = get_structured_review(messages)

    # Output
    if "error" not in review:
        print_review(review)

        # Save to file
        output_path = "review_output.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(review, f, indent=2)
        print(f"\nFull review saved to: {output_path}")
    else:
        print(f"Error generating review: {review['error']}")


if __name__ == "__main__":
    main()
