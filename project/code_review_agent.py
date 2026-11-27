"""
==============================================================================
CODE REVIEW AGENT — A Real Project Tying Everything Together
==============================================================================

This agent combines every Module 2 concept:
  - Extended Thinking:   adaptive thinking for deep code analysis
  - Tool Use:            tools for reading files, listing files, searching
  - Tool Schema Design:  well-defined schemas (review_tools.py)
  - Streaming:           streamed responses for real-time feedback
  - Production Agent:    the while loop with error handling and max iterations
  - Prompt Caching:      cache system prompt + tools across multi-file reviews
  - Structured Outputs:  JSON review findings via output_config.format
  - Error Handling:      proper exception chain with retry logic

USAGE:
  python project/code_review_agent.py <file_or_directory>

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

import json
import os
import sys
import time

import anthropic

from review_report import format_review
from review_schema import REVIEW_FORMAT
from review_tools import TOOLS, ReviewTarget, execute_tool

MODEL = "claude-opus-5-5"
MAX_ITERATIONS = 20
MAX_CONSECUTIVE_ERRORS = 3
OUTPUT_PATH = "review_output.json"

# Frozen for caching: any change here invalidates the cached prefix.
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


def request_params(messages: list) -> dict:
    """Settings shared by both phases, so the second one reuses the cached prefix."""
    return {
        "model": MODEL,
        "thinking": {"type": "adaptive"},
        "tools": TOOLS,
        "system": [
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
        ],
        "messages": messages,
    }


def retry_delay(error: anthropic.APIError, attempt: int) -> float | None:
    """Seconds to wait before retrying, or None if the error is not retryable."""
    if isinstance(error, anthropic.RateLimitError):
        return float(error.response.headers.get("retry-after", 30))
    if isinstance(error, anthropic.APIStatusError):
        return 2.0**attempt if error.status_code >= 500 else None
    if isinstance(error, anthropic.APIConnectionError):
        return 2.0**attempt
    return None


def stream_response(client: anthropic.Anthropic, messages: list, **extra):
    """Send one request, printing text and tool names as they arrive."""
    for attempt in range(1, MAX_CONSECUTIVE_ERRORS + 1):
        try:
            with client.messages.stream(**request_params(messages), **extra) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            print(f"\n  [tool] {event.content_block.name}", flush=True)
                    elif event.type == "text" and "output_config" not in extra:
                        print(event.text, end="", flush=True)
                response = stream.get_final_message()
        except anthropic.APIError as error:
            delay = retry_delay(error, attempt)
            if delay is None or attempt == MAX_CONSECUTIVE_ERRORS:
                raise
            print(f"\n  [request failed, retry {attempt} in {delay:.0f}s]")
            time.sleep(delay)
        else:
            if response.usage.cache_read_input_tokens:
                print(f"\n  [cache hit: {response.usage.cache_read_input_tokens} tokens]")
            return response


# =============================================================================
# PHASE 1: AGENT LOOP — tools + streaming + caching
# =============================================================================


def run_review_agent(client: anthropic.Anthropic, target: ReviewTarget) -> list:
    """Let Claude explore the code with tools. Returns the conversation history."""
    name = target.single_file.name if target.single_file else target.root.name
    messages = [
        {
            "role": "user",
            "content": (
                f"Review the code in: {name}\n\n"
                "Start by listing the files, then read and review each one."
            ),
        }
    ]

    print("\n--- Phase 1: Agent exploring code with tools ---\n")

    for _ in range(MAX_ITERATIONS):
        response = stream_response(client, messages, max_tokens=16000)

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            results = [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": execute_tool(block.name, block.input, target),
                }
                for block in response.content
                if block.type == "tool_use"
            ]
            messages.append({"role": "user", "content": results})
            continue

        if response.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": response.content})
            print("\n\n  [Agent finished exploring]\n")
        else:
            # A cut-off or refused turn can hold a tool call with no result, which
            # the API rejects on the next request, so it is not kept in history.
            print(f"\n  [Stopped early: {response.stop_reason}]")
        return messages

    print(f"\n  [Hit max iterations ({MAX_ITERATIONS})]")
    return messages


# =============================================================================
# PHASE 2: STRUCTURED OUTPUT — final review as JSON
# =============================================================================


def get_structured_review(client: anthropic.Anthropic, messages: list) -> dict:
    """Ask for the final review in the shape defined by REVIEW_FORMAT."""
    print("--- Phase 2: Generating structured review ---\n")

    request = {
        "role": "user",
        "content": "Now produce your final code review as structured JSON. Include all findings.",
    }
    response = stream_response(
        client,
        [*messages, request],
        max_tokens=32000,
        output_config={"format": REVIEW_FORMAT},
    )

    if response.stop_reason != "end_turn":
        return {"error": f"Review did not complete (stop reason: {response.stop_reason})"}

    text = next((block.text for block in response.content if block.type == "text"), None)
    if text is None:
        return {"error": "No text block in response"}
    return json.loads(text)


# =============================================================================
# MAIN
# =============================================================================


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python project/code_review_agent.py <file_or_directory>")
        return 1

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Error: '{path}' does not exist")
        return 1

    print(f"Reviewing: {os.path.abspath(path)}")
    client = anthropic.Anthropic()

    try:
        messages = run_review_agent(client, ReviewTarget(path))
        review = get_structured_review(client, messages)
    except anthropic.APIError as error:
        print(f"\nAPI error: {error.message}")
        return 1

    if "error" in review:
        print(f"Error generating review: {review['error']}")
        return 1

    print(format_review(review, color=sys.stdout.isatty()))
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(review, f, indent=2)
    print(f"\nFull review saved to: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
