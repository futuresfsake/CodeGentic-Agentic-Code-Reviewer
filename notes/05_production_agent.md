# Module 2: Building a Production Agent

## Official Documentation
- [Tool Use Overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md)
- [Managed Agents Overview](https://platform.claude.com/docs/en/managed-agents/overview.md)
- [Managed Agents Quickstart](https://platform.claude.com/docs/en/managed-agents/quickstart.md)
- [Managed Agents Sessions](https://platform.claude.com/docs/en/managed-agents/sessions.md)
- [Managed Agents Events](https://platform.claude.com/docs/en/managed-agents/events-and-streaming.md)
- [Managed Agents Tools](https://platform.claude.com/docs/en/managed-agents/tools.md)
- [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk)
- [Streaming](https://platform.claude.com/docs/en/build-with-claude/streaming.md)
- [Models Overview](https://platform.claude.com/docs/en/about-claude/models/overview.md)

---

## Core Idea: The Agent IS the Loop

An agent is not a special API endpoint. It's a **loop** around the Messages API:

```
while stop_reason == "tool_use":
    execute tools → send results → call API again
```

Everything else — multi-agent, human-in-the-loop, orchestration — is built on top of this loop. The loop is the agent. Without it, you just have tool use.

---

## Wiring Paths: Three Ways to Build an Agent

The same agent loop concept can be implemented through **three different wiring paths**. The pattern (loop until done) is constant — what changes is who runs the loop and where tools execute.

| # | Wiring Path | Who runs the loop | Who runs the tools | You write |
|---|---|---|---|---|
| 1 | **Messages API** (manual or Tool Runner) | Your code | Your code | The loop + tool functions |
| 2 | **Claude Agent SDK** | The SDK (Claude Code as a library) | SDK's built-in tools + your code | Just a prompt + options |
| 3 | **Managed Agents** | Anthropic's orchestration | Anthropic's per-session container | Agent config, then send messages |

### Wiring Path 1: Messages API

You write the `while` loop yourself. You define tools, call `client.messages.create()`, check `stop_reason`, execute tools, send results back, repeat. Maximum control, maximum code.

**Two options within this path:**
- **Manual loop** — you write the entire `while stop_reason == "tool_use"` loop
- **Tool Runner** — `client.beta.messages.tool_runner()` runs the loop for you, you just define the tool functions

```python
# Manual loop: you own everything
while True:
    response = client.messages.create(model=..., tools=..., messages=...)
    if response.stop_reason == "end_turn": break
    # execute tools, append results, continue

# Tool Runner: SDK owns the loop, you own the tools
runner = client.beta.messages.tool_runner(model=..., tools=[...], messages=[...])
response = runner.until_done()
```

### Wiring Path 2: Claude Agent SDK

A separate package (`claude-agent-sdk` / `@anthropic-ai/claude-agent-sdk`) — Claude Code packaged as a library. Ships with built-in tools (file read/write/edit, bash, grep, web search). You call `query(prompt, options)` and it drives everything.

```python
from claude_agent_sdk import query

result = query(
    prompt="Refactor the auth module to use JWT",
    options={"tools": [...], "permissions": {...}}
)
```

- **Harness only** — you host and deploy it yourself
- Has built-in tools (filesystem, bash, grep, web search)
- Good for: coding/filesystem agents on your own infra
- Docs: https://code.claude.com/docs/en/agent-sdk

### Wiring Path 3: Managed Agents (CMA)

Anthropic runs the loop AND hosts a per-session container. You create a persisted Agent config, then start Sessions. The session streams events back to you.

```python
# ONE-TIME SETUP: Create the agent (persisted, versioned)
agent = client.beta.agents.create(
    name="My Agent",
    model="claude-opus-5-5",
    system="You are a helpful assistant.",
    tools=[{"type": "agent_toolset_20260401", ...}],
)

# EVERY RUN: Start a session
session = client.beta.sessions.create(
    agent={"type": "agent", "id": agent.id, "version": agent.version},
    environment_id=environment.id,
)

# Send a message and stream events
client.beta.sessions.events.send(session_id=session.id, events=[
    {"type": "user.message", "content": [{"type": "text", "text": "Do the task"}]}
])
```

- **Harness + deployment** — Anthropic runs loop AND hosts the container
- Agent is a persisted, versioned config (create once, reuse across runs)
- Sessions stream events via SSE
- Good for: long-running agents, scheduled runs, agents that need file/code execution

---

## Single Agent vs Multi-Agent

### Single Agent

One loop, one set of tools, one context. The pattern is the same regardless of wiring path — only the implementation changes.

```
User → Agent Loop → Tools → Result → Agent Loop → ... → Final Answer
```

### Multi-Agent

Two or more agents, each with its **own loop, rules, and context**, working on one task. Multi-agent is NOT a fixed definition — it's a set of patterns for how agents coordinate.

**Common arrangement (not the only one):**
- **Planner** — breaks the task into steps
- **Executor** — carries out each step
- **Evaluator** — checks if the result meets quality bar

But this is one arrangement, not THE definition.

---

## Multi-Agent Patterns

| Pattern | How it works | Example |
|---|---|---|
| **Pipeline** | Agent A → Agent B → Agent C. Output of one feeds into the next, in sequence. | Research → Write → Edit |
| **Orchestrator + Workers** | One agent delegates subtasks to worker agents and combines results. | Lead agent assigns "check API", "check DB", "check UI" to three workers |
| **Shared State** | Agents read/write a common data store. No direct communication. | Multiple agents write to a shared file or database |
| **Message Passing** | Agents send messages to each other. Direct communication. | Planner sends instructions to Executor, Executor reports back |

### Pipeline
```
Agent A ──output──► Agent B ──output──► Agent C ──output──► Final
```
Each agent has its own loop. Output of A becomes input of B. Simple, linear.

### Orchestrator + Workers
```
                    ┌── Worker A ──┐
User ──► Orchestrator ──── Worker B ──── Orchestrator ──► Final
                    └── Worker C ──┘
```
Orchestrator decides what to delegate. Workers run in parallel or sequence.

### Shared State
```
Agent A ──┐                ┌── Agent A
          ├── Shared DB ◄──┤
Agent B ──┘                └── Agent B
```
No direct communication. Agents coordinate through a shared resource.

### Message Passing
```
Planner ◄──messages──► Executor ◄──messages──► Evaluator
```
Agents talk directly. Most flexible, most complex.

---

## Human in the Loop

Human-in-the-loop means a person can **approve, deny, or redirect** agent actions before they execute. This is critical for production agents that take real-world actions (sending emails, modifying databases, deploying code).

### In Messages API
You add approval logic in the tool execution step:

```python
if requires_approval(tool_name, tool_input):
    approved = ask_human(f"Allow {tool_name}({tool_input})?")
    if not approved:
        result = "Action denied by user"
```

### In Managed Agents
Built-in via permission policies on tools:

| Policy | Behavior |
|---|---|
| `always_allow` | Tool runs automatically, no human check |
| `always_ask` | Always pauses for human approval |
| `auto` | Server evaluates risk: runs low-risk, pauses indeterminate, denies high-risk |

When a tool pauses, the session emits a `user.tool_confirmation` event. Your code (or a human) responds with `allow` or `deny`.

---

## Choosing a Wiring Path

| You need... | Use |
|---|---|
| Maximum control over the loop | Messages API (manual loop) |
| Agent loop without writing it | Messages API (Tool Runner) |
| Coding/filesystem agent on your infra | Claude Agent SDK |
| Anthropic-hosted container + managed loop | Managed Agents |
| Scheduled/recurring agent runs | Managed Agents (deployments) |
| Versioned, persistent agent configs | Managed Agents |
| Quick prototype | Messages API (simplest code) |

---

## Key Takeaways

1. **The agent is the loop.** The `while stop_reason == "tool_use"` loop is what makes it agentic.
2. **The pattern is constant across wiring paths.** Loop until done. Only who runs the loop changes.
3. **Multi-agent = multiple agents, each with its own loop, rules, and context.**
4. **Planner/Executor/Evaluator is one arrangement, not the definition.** The main patterns are pipeline, orchestrator+workers, shared state, message passing.
5. **Three wiring paths**: Messages API, Agent SDK, Managed Agents. Same concept, different implementations.
6. **Human-in-the-loop** is an approval gate inside the loop — in Messages API you code it, in Managed Agents it's built in via permission policies.
