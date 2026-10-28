## Agent Build Order

The build order implied by the dependencies runs **bottom-up** — we build the lower layers first because each higher layer depends on the one below it.

### Build order:

1. **Tool functions** — the actual code that does the work (e.g., a function that calls a weather API)
2. **Tool schemas** — the JSON descriptions of those tools so Claude knows what's available and what parameters to pass
3. **Message handling** — how you send messages to Claude and process responses (including tool_use and tool_result blocks)
4. **The loop** — the agentic while loop that keeps running until Claude stops calling tools (`while stop_reason == "tool_use"`)
5. **Agent-level settings** — top-level configuration like model, max_tokens, system prompt, thinking, effort

### Why bottom-up?

The dependencies run bottom-up: the loop depends on message handling, message handling depends on tool schemas, and tool schemas depend on tool functions. You can't write the loop without knowing how messages work, and you can't write schemas without having the functions they describe.
