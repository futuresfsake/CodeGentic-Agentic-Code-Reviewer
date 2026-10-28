"""
==============================================================================
MODULE 2: PROMPT CACHING
==============================================================================

OFFICIAL DOCUMENTATION:
  - Prompt Caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
  - Pricing:        https://platform.claude.com/docs/en/about-claude/pricing.md

Core rule: Caching is a PREFIX MATCH. Any byte change anywhere in the
prefix invalidates everything after it.

Render order: tools → system → messages

==============================================================================
"""

import anthropic
import json

client = anthropic.Anthropic()


# =============================================================================
# AUTOMATIC CACHING (Simplest)
# =============================================================================
# Top-level cache_control auto-caches the last cacheable block.

def auto_caching():
    """Simplest caching — one line, automatic placement."""
    large_context = "This is a very large document... " * 500  # simulate big context

    # First request: writes to cache (~1.25x cost for cached portion)
    response1 = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        cache_control={"type": "ephemeral"},  # auto-caches last block
        system=large_context,
        messages=[{"role": "user", "content": "Summarize the key points"}]
    )
    print(f"Request 1:")
    print(f"  Cache created: {response1.usage.cache_creation_input_tokens} tokens")
    print(f"  Cache read:    {response1.usage.cache_read_input_tokens} tokens")
    print(f"  Uncached:      {response1.usage.input_tokens} tokens")

    # Second request with same prefix: reads from cache (~0.1x cost)
    response2 = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        cache_control={"type": "ephemeral"},
        system=large_context,  # SAME bytes = cache hit
        messages=[{"role": "user", "content": "What are the main themes?"}]
    )
    print(f"\nRequest 2:")
    print(f"  Cache created: {response2.usage.cache_creation_input_tokens} tokens")
    print(f"  Cache read:    {response2.usage.cache_read_input_tokens} tokens")
    print(f"  Uncached:      {response2.usage.input_tokens} tokens")


# =============================================================================
# MANUAL CACHING (Fine-Grained Control)
# =============================================================================
# Place cache_control on specific content blocks.

def manual_caching():
    """Fine-grained caching with explicit breakpoints."""
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        system=[{
            "type": "text",
            "text": "You are an expert analyst. Here is the reference document: ...",
            "cache_control": {"type": "ephemeral"}  # breakpoint: cache up to here
        }],
        messages=[
            {"role": "user", "content": "What does section 3 say?"}  # varies per request
        ]
    )
    return response


def manual_caching_with_ttl():
    """Cache with explicit 1-hour TTL."""
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        system=[{
            "type": "text",
            "text": "Large reference document...",
            "cache_control": {"type": "ephemeral", "ttl": "1h"}  # 1 hour instead of 5 min
        }],
        messages=[{"role": "user", "content": "Summarize"}]
    )
    return response


# =============================================================================
# MULTI-TURN CACHING
# =============================================================================
# Each new turn reuses the cached prefix. Put breakpoint on the last
# content block of the most recent turn.

def multi_turn_caching():
    """Cache grows incrementally with each conversation turn."""
    system = [{
        "type": "text",
        "text": "You are a helpful coding assistant.",
        "cache_control": {"type": "ephemeral"}
    }]
    messages = []

    def chat(user_msg: str) -> str:
        messages.append({"role": "user", "content": user_msg})

        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=4096,
            system=system,
            messages=messages,
        )

        # Append full content to preserve for next turn
        messages.append({"role": "assistant", "content": response.content})

        print(f"  Cache read: {response.usage.cache_read_input_tokens} tokens")
        return next(b.text for b in response.content if b.type == "text")

    chat("What is a closure in Python?")     # first turn: cache write
    chat("Can you give me an example?")      # second turn: cache read + new
    chat("How is this different from a class?")  # third turn: more cache reuse


# =============================================================================
# CACHING WITH TOOLS
# =============================================================================
# Tools render at position 0. A stable tool list = cacheable prefix.
# NEVER reorder or add/remove tools between requests.

def caching_with_tools():
    """Cache tools + system together."""
    tools = [
        {"name": "search", "description": "Search docs", "input_schema": {
            "type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}},
        {"name": "create", "description": "Create item", "input_schema": {
            "type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},
    ]
    # Tools are rendered first, then system, then messages.
    # Breakpoint on system caches tools + system together.
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        tools=tools,  # stable, deterministic order
        system=[{
            "type": "text",
            "text": "You are an assistant with access to a knowledge base.",
            "cache_control": {"type": "ephemeral"}  # caches tools + system
        }],
        messages=[{"role": "user", "content": "Find docs about auth"}]
    )
    return response


# =============================================================================
# SILENT INVALIDATOR EXAMPLES
# =============================================================================

# BAD: timestamp in system prompt invalidates cache every request
def bad_caching():
    from datetime import datetime
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        system=f"You are helpful. Current time: {datetime.now()}",  # CACHE KILLER
        messages=[{"role": "user", "content": "Hello"}]
    )

# GOOD: keep system frozen, put dynamic content in messages
def good_caching():
    from datetime import datetime
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        cache_control={"type": "ephemeral"},
        system="You are helpful.",  # frozen, cacheable
        messages=[
            {"role": "user", "content": f"Current time is {datetime.now()}. Hello!"}
        ]
    )


# BAD: non-deterministic JSON serialization
def bad_json_caching():
    context = {"b": 2, "a": 1}
    system = json.dumps(context)  # could be {"b":2,"a":1} or {"a":1,"b":2}

# GOOD: deterministic serialization
def good_json_caching():
    context = {"b": 2, "a": 1}
    system = json.dumps(context, sort_keys=True)  # always {"a":1,"b":2}


if __name__ == "__main__":
    print("=" * 60)
    print("Prompt Caching Demo")
    print("=" * 60)
    print("\nRun individual functions to test:")
    print("  auto_caching()         - automatic caching")
    print("  manual_caching()       - explicit breakpoints")
    print("  multi_turn_caching()   - incremental multi-turn cache")
    print("  caching_with_tools()   - tools + system cached together")
