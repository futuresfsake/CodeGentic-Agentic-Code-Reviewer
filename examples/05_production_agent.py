"""
==============================================================================
MODULE 2: BUILDING A PRODUCTION AGENT
==============================================================================

OFFICIAL DOCUMENTATION:
  - Tool Use Overview:          https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md
  - Managed Agents Overview:    https://platform.claude.com/docs/en/managed-agents/overview.md
  - Managed Agents Quickstart:  https://platform.claude.com/docs/en/managed-agents/quickstart.md
  - Managed Agents Sessions:    https://platform.claude.com/docs/en/managed-agents/sessions.md
  - Managed Agents Events:      https://platform.claude.com/docs/en/managed-agents/events-and-streaming.md
  - Claude Agent SDK:           https://code.claude.com/docs/en/agent-sdk

Three wiring paths, same core pattern: loop until done.

  1. Messages API  — you run the loop, you run the tools
  2. Agent SDK     — SDK runs the loop with built-in tools, you host it
  3. Managed Agents — Anthropic runs the loop AND hosts the container

==============================================================================
"""

import anthropic
import json

client = anthropic.Anthropic()


# =============================================================================
# WIRING PATH 1: MESSAGES API — MANUAL LOOP
# =============================================================================
# You write the while loop. You define tools. You execute them.
# Maximum control, maximum code.

# --- Tool definitions ---
tools = [
    {
        "name": "search_docs",
        "description": "Search internal documentation by keyword. Use when the user asks about company processes or policies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results (1-10)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "create_ticket",
        "description": "Create a support ticket. Use when the user wants to report an issue or request help.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
            },
            "required": ["title", "description", "priority"]
        }
    },
    {
        "name": "send_email",
        "description": "Send an email notification. Use when the user asks to notify someone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["to", "subject", "body"]
        }
    }
]


# --- Tool implementations ---
def execute_tool(name: str, args: dict) -> str:
    """Dispatch tool calls to real functions."""
    if name == "search_docs":
        return json.dumps({
            "results": [
                {"title": "Password Reset Policy", "snippet": "Users can reset via SSO..."},
                {"title": "Escalation Process", "snippet": "Critical issues go to on-call..."}
            ]
        })
    elif name == "create_ticket":
        return json.dumps({"ticket_id": "TICK-1234", "status": "created"})
    elif name == "send_email":
        return json.dumps({"status": "sent", "to": args["to"]})
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


# --- Human-in-the-loop approval ---
DANGEROUS_TOOLS = {"send_email", "create_ticket"}


def requires_approval(tool_name: str) -> bool:
    """Check if a tool needs human approval before running."""
    return tool_name in DANGEROUS_TOOLS


def get_human_approval(tool_name: str, tool_input: dict) -> bool:
    """Ask a human to approve a tool call. In production, this would
    be a UI prompt, Slack message, API call, etc."""
    print(f"\n⚠ APPROVAL REQUIRED: {tool_name}")
    print(f"  Arguments: {json.dumps(tool_input, indent=2)}")
    response = input("  Approve? (y/n): ").strip().lower()
    return response == "y"


# --- The agent loop with human-in-the-loop ---
def messages_api_agent(user_message: str, max_iterations: int = 10):
    """
    WIRING PATH 1: Messages API agent with human-in-the-loop.

    The loop pattern:
      1. Call API with tools + messages
      2. If stop_reason == "end_turn" → done
      3. If stop_reason == "tool_use" → execute tools, continue
      4. Human-in-the-loop: approve dangerous actions before executing
    """
    messages = [{"role": "user", "content": user_message}]
    iterations = 0

    while iterations < max_iterations:
        iterations += 1
        print(f"\n--- Iteration {iterations} ---")

        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )

        # Done
        if response.stop_reason == "end_turn":
            answer = next((b.text for b in response.content if b.type == "text"), "")
            print(f"\n✓ Agent finished in {iterations} iterations")
            print(f"Answer: {answer}")
            return answer

        # Max tokens or refusal
        if response.stop_reason in ("max_tokens", "refusal"):
            print(f"[Stopped: {response.stop_reason}]")
            return None

        # Tool use — the core of the agent loop
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":

                    # HUMAN-IN-THE-LOOP: approve dangerous tools
                    if requires_approval(block.name):
                        approved = get_human_approval(block.name, block.input)
                        if not approved:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "is_error": True,
                                "content": "Action denied by human operator."
                            })
                            continue

                    # Execute the tool
                    print(f"  → {block.name}({json.dumps(block.input)})")
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
# WIRING PATH 1b: MESSAGES API — TOOL RUNNER
# =============================================================================
# Same wiring path, but the SDK runs the loop for you.
# You just define the tool functions with @beta_tool decorator.

from anthropic import beta_tool


@beta_tool(description="Search internal docs by keyword.")
def search_docs_runner(query: str, max_results: int = 5) -> str:
    return json.dumps({
        "results": [{"title": "Policy Doc", "snippet": "Found relevant info..."}]
    })


@beta_tool(description="Create a support ticket.")
def create_ticket_runner(title: str, description: str, priority: str) -> str:
    return json.dumps({"ticket_id": "TICK-5678", "status": "created"})


def tool_runner_agent(user_message: str):
    """
    WIRING PATH 1b: Tool Runner — SDK runs the loop.

    You define tools with @beta_tool, the runner handles:
      - Calling the API
      - Checking stop_reason
      - Executing your functions
      - Sending results back
      - Looping until done
    """
    runner = client.beta.messages.tool_runner(
        model="claude-opus-5-5",
        max_tokens=4096,
        tools=[search_docs_runner, create_ticket_runner],
        messages=[{"role": "user", "content": user_message}],
    )
    response = runner.until_done()

    answer = next((b.text for b in response.content if b.type == "text"), "")
    print(f"Answer: {answer}")
    return response


# =============================================================================
# WIRING PATH 3: MANAGED AGENTS
# =============================================================================
# Anthropic runs the loop AND hosts the container.
# You create an Agent (once), then start Sessions (every run).
#
# Agent = persisted, versioned config (model, system, tools)
# Session = one run of the agent
# Events = SSE stream of what the agent does
#
# The mandatory flow: Agent (once) → Session (every run)


def managed_agent_setup():
    """
    WIRING PATH 3: Create a Managed Agent.

    This is ONE-TIME SETUP. Store the agent.id and reuse it.
    Do NOT call agents.create() on every run.
    """

    # 1. Create environment (where tools execute)
    environment = client.beta.environments.create(
        name="my-dev-env",
        config={
            "type": "cloud",
            "networking": {
                "type": "limited",
                "allow_package_managers": True,
                "allow_mcp_servers": True,
            },
        },
    )
    print(f"Environment: {environment.id}")

    # 2. Create agent (persisted, versioned)
    agent = client.beta.agents.create(
        name="Support Agent",
        model="claude-opus-5-5",
        system="You are a helpful support agent. Search docs before answering.",
        tools=[
            {
                "type": "agent_toolset_20260401",
                "default_config": {
                    "enabled": True,
                    "permission_policy": {"type": "auto"},
                },
                "configs": [
                    {"name": "web_fetch", "enabled": False},
                    {"name": "web_search", "enabled": False},
                ],
            },
        ],
    )
    print(f"Agent: {agent.id} (version: {agent.version})")

    return agent, environment


def managed_agent_run(agent_id: str, agent_version: str, environment_id: str, task: str):
    """
    WIRING PATH 3: Run a Managed Agent session.

    This is EVERY RUN. Uses the stored agent_id.
    Anthropic runs the loop — you just stream events.
    """

    # 1. Create session (references the pre-created agent)
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": agent_id, "version": agent_version},
        environment_id=environment_id,
    )
    print(f"Session: {session.id} ({session.status})")

    # 2. Stream events — open stream FIRST, then send message
    with client.beta.sessions.events.stream(
        session_id=session.id,
    ) as stream:
        # Send the user message while stream is open
        client.beta.sessions.events.send(
            session_id=session.id,
            events=[{
                "type": "user.message",
                "content": [{"type": "text", "text": task}],
            }],
        )

        # 3. Process events as they arrive
        for event in stream:
            # Agent's text output
            if event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        print(block.text, end="", flush=True)

            # HUMAN-IN-THE-LOOP: tool needs approval
            elif event.type in ("agent.tool_use", "agent.mcp_tool_use"):
                if hasattr(event, "evaluated_permission") and event.evaluated_permission == "ask":
                    print(f"\n⚠ Tool approval needed: {event.name}")
                    approved = input("  Approve? (y/n): ").strip().lower() == "y"
                    client.beta.sessions.events.send(
                        session_id=session.id,
                        events=[{
                            "type": "user.tool_confirmation",
                            "tool_use_id": event.id,
                            "result": "allow" if approved else "deny",
                        }],
                    )

            # Custom tool call — your code executes it
            elif event.type == "agent.custom_tool_use":
                print(f"\n[Custom tool: {event.name}({json.dumps(event.input)})]")
                result = execute_tool(event.name, event.input)
                client.beta.sessions.events.send(
                    session_id=session.id,
                    events=[{
                        "type": "user.custom_tool_result",
                        "custom_tool_use_id": event.id,
                        "content": [{"type": "text", "text": result}],
                    }],
                )

            # Session done
            elif event.type == "session.status_idle":
                if event.stop_reason.type != "requires_action":
                    print("\n\n--- Session idle ---")
                    break

            elif event.type == "session.status_terminated":
                print("\n\n--- Session terminated ---")
                break

    return session.id


# =============================================================================
# MULTI-AGENT: PIPELINE PATTERN (Messages API)
# =============================================================================
# Agent A → Agent B → Agent C
# Output of one agent feeds into the next.

def pipeline_agent():
    """
    Multi-agent pipeline: Research → Write → Edit

    Each agent has its own loop, tools, and system prompt.
    The output of one becomes the input of the next.
    """

    # Agent 1: Researcher
    research_result = run_single_agent(
        system="You are a research agent. Gather key facts and return them as bullet points.",
        tools=[],  # could have search_docs, web_search, etc.
        task="Research the benefits of microservices architecture."
    )

    # Agent 2: Writer (receives research output)
    draft = run_single_agent(
        system="You are a technical writer. Write a clear blog post from the research provided.",
        tools=[],
        task=f"Write a blog post based on this research:\n\n{research_result}"
    )

    # Agent 3: Editor (receives draft)
    final = run_single_agent(
        system="You are an editor. Fix grammar, improve clarity, and tighten the writing.",
        tools=[],
        task=f"Edit this blog post:\n\n{draft}"
    )

    return final


def run_single_agent(system: str, tools: list, task: str) -> str:
    """Helper: run a single agent loop and return its text output."""
    messages = [{"role": "user", "content": task}]

    while True:
        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=4096,
            system=system,
            tools=tools if tools else None,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return next((b.text for b in response.content if b.type == "text"), "")

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            return next((b.text for b in response.content if b.type == "text"), "")


# =============================================================================
# MULTI-AGENT: ORCHESTRATOR + WORKERS (Messages API)
# =============================================================================
# One agent delegates subtasks to worker agents.

def orchestrator_agent(task: str):
    """
    Orchestrator pattern: a lead agent delegates to workers.

    The orchestrator decides what subtasks to create,
    workers execute them, orchestrator combines results.
    """
    # Step 1: Orchestrator plans subtasks
    plan = run_single_agent(
        system=(
            "You are a project planner. Break the task into 2-3 independent subtasks. "
            "Return each subtask on its own line, prefixed with '- '."
        ),
        tools=[],
        task=task
    )

    print(f"Plan:\n{plan}\n")
    subtasks = [line.strip("- ").strip() for line in plan.strip().split("\n") if line.strip().startswith("-")]

    # Step 2: Workers execute subtasks in parallel (simplified as sequential here)
    worker_results = []
    for i, subtask in enumerate(subtasks):
        print(f"Worker {i+1}: {subtask}")
        result = run_single_agent(
            system="You are a focused worker agent. Complete the assigned task thoroughly.",
            tools=[],
            task=subtask
        )
        worker_results.append(f"## Subtask: {subtask}\n{result}")

    # Step 3: Orchestrator combines results
    combined = "\n\n".join(worker_results)
    final = run_single_agent(
        system="You are a synthesizer. Combine these worker results into one coherent response.",
        tools=[],
        task=f"Combine these results into a final answer:\n\n{combined}"
    )

    return final


# =============================================================================
# SUMMARY: THE THREE WIRING PATHS
# =============================================================================
#
#  MESSAGES API (manual loop):
#    - You write the while loop
#    - You define and execute tools
#    - Maximum control
#    - Use: custom agents, quick prototypes
#
#  MESSAGES API (Tool Runner):
#    - SDK runs the loop via @beta_tool + tool_runner()
#    - You define tool functions, SDK handles the rest
#    - Use: custom-tool agents without writing the loop
#
#  AGENT SDK (separate package):
#    - Claude Code as a library
#    - Built-in tools (file, bash, grep, web search)
#    - You host and deploy
#    - Use: coding/filesystem agents
#    - Docs: https://code.claude.com/docs/en/agent-sdk
#
#  MANAGED AGENTS:
#    - Anthropic runs loop + hosts container
#    - Agent config is persisted and versioned
#    - Sessions stream events via SSE
#    - Built-in permission policies for human-in-the-loop
#    - Use: production agents, scheduled runs, long-running tasks
#    - Docs: https://platform.claude.com/docs/en/managed-agents/overview.md
#
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Production Agent Demo")
    print("=" * 60)
    print("\nWiring Path 1 — Messages API:")
    print("  messages_api_agent('Help me report a login bug')")
    print("  tool_runner_agent('Search for password reset policy')")
    print("\nWiring Path 3 — Managed Agents:")
    print("  agent, env = managed_agent_setup()")
    print("  managed_agent_run(agent.id, agent.version, env.id, 'Do the task')")
    print("\nMulti-Agent:")
    print("  pipeline_agent()")
    print("  orchestrator_agent('Write a guide on API security')")
    print("\nRequires: pip install anthropic")
    print("Requires: ANTHROPIC_API_KEY environment variable")
