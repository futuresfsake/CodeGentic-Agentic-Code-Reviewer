# Claude Developer Certification – Module 2 Practice

Study notes and runnable examples from Module 2 of my Claude Developer Certification preparation. The focus is on how the Claude API works under the hood: extended thinking, tool use, and how those pieces combine into an agent.

## Contents

| File | What it covers |
|------|----------------|
| [`01_extended_thinking.py`](01_extended_thinking.py) | Extended thinking: adaptive thinking vs. legacy `budget_tokens`, effort levels, display modes, thinking blocks in multi-turn conversations, streaming with thinking, and model-specific rules. |
| [`02_tool_use.py`](02_tool_use.py) | Tool use: defining tool schemas, the 6-step tool use cycle (`tool_use` → `tool_result`), calling patterns, and how a tool-use loop turns into an agent. |
| [`extended_thinking.md`](extended_thinking.md) | Short notes on configuring thinking through JSON objects (`thinking`, `output_config`) passed to the Messages API. |
| [`agent_build_order.md`](agent_build_order.md) | The bottom-up order for building an agent: tool functions → tool schemas → message handling → the loop → agent-level settings. |

## Key ideas

- **Adaptive thinking** lets Claude decide when and how deeply to think; `output_config.effort` controls depth.
- **Tool use is the mechanism, the loop is the agent.** Claude only *requests* a tool call; your code runs it and returns a `tool_result`. Looping while `stop_reason == "tool_use"` is what makes the system agentic.
- **Build agents bottom-up**, since each layer depends on the one below it.

## Running the examples

```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key-here"   # PowerShell: $env:ANTHROPIC_API_KEY="your-key-here"
python 01_extended_thinking.py
python 02_tool_use.py
```

## Resources

- [Claude API docs](https://platform.claude.com/docs)
