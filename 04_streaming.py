"""
==============================================================================
MODULE 2: STREAMING RESPONSES
==============================================================================

OFFICIAL DOCUMENTATION:
  - Streaming:       https://platform.claude.com/docs/en/build-with-claude/streaming.md
  - Errors:          https://platform.claude.com/docs/en/api/errors.md
  - Models Overview: https://platform.claude.com/docs/en/about-claude/models/overview.md

Streaming sends tokens as Claude generates them via Server-Sent Events (SSE).
Required for large outputs, recommended for everything else.

==============================================================================
"""

import anthropic

client = anthropic.Anthropic()


# =============================================================================
# BASIC STREAMING - text_stream helper
# =============================================================================
# Simplest way to stream. Use text_stream to get just the text tokens.
# Call get_final_message() at the end for the complete response.

def basic_stream():
    """Stream text tokens as they arrive."""
    with client.messages.stream(
        model="claude-opus-5-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": "Explain what an API is in 3 sentences."}]
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)  # flush=True is critical!

        final = stream.get_final_message()

    print(f"\n\nTokens: in={final.usage.input_tokens}, out={final.usage.output_tokens}")
    print(f"Stop reason: {final.stop_reason}")
    return final


# =============================================================================
# STREAMING WITH EXTENDED THINKING
# =============================================================================
# When thinking is enabled, the stream produces thinking blocks first,
# then text blocks. You handle them by checking the delta type.

def stream_with_thinking():
    """Stream thinking + response tokens separately."""
    with client.messages.stream(
        model="claude-opus-5-5",
        max_tokens=16000,
        thinking={"type": "adaptive", "display": "summarized"},
        output_config={"effort": "high"},
        messages=[
            {"role": "user", "content": "What is 127 * 389? Think step by step."}
        ]
    ) as stream:
        current_type = None

        for event in stream:
            # A new block starts (thinking or text)
            if event.type == "content_block_start":
                current_type = event.content_block.type
                if current_type == "thinking":
                    print("--- THINKING ---")
                elif current_type == "text":
                    print("\n--- RESPONSE ---")

            # Token arrives
            elif event.type == "content_block_delta":
                if event.delta.type == "thinking_delta":
                    print(event.delta.thinking, end="", flush=True)
                elif event.delta.type == "text_delta":
                    print(event.delta.text, end="", flush=True)

        final = stream.get_final_message()

    print(f"\n\nTokens: in={final.usage.input_tokens}, out={final.usage.output_tokens}")
    return final


# =============================================================================
# STREAMING WITH TOOL USE
# =============================================================================
# When Claude calls a tool, the stream produces input_json_delta events
# for the tool arguments. The agent loop still works the same way -
# you just wrap the API call in stream() instead of create().

import json

tools = [
    {
        "name": "get_weather",
        "description": "Get current weather for a city. Use when the user asks about weather.",
        "eager_input_streaming": True,  # stream tool inputs immediately
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"]
        }
    }
]


def fake_get_weather(city: str) -> str:
    return json.dumps({"city": city, "temp": "22°C", "conditions": "sunny"})


def stream_with_tools():
    """Streaming agent loop - same pattern, just with stream()."""
    messages = [{"role": "user", "content": "What's the weather in Berlin?"}]

    while True:
        with client.messages.stream(
            model="claude-opus-5-5",
            max_tokens=4096,
            tools=tools,
            messages=messages,
        ) as stream:
            # Print text tokens as they arrive
            for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        print(event.delta.text, end="", flush=True)
                    elif event.delta.type == "input_json_delta":
                        pass  # tool input building, could display for debugging

            response = stream.get_final_message()

        # Same loop logic as non-streaming
        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"\n[Calling {block.name}({block.input})]")
                    result = fake_get_weather(**block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

    print(f"\nStop reason: {response.stop_reason}")
    return response


# =============================================================================
# ERROR HANDLING IN STREAMS
# =============================================================================
# The SDK retries connection errors and 429s automatically (default 2 retries).
# Wrap in try/except for anything beyond that.

def stream_with_error_handling():
    """Robust streaming with error recovery."""
    try:
        with client.messages.stream(
            model="claude-opus-5-5",
            max_tokens=16000,
            messages=[{"role": "user", "content": "Write a short poem."}]
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)

            final = stream.get_final_message()
            return final

    except anthropic.APIConnectionError:
        print("\n[Connection lost - retry the request]")
    except anthropic.RateLimitError as e:
        retry_after = int(e.response.headers.get("retry-after", "60"))
        print(f"\n[Rate limited - retry after {retry_after}s]")
    except anthropic.APIStatusError as e:
        if e.status_code >= 500:
            print(f"\n[Server error {e.status_code} - retry later]")
        else:
            print(f"\n[API error: {e.message}]")
    return None


# =============================================================================
# ASYNC STREAMING
# =============================================================================
# Same pattern but with async/await. Use AsyncAnthropic client.

async def async_stream():
    """Async streaming for concurrent applications."""
    async_client = anthropic.AsyncAnthropic()

    async with async_client.messages.stream(
        model="claude-opus-5-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": "Hello!"}]
    ) as stream:
        async for text in stream.text_stream:
            print(text, end="", flush=True)

        final = stream.get_final_message()

    print(f"\nTokens: {final.usage.output_tokens}")
    return final


# =============================================================================
# get_final_message() - BEST OF BOTH WORLDS
# =============================================================================
# Sometimes you don't need live tokens - you just want timeout protection.
# stream() + get_final_message() gives you that without handling events.

def stream_for_timeout_protection():
    """Stream just for timeout safety, get the full response at the end."""
    with client.messages.stream(
        model="claude-opus-5-5",
        max_tokens=64000,  # large output that would timeout without streaming
        thinking={"type": "adaptive"},
        output_config={"effort": "xhigh"},
        messages=[
            {"role": "user", "content": "Write a detailed analysis of sorting algorithms."}
        ]
    ) as stream:
        # Skip event handling, just get the final message
        final = stream.get_final_message()

    for block in final.content:
        if block.type == "text":
            print(block.text)

    return final


# =============================================================================
# LOW-LEVEL STREAMING (stream=True)
# =============================================================================
# Raw event iterator. No state accumulation, no get_final_message().
# Use only when you need minimum memory or custom event processing.

def raw_stream():
    """Low-level streaming - raw events, no helpers."""
    for event in client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": "Say hello."}],
        stream=True,
    ):
        if event.type == "content_block_delta":
            if event.delta.type == "text_delta":
                print(event.delta.text, end="", flush=True)
        elif event.type == "message_delta":
            print(f"\n[Stop: {event.delta.stop_reason}]")


if __name__ == "__main__":
    print("=" * 60)
    print("Streaming Demo")
    print("=" * 60)
    print("\nRun individual functions to test each pattern:")
    print("  basic_stream()               - simplest streaming")
    print("  stream_with_thinking()        - thinking + text blocks")
    print("  stream_with_tools()           - streaming agent loop")
    print("  stream_with_error_handling()  - robust error recovery")
    print("  stream_for_timeout_protection() - stream just for safety")
    print("  raw_stream()                  - low-level events")
    print("\nRequires: pip install anthropic")
    print("Requires: ANTHROPIC_API_KEY environment variable")
