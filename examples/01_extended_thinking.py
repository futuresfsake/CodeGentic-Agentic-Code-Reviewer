"""
==============================================================================
MODULE 2: EXTENDED THINKING
==============================================================================

OFFICIAL DOCUMENTATION:
  - Extended Thinking:  https://platform.claude.com/docs/en/build-with-claude/extended-thinking.md
  - Adaptive Thinking:  https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking.md
  - Effort Parameter:   https://platform.claude.com/docs/en/build-with-claude/effort.md
  - Streaming:          https://platform.claude.com/docs/en/build-with-claude/streaming.md
  - Models Overview:    https://platform.claude.com/docs/en/about-claude/models/overview.md
  - Migration Guide:    https://platform.claude.com/docs/en/about-claude/models/migration-guide.md

Extended thinking lets Claude "think out loud" before responding. It produces
a chain-of-thought reasoning step (a `thinking` block) followed by the final
answer (a `text` block). This dramatically improves performance on complex
tasks: math, code analysis, multi-step reasoning, and planning.

KEY CONCEPTS FOR CERTIFICATION:
  1. Adaptive thinking (current models) vs budget_tokens (legacy)
  2. Effort levels control thinking depth
  3. Display modes control what you see
  4. Thinking blocks in multi-turn conversations
  5. Streaming with thinking
  6. Model-specific rules (what works where)

==============================================================================
"""

import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env


# =============================================================================
# PART 1: BASIC ADAPTIVE THINKING (Current Best Practice)
# =============================================================================
# On current models (Opus 5.5, Opus 5, Opus 4.8, 4.7, 4.6, Fable 5/5.1,
# Sonnet 5.5, Sonnet 5, Sonnet 4.6, Haiku 5.5), use adaptive thinking.
#
# Claude decides HOW MUCH to think based on problem complexity.
# You control the DEPTH with the `effort` parameter.

def basic_adaptive_thinking():
    """The standard way to use extended thinking on current models."""
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        thinking={"type": "adaptive"},         # <-- adaptive thinking ON
        output_config={"effort": "high"},       # <-- controls thinking depth
        messages=[
            {"role": "user", "content": "What is 27 * 453 + 128? Show your reasoning."}
        ]
    )

    # Response contains BOTH thinking blocks and text blocks
    for block in response.content:
        if block.type == "thinking":
            print(f"[THINKING]: {block.thinking}")
        elif block.type == "text":
            print(f"[ANSWER]: {block.text}")

    return response


# =============================================================================
# PART 2: THE THINKING PARAMETER - WHAT GOES IN IT
# =============================================================================
#
# The `thinking` parameter is a dict with a `type` key. The valid types
# depend on the model:
#
# ┌──────────────────────┬──────────────────────────────────────────────────┐
# │ Model                │ Valid `thinking` configs                         │
# ├──────────────────────┼──────────────────────────────────────────────────┤
# │ Fable 5 / 5.1        │ {"type": "adaptive"} or OMIT entirely.          │
# │                      │ {"type": "disabled"} -> 400 ERROR               │
# │                      │ budget_tokens -> 400 ERROR                      │
# │                      │ Thinking is ALWAYS ON, can't be turned off.     │
# ├──────────────────────┼──────────────────────────────────────────────────┤
# │ Opus 5.5             │ {"type": "adaptive"} or OMIT (same effect).     │
# │                      │ {"type": "disabled"} -> 400 ERROR at ALL effort │
# │                      │ budget_tokens -> 400 ERROR                      │
# │                      │ Thinking is ALWAYS ON. Default effort: medium.  │
# ├──────────────────────┼──────────────────────────────────────────────────┤
# │ Opus 5               │ {"type": "adaptive"} or OMIT (same effect).     │
# │                      │ {"type": "disabled"} OK at effort high or below │
# │                      │ {"type": "disabled"} -> 400 at xhigh/max       │
# │                      │ budget_tokens -> 400 ERROR                      │
# ├──────────────────────┼──────────────────────────────────────────────────┤
# │ Opus 4.8 / 4.7       │ {"type": "adaptive"} is the only ON mode.      │
# │                      │ {"type": "disabled"} is accepted.               │
# │                      │ OMITTING thinking = NO thinking (unlike Opus 5) │
# │                      │ budget_tokens -> 400 ERROR                      │
# ├──────────────────────┼──────────────────────────────────────────────────┤
# │ Opus 4.6 / Sonnet 4.6│ {"type": "adaptive"} recommended.              │
# │                      │ budget_tokens: deprecated but still functional  │
# │                      │ (transitional escape hatch only)                │
# ├──────────────────────┼──────────────────────────────────────────────────┤
# │ Sonnet 5.5           │ {"type": "adaptive"} or OMIT.                   │
# │                      │ {"type": "disabled"} -> 400 ERROR               │
# │                      │ Use {"type": "between_tools"} to turn off.      │
# │                      │ budget_tokens -> 400 ERROR                      │
# ├──────────────────────┼──────────────────────────────────────────────────┤
# │ Sonnet 5             │ {"type": "adaptive"} or OMIT (adaptive by deflt)│
# │                      │ {"type": "disabled"} is accepted.               │
# │                      │ budget_tokens -> 400 ERROR                      │
# ├──────────────────────┼──────────────────────────────────────────────────┤
# │ Haiku 5.5            │ {"type": "adaptive"} or OMIT.                   │
# │                      │ {"type": "disabled"} OK at high or below.       │
# │                      │ budget_tokens -> 400 ERROR                      │
# ├──────────────────────┼──────────────────────────────────────────────────┤
# │ Haiku 4.5 (legacy)   │ {"type": "enabled", "budget_tokens": N}        │
# │                      │ budget_tokens REQUIRED for thinking             │
# │                      │ Must be < max_tokens, minimum 1024              │
# └──────────────────────┴──────────────────────────────────────────────────┘
#
# CERTIFICATION TAKEAWAY:
#   - Modern models: use {"type": "adaptive"}
#   - budget_tokens is REMOVED on all models after Opus 4.6/Sonnet 4.6
#   - If someone says "set a thinking budget", tell them to use effort levels


# =============================================================================
# PART 3: EFFORT LEVELS (The replacement for budget_tokens)
# =============================================================================
#
# Instead of setting a raw token budget, you set an EFFORT level.
# This is a GA (generally available) feature - no beta header needed.
#
# Effort levels: low | medium | high | xhigh | max
#
# ┌─────────┬────────────────────────────────────────────────────────┐
# │ Level   │ When to use                                            │
# ├─────────┼────────────────────────────────────────────────────────┤
# │ low     │ Simple classification, routing, subagents              │
# │ medium  │ Chat, summaries, straightforward tasks                 │
# │ high    │ Default for most models. Good for coding, analysis.    │
# │ xhigh   │ Best for coding & agentic work (added with Opus 4.7)  │
# │ max     │ When correctness matters more than cost                │
# └─────────┴────────────────────────────────────────────────────────┘
#
# IMPORTANT: Default effort varies by model!
#   - Opus 5.5 and Haiku 5.5: default is "medium"
#   - Everything else: default is "high"

def effort_levels_demo():
    """Show how effort controls thinking depth."""

    # LOW effort - fast, cheap, less thinking
    quick = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": "Is 7 a prime number?"}]
    )

    # HIGH effort - deeper reasoning
    deep = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": "Prove that sqrt(2) is irrational."}]
    )

    # MAX effort - maximum thinking, highest cost
    maximum = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "max"},
        messages=[
            {"role": "user", "content": "Find all bugs in this code and prove correctness..."}
        ]
    )

    return quick, deep, maximum


# =============================================================================
# PART 4: DISPLAY MODES - What you see from thinking
# =============================================================================
#
# The raw chain of thought is NEVER exposed on any current model.
# The `display` field controls what you get back:
#
# ┌──────────────┬──────────────────────────────────────────────────────┐
# │ Display      │ What happens                                         │
# ├──────────────┼──────────────────────────────────────────────────────┤
# │ "omitted"    │ DEFAULT on all current models. Thinking blocks have  │
# │              │ empty text. You still get billed for thinking tokens. │
# ├──────────────┼──────────────────────────────────────────────────────┤
# │ "summarized" │ Returns a readable SUMMARY of the reasoning.         │
# │              │ Opt-in. Same billing. Good for debugging/display.    │
# ├──────────────┼──────────────────────────────────────────────────────┤
# │ "updates"    │ Beta. Returns between-tool-call progress notes.      │
# │              │ Only on Fable 5/5.1, Opus 5.5, Sonnet 5.5.          │
# │              │ Requires beta header: thinking-display-updates-...   │
# └──────────────┴──────────────────────────────────────────────────────┘
#
# GOTCHA: If you stream reasoning to users and use the default "omitted",
# it looks like a long pause before output. Set "summarized" explicitly.

def display_modes_demo():
    """Show different display modes for thinking."""

    # Default: omitted (thinking block has empty string)
    omitted = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        thinking={"type": "adaptive"},  # display defaults to "omitted"
        messages=[{"role": "user", "content": "What is 15 factorial?"}]
    )
    for block in omitted.content:
        if block.type == "thinking":
            print(f"Thinking text: '{block.thinking}'")  # empty string!

    # Summarized: get a readable reasoning summary
    summarized = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        thinking={"type": "adaptive", "display": "summarized"},
        messages=[{"role": "user", "content": "What is 15 factorial?"}]
    )
    for block in summarized.content:
        if block.type == "thinking":
            print(f"Thinking summary: {block.thinking}")  # readable text


# =============================================================================
# PART 5: STREAMING WITH EXTENDED THINKING
# =============================================================================
#
# Streaming is CRITICAL with extended thinking because:
#   1. Thinking can produce many tokens -> long wait without streaming
#   2. Large max_tokens (up to 128K) REQUIRES streaming to avoid HTTP timeouts
#   3. Users need visual feedback that the model is working
#
# Stream events for thinking:
#   - content_block_start with type "thinking" -> thinking begins
#   - content_block_delta with type "thinking_delta" -> thinking tokens
#   - content_block_stop -> thinking done
#   - content_block_start with type "text" -> answer begins
#   - content_block_delta with type "text_delta" -> answer tokens

def streaming_with_thinking():
    """Stream a response that includes thinking blocks."""
    with client.messages.stream(
        model="claude-opus-5-5",
        max_tokens=64000,
        thinking={"type": "adaptive", "display": "summarized"},
        output_config={"effort": "high"},
        messages=[
            {"role": "user", "content": "Explain the P vs NP problem step by step."}
        ]
    ) as stream:
        current_block_type = None

        for event in stream:
            if event.type == "content_block_start":
                current_block_type = event.content_block.type
                if current_block_type == "thinking":
                    print("\n--- THINKING ---")
                elif current_block_type == "text":
                    print("\n--- RESPONSE ---")

            elif event.type == "content_block_delta":
                if event.delta.type == "thinking_delta":
                    print(event.delta.thinking, end="", flush=True)
                elif event.delta.type == "text_delta":
                    print(event.delta.text, end="", flush=True)

        # Always get the final message for usage stats
        final = stream.get_final_message()
        print(f"\n\nInput tokens: {final.usage.input_tokens}")
        print(f"Output tokens: {final.usage.output_tokens}")

    return final


# =============================================================================
# PART 6: MULTI-TURN CONVERSATIONS WITH THINKING
# =============================================================================
#
# CRITICAL RULE: Pass thinking blocks back UNCHANGED in the conversation.
# The API needs them for context continuity. Pass response.content, not
# just the text.
#
# IMPORTANT: Thinking blocks are tied to the model that produced them.
# If you switch models, the new model drops thinking blocks from the old
# model (silently, unbilled). This is called "preserved thinking."

def multi_turn_with_thinking():
    """Show how to handle thinking blocks across turns."""
    messages = []

    # Turn 1
    messages.append({"role": "user", "content": "What is the derivative of x^3 * sin(x)?"})

    response1 = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        thinking={"type": "adaptive", "display": "summarized"},
        messages=messages
    )

    # CRITICAL: Append the FULL content (includes thinking blocks)
    # Do NOT extract just the text - you'd lose the thinking blocks
    messages.append({"role": "assistant", "content": response1.content})

    # Turn 2 - Claude has access to its previous thinking
    messages.append({"role": "user", "content": "Now find the second derivative."})

    response2 = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        thinking={"type": "adaptive", "display": "summarized"},
        messages=messages
    )

    # Print results
    for block in response2.content:
        if block.type == "text":
            print(block.text)

    return response2


# =============================================================================
# PART 7: LEGACY budget_tokens (Haiku 4.5 and older only)
# =============================================================================
#
# This is the OLD way. Only needed if you're working with Haiku 4.5 or
# models older than 4.6. You'll see it in older code and docs.
#
# budget_tokens constraints:
#   - Must be LESS than max_tokens
#   - Minimum: 1024
#   - Directly sets the thinking token ceiling

def legacy_budget_tokens():
    """Legacy approach for older models. DON'T use for new code."""
    response = client.messages.create(
        model="claude-haiku-4-5",   # only old models need this
        max_tokens=16000,
        thinking={
            "type": "enabled",      # NOT "adaptive"
            "budget_tokens": 8000   # must be < max_tokens, min 1024
        },
        messages=[
            {"role": "user", "content": "What is 27 * 453?"}
        ]
    )

    for block in response.content:
        if block.type == "thinking":
            print(f"Thinking: {block.thinking}")
        elif block.type == "text":
            print(f"Answer: {block.text}")

    return response


# =============================================================================
# PART 8: RESPONSE STRUCTURE WITH THINKING
# =============================================================================
#
# When thinking is enabled, response.content looks like:
#
# [
#   ThinkingBlock(type="thinking", thinking="...summary or empty..."),
#   TextBlock(type="text", text="...the actual answer...")
# ]
#
# Key fields on the response:
#   response.content          -> list of content blocks
#   response.stop_reason      -> "end_turn", "max_tokens", "tool_use", etc.
#   response.usage.input_tokens
#   response.usage.output_tokens  (includes thinking tokens!)
#   response.model            -> the model that actually served this

def parse_thinking_response():
    """Demonstrate how to properly parse a thinking-enabled response."""
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        thinking={"type": "adaptive", "display": "summarized"},
        messages=[{"role": "user", "content": "Solve: 2x + 5 = 13"}]
    )

    thinking_text = ""
    answer_text = ""

    for block in response.content:
        if block.type == "thinking":
            thinking_text = block.thinking
        elif block.type == "text":
            answer_text = block.text

    print(f"Stop reason: {response.stop_reason}")
    print(f"Model: {response.model}")
    print(f"Input tokens: {response.usage.input_tokens}")
    print(f"Output tokens: {response.usage.output_tokens}")
    print(f"Thinking: {thinking_text[:200]}...")
    print(f"Answer: {answer_text}")

    return response


# =============================================================================
# PART 9: CONSTRAINTS & GOTCHAS (CERTIFICATION IMPORTANT)
# =============================================================================
#
# 1. SAMPLING PARAMETERS REMOVED on 4.6+ models:
#    temperature, top_p, top_k are all 400 errors on modern models.
#    (On 2026-10-21, they become 400 on ALL models.)
#
# 2. NO ASSISTANT PREFILL on 4.6+ models:
#    You can't start the assistant's response with pre-filled text.
#    Use structured outputs or system prompt instructions instead.
#
# 3. THINKING TOKENS ARE BILLED:
#    output_tokens in usage INCLUDES thinking tokens, regardless of
#    the display setting. "omitted" display doesn't save money.
#
# 4. DON'T COMBINE thinking WITH temperature/top_p/top_k:
#    On current models, sampling parameters are removed entirely.
#    On legacy models, thinking + sampling params = 400 error.
#
# 5. FORCED TOOL_CHOICE REMOVED on some models:
#    Opus 5.5, Sonnet 5.5, Fable 5.1 reject tool_choice "any"/"tool".
#    Use "auto" + strict: true instead.
#
# 6. OUTPUT TOKENS INCLUDE THINKING:
#    When max_tokens=16000 and thinking uses 10000, only 6000 remain
#    for the visible answer. For complex problems, set max_tokens high.
#    Models support up to 128K output but need streaming for that.


# =============================================================================
# PART 10: PUTTING IT ALL TOGETHER - A COMPLETE WORKING EXAMPLE
# =============================================================================

def complete_example():
    """
    A complete, production-ready example with thinking:
    - Uses adaptive thinking
    - Streams the response
    - Handles thinking and text blocks
    - Tracks token usage
    - Works in multi-turn
    """
    messages = []
    total_input_tokens = 0
    total_output_tokens = 0

    def ask(question: str) -> str:
        nonlocal total_input_tokens, total_output_tokens
        messages.append({"role": "user", "content": question})

        with client.messages.stream(
            model="claude-opus-5-5",
            max_tokens=16000,
            thinking={"type": "adaptive", "display": "summarized"},
            output_config={"effort": "high"},
            messages=messages,
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "thinking":
                        print("[thinking...]", end="", flush=True)
                    elif event.content_block.type == "text":
                        print("\n", end="")
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        print(event.delta.text, end="", flush=True)

            final = stream.get_final_message()

        # Append full content (preserves thinking blocks for next turn)
        messages.append({"role": "assistant", "content": final.content})

        total_input_tokens += final.usage.input_tokens
        total_output_tokens += final.usage.output_tokens

        # Extract just the text answer for return value
        answer = next(
            (b.text for b in final.content if b.type == "text"), ""
        )
        print(f"\n[tokens: in={final.usage.input_tokens}, out={final.usage.output_tokens}]")
        return answer

    # Multi-turn conversation with thinking
    ask("What are the three hardest problems in computer science?")
    ask("Explain the first one in more detail.")
    ask("How does it relate to the P vs NP problem?")

    print(f"\nTotal tokens: in={total_input_tokens}, out={total_output_tokens}")


# =============================================================================
# QUICK REFERENCE CHEAT SHEET
# =============================================================================
#
#  WHAT TO DO (modern models - Opus 5.5, Fable 5.1, etc.):
#    thinking={"type": "adaptive"}
#    thinking={"type": "adaptive", "display": "summarized"}
#    output_config={"effort": "high"}   # low/medium/high/xhigh/max
#
#  WHAT NOT TO DO:
#    thinking={"type": "enabled", "budget_tokens": 8000}  # 400 ERROR!
#    thinking={"type": "disabled"}                         # 400 on many models!
#    temperature=0.5                                       # 400 ERROR on 4.6+!
#
#  DEFAULT EFFORT BY MODEL:
#    Opus 5.5, Haiku 5.5  -> "medium"
#    Everything else       -> "high"
#
#  RESPONSE BLOCKS (in order):
#    [ThinkingBlock, TextBlock]        # normal response
#    [ThinkingBlock, ToolUseBlock]     # tool call with thinking
#
#  TOKEN COUNTING:
#    response.usage.output_tokens      # includes thinking + visible text
#    response.usage.input_tokens       # your prompt tokens
#    response.usage.cache_read_input_tokens    # if caching
#    response.usage.cache_creation_input_tokens # if caching
#
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Extended Thinking Demo")
    print("=" * 60)
    print("\nRun individual functions to test each concept.")
    print("Example: basic_adaptive_thinking()")
    print("\nRequires: pip install anthropic")
    print("Requires: ANTHROPIC_API_KEY environment variable")
