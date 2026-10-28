"""
==============================================================================
MODULE 2: TOOL USE - SCHEMAS, THE LOOP, AND CALLING PATTERNS
==============================================================================

OFFICIAL DOCUMENTATION:
  - Tool Use Overview:     https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md
  - Structured Outputs:    https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
  - Streaming:             https://platform.claude.com/docs/en/build-with-claude/streaming.md
  - Models Overview:       https://platform.claude.com/docs/en/about-claude/models/overview.md
  - Code Execution Tool:   https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool.md
  - Bash Tool:             https://platform.claude.com/docs/en/agents-and-tools/tool-use/bash-tool.md
  - Text Editor Tool:      https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool.md
  - Errors:                https://platform.claude.com/docs/en/api/errors.md

Tool use (aka "function calling") is how Claude interacts with the outside
world. Claude can't run code itself - it can only REQUEST that your
application run a function, then use the result.

IS TOOL USE AN AGENT?
  Not by itself. Tool use is the MECHANISM. An agent is built ON TOP of it.
  - Single tool call: Claude calls one tool, gets the result, responds.
    That's just tool use. Like a calculator.
  - Agent loop: Claude calls tools REPEATEDLY, deciding what to do next
    based on results, until it finishes the task autonomously.
    THAT'S an agent. The loop is what makes it agentic.

  Think of it this way:
    Tool use = "Claude can use a hammer"
    Agent    = "Claude can build a house, deciding which tools to pick up"

==============================================================================
THE 6-STEP TOOL USE CYCLE (CERTIFICATION CORE CONCEPT)
==============================================================================

  Step 1: DEFINE   - You define tools with name, description, input_schema
  Step 2: SEND     - Your code sends user message + tool definitions to Claude
  Step 3: RECEIVE  - Claude responds with a tool_use block (stop_reason: "tool_use")
  Step 4: EXECUTE  - YOUR code runs the actual function (Claude never runs it)
  Step 5: RETURN   - You send back a tool_result block referencing the tool_use id
  Step 6: CONTINUE - Claude reads the result and either responds or calls another tool

  ┌─────────┐     tools + message      ┌─────────┐
  │  YOUR   │ ──────────────────────►  │  CLAUDE │
  │  CODE   │                          │   API   │
  │         │  ◄─────────────────────  │         │
  │         │     tool_use block       │         │
  │         │     stop_reason:tool_use │         │
  │         │                          │         │
  │ (runs   │     tool_result block    │         │
  │  the    │ ──────────────────────►  │(uses    │
  │  func)  │                          │ result) │
  │         │  ◄─────────────────────  │         │
  │         │     final text response  │         │
  └─────────┘                          └─────────┘

  KEY INSIGHT: The API is STATELESS between calls. Every request must include
  the full conversation history. Your code keeps the state, not Claude.

==============================================================================
"""

import anthropic
import json

client = anthropic.Anthropic()


# =============================================================================
# STEP 1: DEFINE THE TOOL SCHEMA
# =============================================================================
# A tool definition has three required parts:
#   - name: what Claude calls the tool (snake_case, unique)
#   - description: tells Claude WHEN and WHY to use this tool
#   - input_schema: JSON Schema defining the parameters
#
# The description is critical - it's how Claude decides whether to use the tool.
# A vague description = Claude uses the tool wrong or not at all.

tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a specific city. Use this when the user asks about weather conditions, temperature, or forecasts for a location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name, e.g. 'San Francisco'"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit. Defaults to fahrenheit."
                }
            },
            "required": ["city"]
        }
    }
]

# The input_schema follows JSON Schema spec:
#   - "type": "object" at the top level (always)
#   - "properties": the parameters Claude can pass
#   - "required": which parameters are mandatory
#   - Each property has type, description, and optionally enum/default


# =============================================================================
# STEP 2 & 3: SEND MESSAGE, RECEIVE tool_use BLOCK
# =============================================================================
# When you send tools with a message, Claude may decide to call one.
# If it does, the response has:
#   - stop_reason: "tool_use"
#   - A tool_use content block with: id, name, input

def demonstrate_tool_call():
    """Show what a tool_use response looks like."""

    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        tools=tools,
        messages=[
            {"role": "user", "content": "What's the weather in Tokyo?"}
        ]
    )

    print(f"Stop reason: {response.stop_reason}")  # "tool_use"

    for block in response.content:
        if block.type == "tool_use":
            print(f"Tool name: {block.name}")       # "get_weather"
            print(f"Tool ID:   {block.id}")          # "toolu_abc123..."
            print(f"Input:     {block.input}")        # {"city": "Tokyo"}
        elif block.type == "text":
            print(f"Text: {block.text}")

    # The response.content might contain BOTH text and tool_use blocks.
    # Claude might say "Let me check the weather for you" (text) then
    # call the tool (tool_use). Always check ALL blocks.

    return response


# =============================================================================
# STEP 4 & 5: EXECUTE TOOL, RETURN tool_result
# =============================================================================
# YOUR code runs the function. Claude never executes anything.
# Then you send back a tool_result block that MUST reference the
# original tool_use id. This is how Claude knows which call it's for.

def fake_get_weather(city: str, unit: str = "fahrenheit") -> dict:
    """Simulated weather function - in production this hits a real API."""
    return {
        "city": city,
        "temperature": 72 if unit == "fahrenheit" else 22,
        "unit": unit,
        "conditions": "partly cloudy",
        "humidity": "65%"
    }


def execute_and_return():
    """Show the full execute -> return cycle."""

    # Step 2: Send message with tools
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        tools=tools,
        messages=[
            {"role": "user", "content": "What's the weather in Tokyo?"}
        ]
    )

    # Step 3: Check if Claude wants to call a tool
    if response.stop_reason != "tool_use":
        print("Claude didn't call a tool")
        return

    # Step 4: Find the tool_use block and execute the function
    tool_use_block = next(b for b in response.content if b.type == "tool_use")

    result = fake_get_weather(**tool_use_block.input)

    # Step 5 & 6: Send tool_result back, Claude continues
    followup = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        tools=tools,
        messages=[
            {"role": "user", "content": "What's the weather in Tokyo?"},
            {"role": "assistant", "content": response.content},  # includes tool_use
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,  # MUST match!
                        "content": json.dumps(result)
                    }
                ]
            }
        ]
    )

    # Now Claude has the weather data and gives a natural language answer
    for block in followup.content:
        if block.type == "text":
            print(block.text)

    return followup


# =============================================================================
# THE COMPLETE TOOL USE LOOP (SINGLE TOOL CALL - NOT AN AGENT YET)
# =============================================================================
# This handles ONE round of tool use. Claude calls a tool, gets the result,
# and responds. This is the foundation - but it's not an agent because
# it doesn't loop.

def single_tool_use():
    """A complete single-round tool use interaction."""

    messages = [{"role": "user", "content": "What's the weather like in Paris?"}]

    # First API call - Claude decides to use a tool
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        tools=tools,
        messages=messages,
    )

    # If Claude didn't call a tool, we're done
    if response.stop_reason == "end_turn":
        return next(b.text for b in response.content if b.type == "text")

    # Claude wants to use a tool - execute it
    if response.stop_reason == "tool_use":
        # Add Claude's response (with tool_use block) to conversation
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool call and collect results
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = fake_get_weather(**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result)
                })

        # Send results back
        messages.append({"role": "user", "content": tool_results})

        # Second API call - Claude uses the results
        final = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )
        return next(b.text for b in final.content if b.type == "text")


# =============================================================================
# THE AGENT LOOP (MULTI-STEP TOOL USE - THIS IS AN AGENT)
# =============================================================================
# An agent loop keeps calling Claude until it stops requesting tools.
# Claude decides what tools to call, in what order, based on results.
# THIS is what makes it agentic - the model drives the workflow.
#
# The pattern: while stop_reason == "tool_use": keep going

def make_tools_for_agent():
    """Define multiple tools for the agent to choose from."""
    return [
        {
            "name": "get_weather",
            "description": "Get current weather for a city.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        },
        {
            "name": "get_time",
            "description": "Get the current time in a timezone.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "IANA timezone, e.g. 'Asia/Tokyo'"}
                },
                "required": ["timezone"]
            }
        },
        {
            "name": "convert_currency",
            "description": "Convert an amount between currencies.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Amount to convert"},
                    "from_currency": {"type": "string", "description": "Source currency code"},
                    "to_currency": {"type": "string", "description": "Target currency code"}
                },
                "required": ["amount", "from_currency", "to_currency"]
            }
        }
    ]


def execute_tool(name: str, args: dict) -> str:
    """Dispatch tool calls to the right function."""
    if name == "get_weather":
        return json.dumps({"city": args["city"], "temp": "22°C", "conditions": "sunny"})
    elif name == "get_time":
        return json.dumps({"timezone": args["timezone"], "time": "14:30 JST"})
    elif name == "convert_currency":
        return json.dumps({"result": args["amount"] * 0.85, "currency": args["to_currency"]})
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


def agent_loop(user_message: str):
    """
    The AGENTIC tool use loop. This is the core pattern that makes
    Claude an agent - it keeps calling tools until it's done.

    Claude might:
      - Call one tool, then respond
      - Call multiple tools in parallel, then respond
      - Call a tool, read the result, call another tool, then respond
      - Decide no tools are needed and just respond
    """
    agent_tools = make_tools_for_agent()
    messages = [{"role": "user", "content": user_message}]

    # The loop: keep going while Claude wants to call tools
    while True:
        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=4096,
            tools=agent_tools,
            messages=messages,
        )

        # If Claude is done (no more tool calls), break out
        if response.stop_reason == "end_turn":
            break

        # If Claude hit the token limit, break (handle gracefully)
        if response.stop_reason == "max_tokens":
            print("[WARNING] Hit max_tokens limit")
            break

        # Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Add Claude's response to conversation history
            messages.append({"role": "assistant", "content": response.content})

            # Execute ALL tool calls (Claude can call multiple in parallel)
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  -> Calling {block.name}({block.input})")
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Send ALL results back in a SINGLE user message
            # (splitting them into multiple messages trains Claude to
            # stop making parallel calls - always batch them)
            messages.append({"role": "user", "content": tool_results})

            # Loop continues - Claude will process results and either
            # call more tools or give a final answer

    # Extract final text answer
    answer = next((b.text for b in response.content if b.type == "text"), "")
    print(f"\nFinal answer: {answer}")
    return answer


# =============================================================================
# PARALLEL TOOL USE
# =============================================================================
# By default, Claude can call MULTIPLE tools in a single response.
# One assistant message may contain several tool_use blocks.
# You MUST execute all of them and return ALL results in ONE user message.
#
# Example: "What's the weather in Tokyo and the time in London?"
# Claude might call get_weather AND get_time in one response.
#
# To disable: set disable_parallel_tool_use=True (still works on all models)

def parallel_tool_example():
    """Demonstrate handling parallel tool calls."""
    agent_tools = make_tools_for_agent()

    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        tools=agent_tools,
        messages=[
            {"role": "user", "content": "What's the weather in Tokyo AND the time in London?"}
        ]
    )

    # Response may have multiple tool_use blocks
    tool_uses = [b for b in response.content if b.type == "tool_use"]
    print(f"Claude made {len(tool_uses)} parallel tool calls:")

    for tu in tool_uses:
        print(f"  - {tu.name}({tu.input})")


# =============================================================================
# TOOL USE WITH ERRORS
# =============================================================================
# If a tool call fails, return a tool_result with is_error: True.
# Don't drop the result - Claude needs to know the call failed.

def error_handling_example():
    """Show how to handle tool execution errors."""
    messages = [{"role": "user", "content": "What's the weather in Atlantis?"}]

    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        tools=tools,
        messages=messages,
    )

    if response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                try:
                    result = fake_get_weather(**block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })
                except Exception as e:
                    # Return error - DON'T skip the tool_result
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "is_error": True,
                        "content": f"Error: {str(e)}"
                    })

        messages.append({"role": "user", "content": tool_results})


# =============================================================================
# STRICT MODE (input validation guarantee)
# =============================================================================
# Set strict: True on the tool definition. Claude's tool_use.input will
# ALWAYS validate against the schema. No extra fields, all required present.
#
# Requirements for strict mode:
#   - additionalProperties: false in the schema
#   - All properties listed in required
#
# NOTE: Forced tool_choice ("any"/"tool") is REMOVED on Opus 5.5,
# Sonnet 5.5, and Fable 5.1. Use tool_choice "auto" + strict: true.

strict_tools = [
    {
        "name": "classify_sentiment",
        "description": "Classify the sentiment of text as positive, negative, or neutral.",
        "strict": True,  # <-- guarantees valid input
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text to classify"},
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral"]
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence score 0-1"
                }
            },
            "required": ["text", "sentiment", "confidence"],
            "additionalProperties": False  # REQUIRED for strict mode
        }
    }
]


# =============================================================================
# tool_choice - CONTROLLING WHEN CLAUDE USES TOOLS
# =============================================================================
# tool_choice controls WHETHER Claude calls a tool:
#
# ┌──────────────────────────┬──────────────────────────────────────────────┐
# │ tool_choice              │ Behavior                                     │
# ├──────────────────────────┼──────────────────────────────────────────────┤
# │ {"type": "auto"}         │ Claude decides. DEFAULT. Always use this.   │
# │ {"type": "any"}          │ MUST call a tool. REMOVED on Opus 5.5,      │
# │                          │ Sonnet 5.5, Fable 5.1 (400 error).         │
# │ {"type": "tool",         │ MUST call this specific tool. ALSO REMOVED  │
# │  "name": "tool_name"}    │ on those same models.                       │
# │ {"type": "none"}         │ Never call tools. Still works everywhere.   │
# └──────────────────────────┴──────────────────────────────────────────────┘
#
# CERTIFICATION KEY POINT:
# On modern models, use tool_choice "auto" + an instruction in the prompt
# telling Claude which tool to use, plus strict: true for valid arguments.

def tool_choice_example():
    """Demonstrate tool_choice options."""

    # AUTO (default, works everywhere) - Claude decides
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        tools=strict_tools,
        tool_choice={"type": "auto"},  # this is the default
        messages=[
            {"role": "user", "content": "Analyze: 'I love this product!'"}
        ]
    )

    # NONE - prevent tool use
    response_no_tools = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        tools=strict_tools,
        tool_choice={"type": "none"},
        messages=[
            {"role": "user", "content": "Analyze: 'I love this product!'"}
        ]
    )


# =============================================================================
# THE FULL MESSAGE FLOW (what the conversation history looks like)
# =============================================================================
# After a tool use cycle, the messages array looks like this:
#
# messages = [
#   {"role": "user", "content": "What's the weather in Tokyo?"},
#
#   {"role": "assistant", "content": [
#       {"type": "text", "text": "I'll check the weather for you."},
#       {"type": "tool_use", "id": "toolu_abc", "name": "get_weather",
#        "input": {"city": "Tokyo"}}
#   ]},
#
#   {"role": "user", "content": [
#       {"type": "tool_result", "tool_use_id": "toolu_abc",
#        "content": "{\"temp\": 22, \"conditions\": \"sunny\"}"}
#   ]},
#
#   {"role": "assistant", "content": [
#       {"type": "text", "text": "It's 22°C and sunny in Tokyo!"}
#   ]}
# ]
#
# NOTICE:
# - tool_result is in a "user" message (it's input TO Claude)
# - tool_use is in an "assistant" message (it's output FROM Claude)
# - tool_use_id MUST match between the call and the result
# - Each API call resends the ENTIRE conversation (stateless)


# =============================================================================
# TOOL USE vs AGENT - THE DISTINCTION
# =============================================================================
#
# TOOL USE (not an agent):
#   User asks question -> Claude calls tool -> Result -> Claude answers
#   ONE round. Fixed. Predictable. Like a calculator.
#
# AGENT (built on tool use):
#   User gives task -> Claude calls tool -> Result ->
#   Claude decides: need more info? -> calls another tool -> Result ->
#   Claude decides: ready to answer -> Final response
#   MULTIPLE rounds. Dynamic. Claude drives the workflow.
#
# The while loop in agent_loop() above IS the agent. Without the loop,
# it's just tool use. The loop + Claude's decision-making = agent.
#
# PRODUCTION AGENTS add:
#   - Max iteration limits (prevent infinite loops)
#   - Token budget tracking
#   - Error recovery and retry logic
#   - Timeout handling
#   - Logging and observability

def production_agent_loop(user_message: str, max_iterations: int = 10):
    """A more robust agent loop with safety guardrails."""
    agent_tools = make_tools_for_agent()
    messages = [{"role": "user", "content": user_message}]
    iterations = 0

    while iterations < max_iterations:
        iterations += 1
        print(f"\n--- Iteration {iterations} ---")

        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=4096,
            tools=agent_tools,
            messages=messages,
        )

        # Done - Claude gave a final answer
        if response.stop_reason == "end_turn":
            answer = next((b.text for b in response.content if b.type == "text"), "")
            print(f"[Done in {iterations} iterations]")
            return answer

        # Token limit hit
        if response.stop_reason == "max_tokens":
            print("[Hit max_tokens - stopping]")
            return next((b.text for b in response.content if b.type == "text"), "")

        # Refusal
        if response.stop_reason == "refusal":
            print("[Claude refused the request]")
            return None

        # Tool use - execute and continue
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        result = execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "is_error": True,
                            "content": str(e)
                        })

            messages.append({"role": "user", "content": tool_results})

    print(f"[Hit max iterations ({max_iterations})]")
    return None


# =============================================================================
# QUICK REFERENCE CHEAT SHEET
# =============================================================================
#
#  TOOL DEFINITION SCHEMA:
#    {
#      "name": "snake_case_name",
#      "description": "When and why to use this tool",
#      "strict": True,              # optional - guarantees valid input
#      "input_schema": {
#        "type": "object",
#        "properties": { ... },
#        "required": ["param1"],
#        "additionalProperties": false  # required if strict: True
#      }
#    }
#
#  STOP REASONS:
#    "end_turn"   -> Claude is done, read the text
#    "tool_use"   -> Claude wants to call a tool, execute it
#    "max_tokens" -> Output was truncated
#    "refusal"    -> Safety refusal, check stop_details
#    "pause_turn" -> Server tool paused, can resume
#
#  TOOL_RESULT BLOCK:
#    {"type": "tool_result", "tool_use_id": "must_match", "content": "..."}
#    {"type": "tool_result", "tool_use_id": "...", "is_error": True, "content": "error msg"}
#
#  AGENT LOOP PATTERN:
#    while True:
#        response = client.messages.create(tools=..., messages=...)
#        if response.stop_reason == "end_turn": break
#        if response.stop_reason == "tool_use":
#            execute tools, append results, continue loop
#
#  TOOL_CHOICE (modern models):
#    {"type": "auto"}  -> Claude decides (USE THIS)
#    {"type": "none"}  -> No tools allowed
#    "any" / "tool"    -> REMOVED on Opus 5.5, Sonnet 5.5, Fable 5.1
#
#  PARALLEL CALLS:
#    One response can have multiple tool_use blocks.
#    Execute ALL, return ALL in ONE user message.
#
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Tool Use Demo")
    print("=" * 60)
    print("\nRun individual functions to test each concept:")
    print("  demonstrate_tool_call()    - see a tool_use response")
    print("  execute_and_return()       - full single-round cycle")
    print("  single_tool_use()          - complete one-shot tool use")
    print("  agent_loop(msg)            - the agentic loop")
    print("  production_agent_loop(msg) - robust loop with guardrails")
    print("\nRequires: pip install anthropic")
    print("Requires: ANTHROPIC_API_KEY environment variable")
