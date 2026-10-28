# Claude Developer Certification – Module 2 Practice

Study notes and runnable examples from Module 2 of my Claude Developer Certification preparation. The focus is on how the Claude API works under the hood: extended thinking, tool use, and how those pieces combine into an agent.

## Code Examples

| File | What it covers |
|------|----------------|
| [`01_extended_thinking.py`](01_extended_thinking.py) | Adaptive thinking, effort levels, display modes, streaming with thinking, multi-turn, model-specific rules |
| [`02_tool_use.py`](02_tool_use.py) | The 6-step tool use cycle, the agent loop, parallel calls, error handling, tool_choice |
| [`03_tool_schema_design.py`](03_tool_schema_design.py) | Tool definition structure, input_schema anatomy, strict mode, simple → complex schema examples |
| [`04_streaming.py`](04_streaming.py) | Streaming basics, streaming with thinking, streaming agent loop, error handling, async, `get_final_message()` |
| [`05_production_agent.py`](05_production_agent.py) | Three wiring paths (Messages API, Agent SDK, Managed Agents), human-in-the-loop, multi-agent pipeline and orchestrator patterns |
| [`06_prompt_caching.py`](06_prompt_caching.py) | Automatic and manual caching, multi-turn caching, caching with tools, silent invalidators |
| [`07_structured_outputs.py`](07_structured_outputs.py) | `output_config.format`, `strict: true` on tools, extraction, nested schemas |
| [`08_error_handling.py`](08_error_handling.py) | Exception chain, SDK auto-retry config, custom backoff, timeouts, robust agent loop |

## Notes

| File | Related to | What it covers |
|------|------------|----------------|
| [`notes/01_extended_thinking.md`](notes/01_extended_thinking.md) | `01_extended_thinking.py` | Configuring thinking through JSON objects (`thinking`, `output_config`) |
| [`notes/02_tool_use.md`](notes/02_tool_use.md) | `02_tool_use.py`, `03_tool_schema_design.py` | Tool use concepts, the 6-step cycle, schema design, tool use vs agent, stop reasons, MCP, the LLM-powered app spectrum |
| [`notes/02_agent_build_order.md`](notes/02_agent_build_order.md) | `02_tool_use.py` | Bottom-up order for building an agent: functions → schemas → messages → loop → settings |
| [`notes/04_streaming.md`](notes/04_streaming.md) | `04_streaming.py` | Streaming concepts, SSE events, delta types, when streaming is required, error handling, gotchas |
| [`notes/05_production_agent.md`](notes/05_production_agent.md) | `05_production_agent.py` | The agent is the loop, three wiring paths, single vs multi-agent, multi-agent patterns (pipeline, orchestrator, shared state, message passing), human-in-the-loop |
| [`notes/06_prompt_caching.md`](notes/06_prompt_caching.md) | `06_prompt_caching.py` | Prefix match rule, render order, pricing, auto vs manual caching, silent invalidators, architectural rules |
| [`notes/07_structured_outputs.md`](notes/07_structured_outputs.md) | `07_structured_outputs.py` | Two methods (`output_config.format` and `strict: true`), `messages.parse()`, when to use which |
| [`notes/08_error_handling.md`](notes/08_error_handling.md) | `08_error_handling.py` | SDK auto-retry, exception hierarchy, common 400 errors, custom retry, timeouts |

## Running the examples

```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key-here"   # PowerShell: $env:ANTHROPIC_API_KEY="your-key-here"
python 01_extended_thinking.py
python 02_tool_use.py
python 03_tool_schema_design.py
```

## Resources

- [Claude API docs](https://platform.claude.com/docs)
