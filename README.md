# Claude Developer Certification – Module 2 Practice

Study notes and runnable examples from Module 2 of my Claude Developer Certification preparation. The focus is on how the Claude API works under the hood: extended thinking, tool use, and how those pieces combine into an agent.

## Project Structure

```
Module2Practice/
├── examples/          # Numbered concept implementations
│   ├── 01_extended_thinking.py
│   ├── 02_tool_use.py
│   ├── 03_tool_schema_design.py
│   ├── 04_streaming.py
│   ├── 05_production_agent.py
│   ├── 06_prompt_caching.py
│   ├── 07_structured_outputs.py
│   └── 08_error_handling.py
├── notes/             # Concept notes (matched by number)
│   ├── 01_extended_thinking.md
│   ├── 02_tool_use.md
│   ├── 02_agent_build_order.md
│   ├── 04_streaming.md
│   ├── 05_production_agent.md
│   ├── 06_prompt_caching.md
│   ├── 07_structured_outputs.md
│   └── 08_error_handling.md
├── project/           # Real project tying everything together
│   └── code_review_agent.py
└── README.md
```

## Code Examples (`examples/`)

| File | What it covers |
|------|----------------|
| [`01_extended_thinking.py`](examples/01_extended_thinking.py) | Adaptive thinking, effort levels, display modes, streaming with thinking, multi-turn, model-specific rules |
| [`02_tool_use.py`](examples/02_tool_use.py) | The 6-step tool use cycle, the agent loop, parallel calls, error handling, tool_choice |
| [`03_tool_schema_design.py`](examples/03_tool_schema_design.py) | Tool definition structure, input_schema anatomy, strict mode, simple → complex schema examples |
| [`04_streaming.py`](examples/04_streaming.py) | Streaming basics, streaming with thinking, streaming agent loop, error handling, async, `get_final_message()` |
| [`05_production_agent.py`](examples/05_production_agent.py) | Three wiring paths (Messages API, Agent SDK, Managed Agents), human-in-the-loop, multi-agent pipeline and orchestrator patterns |
| [`06_prompt_caching.py`](examples/06_prompt_caching.py) | Automatic and manual caching, multi-turn caching, caching with tools, silent invalidators |
| [`07_structured_outputs.py`](examples/07_structured_outputs.py) | `output_config.format`, `strict: true` on tools, extraction, nested schemas |
| [`08_error_handling.py`](examples/08_error_handling.py) | Exception chain, SDK auto-retry config, custom backoff, timeouts, robust agent loop |

## Notes (`notes/`)

| File | Related to | What it covers |
|------|------------|----------------|
| [`01_extended_thinking.md`](notes/01_extended_thinking.md) | `01_extended_thinking.py` | Configuring thinking through JSON objects (`thinking`, `output_config`) |
| [`02_tool_use.md`](notes/02_tool_use.md) | `02_tool_use.py`, `03_tool_schema_design.py` | Tool use concepts, the 6-step cycle, schema design, tool use vs agent, stop reasons, MCP, the LLM-powered app spectrum |
| [`02_agent_build_order.md`](notes/02_agent_build_order.md) | `02_tool_use.py` | Bottom-up order for building an agent: functions → schemas → messages → loop → settings |
| [`04_streaming.md`](notes/04_streaming.md) | `04_streaming.py` | Streaming concepts, SSE events, delta types, when streaming is required, error handling, gotchas |
| [`05_production_agent.md`](notes/05_production_agent.md) | `05_production_agent.py` | The agent is the loop, three wiring paths, single vs multi-agent, multi-agent patterns (pipeline, orchestrator, shared state, message passing), human-in-the-loop |
| [`06_prompt_caching.md`](notes/06_prompt_caching.md) | `06_prompt_caching.py` | Prefix match rule, render order, pricing, auto vs manual caching, silent invalidators, architectural rules |
| [`07_structured_outputs.md`](notes/07_structured_outputs.md) | `07_structured_outputs.py` | Two methods (`output_config.format` and `strict: true`), `messages.parse()`, when to use which |
| [`08_error_handling.md`](notes/08_error_handling.md) | `08_error_handling.py` | SDK auto-retry, exception hierarchy, common 400 errors, custom retry, timeouts |

## Real Project: Code Review Agent

[`project/code_review_agent.py`](project/code_review_agent.py) — A working agent that ties **every Module 2 concept** together:

| Concept | How it's used |
|---------|---------------|
| Extended Thinking | Adaptive thinking for deep code analysis |
| Tool Use | `list_files`, `read_file`, `search_pattern` tools with the agent loop |
| Tool Schema Design | Well-defined schemas with descriptions |
| Streaming | Real-time streamed output during review |
| Production Agent | `while` loop with max iterations and error tracking |
| Prompt Caching | System prompt + tools cached across all loop iterations |
| Structured Outputs | Final review returned as validated JSON via `output_config.format` |
| Error Handling | Specific exception chain, retry logic, consecutive error limits |

```bash
python project/code_review_agent.py my_script.py     # review a single file
python project/code_review_agent.py src/              # review a directory
```

## Running the examples

```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key-here"   # PowerShell: $env:ANTHROPIC_API_KEY="your-key-here"
python examples/01_extended_thinking.py
python examples/02_tool_use.py
python examples/03_tool_schema_design.py
```

## Resources

- [Claude API docs](https://platform.claude.com/docs)
