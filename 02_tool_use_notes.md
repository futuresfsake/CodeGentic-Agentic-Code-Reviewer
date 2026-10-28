# Module 2: Tool Use & Schema Design

## Official Documentation
- [Tool Use Overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md)
- [Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md)
- [Extended Thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking.md)
- [Adaptive Thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking.md)
- [Effort Parameter](https://platform.claude.com/docs/en/build-with-claude/effort.md)
- [Streaming](https://platform.claude.com/docs/en/build-with-claude/streaming.md)
- [Models Overview](https://platform.claude.com/docs/en/about-claude/models/overview.md)
- [Migration Guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide.md)
- [Errors](https://platform.claude.com/docs/en/api/errors.md)

---

## Tool Schemas = LLM-Powered Application

The moment you define tool schemas and wire them into Claude API calls, your application becomes an **LLM-powered application**. The tool schema is the bridge between Claude's intelligence and your application's capabilities.

- **Without tools**: your app sends text to Claude, gets text back. That's just a chatbot wrapper.
- **With tools**: Claude can **take actions** in your system — query databases, call APIs, create records, send emails. Now Claude is the brain driving your application's features.

### The Spectrum

| Level | Description |
|---|---|
| Plain app | No LLM. Just code. |
| Chatbot wrapper | LLM generates text. No tools. |
| LLM-powered app | LLM + tools. Claude calls YOUR functions. |
| Agent | LLM + tools + loop. Claude drives the workflow. |

### The Contract

Tool schemas are the **contract** between the two sides:
- **Claude's side**: reads the schema to know what's available and how to call it
- **Your app's side**: reads Claude's `tool_use` block and dispatches to real functions

A bad schema means Claude can't use your app's features correctly, no matter how good the underlying functions are.

---

## What Is Tool Use?

Tool use is the **general act** of Claude picking up and using any tool.

It doesn't mean one specific tool. It's the entire mechanism — Claude looks at the tools available, decides which one fits the user's request, and asks your code to run it. Like a person in a workshop picking the right tool off the wall.

- **"Tool use"** = the capability of selecting and calling tools
- **"A tool"** = one specific function you've defined (get_weather, etc.)
- **`tool_use`** = the API block type Claude returns when it picks a tool

---

## The 6-Step Tool Use Cycle

```
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
```

| Step | What happens | Who does it |
|---|---|---|
| 1. **Define** | Define tools with `name`, `description`, `input_schema` | You (developer) |
| 2. **Send** | Send user message + tool definitions to Claude | Your code |
| 3. **Receive** | Claude responds with a `tool_use` block (`stop_reason: "tool_use"`) containing tool name, unique id, and input arguments | Claude API |
| 4. **Execute** | Run the actual function using those arguments | Your code |
| 5. **Return** | Send a `tool_result` block referencing the original `tool_use` id | Your code |
| 6. **Continue** | Claude reads the result and responds (or calls another tool) | Claude API |

**Key insight**: The API is **stateless** between calls. Every request must include the full conversation history. Your code keeps the state, not Claude.

---

## Tool Use vs Agent

| | Tool Use | Agent |
|---|---|---|
| **What** | One round of tool calling | Multi-round, looping tool calls |
| **Flow** | User → Claude calls tool → result → answer | User → Claude calls tool → result → decides next step → calls another tool → ... → answer |
| **Who decides** | Fixed, predictable | Claude drives the workflow |
| **Analogy** | Using a calculator once | Building a house, picking which tools to use |
| **Code pattern** | Single API call + one tool execution | `while stop_reason == "tool_use": keep going` |

The **loop** is what makes it agentic. Without the loop, it's just tool use.

---

## Tool Definition — Fixed Structure

The top-level structure is **fixed by the API**. You cannot rename these fields.

```json
{
    "name":         "REQUIRED - identifier Claude uses to call it",
    "description":  "REQUIRED - tells Claude WHEN and WHY to use it",
    "input_schema": "REQUIRED - JSON Schema defining the parameters",

    "strict":                true,
    "eager_input_streaming": true,
    "cache_control":         {"type": "ephemeral"},
    "defer_loading":         true
}
```

### What you CAN'T customize
- The field names (`name` can't become `tool_name`, `description` can't become `info`)
- `input_schema` must be `"type": "object"` at the top level
- If `strict: true`, you must have `"additionalProperties": false` and all props in `"required"`

### What you CAN customize
- The **value** of `name` (any snake_case string)
- The **value** of `description` (whatever helps Claude decide)
- Everything **inside** `input_schema.properties` — your parameters, types, enums, nested objects, arrays

The `input_schema` is **your space**. It defines what arguments your tool accepts, expressed as JSON Schema. It's like a function signature for Claude to read.

---

## input_schema Basics

The `input_schema` tells Claude: "when you call this tool, here's what you can pass."

```python
# This function signature...
def get_weather(city: str, unit: str = "fahrenheit"):

# ...becomes this input_schema:
{
    "type": "object",
    "properties": {
        "city": {"type": "string", "description": "City name"},
        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
    },
    "required": ["city"]
}
```

### Supported types
`string`, `number`, `integer`, `boolean`, `array`, `object`, `null`

### Useful keywords
| Keyword | Purpose | Example |
|---|---|---|
| `enum` | Restrict to specific values | `["celsius", "fahrenheit"]` |
| `description` | Tells Claude what this param is for | `"City name, e.g. 'Tokyo'"` |
| `items` | Schema for array elements | `{"type": "string"}` |
| `minimum` / `maximum` | Number range | `"minimum": 1, "maximum": 50` |
| `pattern` | Regex for strings | `"^[A-Z]{2}$"` |
| `required` | Which params are mandatory | `["city"]` |
| `additionalProperties` | Block extra fields (needed for strict) | `false` |

---

## tool_choice — Controlling When Claude Uses Tools

| Value | Behavior | Notes |
|---|---|---|
| `{"type": "auto"}` | Claude decides. **DEFAULT. Always use this.** | Works everywhere |
| `{"type": "any"}` | Must call a tool | **REMOVED** on Opus 5.5, Sonnet 5.5, Fable 5.1 (400 error) |
| `{"type": "tool", "name": "..."}` | Must call this specific tool | **Also REMOVED** on those models |
| `{"type": "none"}` | Never call tools | Still works everywhere |

On modern models: use `auto` + an instruction in the prompt + `strict: true`.

---

## Stop Reasons

| Value | Meaning | What to do |
|---|---|---|
| `end_turn` | Claude is done | Read the text, you're finished |
| `tool_use` | Claude wants to call a tool | Execute it, return result, continue |
| `max_tokens` | Output was truncated | Increase `max_tokens` or stream |
| `refusal` | Safety refusal | Check `stop_details` |
| `pause_turn` | Server tool paused | Can resume |

---

## Parallel Tool Calls

Claude can call **multiple tools in one response**. One assistant message may contain several `tool_use` blocks.

**Rule**: Execute ALL of them and return ALL results in **ONE user message**. Splitting them into multiple messages trains Claude to stop making parallel calls.

---

## Error Handling

If a tool fails, return `tool_result` with `is_error: true`. Never drop the result.

```json
{
    "type": "tool_result",
    "tool_use_id": "toolu_abc123",
    "is_error": true,
    "content": "Error: city not found"
}
```

---

## Conversation History Shape

After a tool use cycle, messages look like this:

```
1. user:      "What's the weather in Tokyo?"
2. assistant: [text: "Let me check.", tool_use: {id: "toolu_abc", name: "get_weather", input: {city: "Tokyo"}}]
3. user:      [tool_result: {tool_use_id: "toolu_abc", content: "{temp: 22, conditions: sunny}"}]
4. assistant: [text: "It's 22°C and sunny in Tokyo!"]
```

- `tool_result` is in a **user** message (it's input TO Claude)
- `tool_use` is in an **assistant** message (it's output FROM Claude)
- `tool_use_id` **must match** between the call and the result
- Each API call resends the **entire conversation** (stateless)

---

## Extended Thinking Quick Reference

### Adaptive Thinking (current models)
```python
thinking={"type": "adaptive"}              # turn on thinking
thinking={"type": "adaptive", "display": "summarized"}  # see the reasoning
output_config={"effort": "high"}           # control depth
```

### Model Rules
| Model | Config | Default Effort |
|---|---|---|
| Fable 5/5.1 | Always on. Can't disable. No budget_tokens. | high |
| Opus 5.5 | Always on. Can't disable. No budget_tokens. | **medium** |
| Opus 5 | On by default. Disable OK at high or below. | high |
| Opus 4.8/4.7 | Must set adaptive explicitly. Disable OK. | high |
| Sonnet 5.5 | Always on. Use `between_tools` to turn off. | high |
| Haiku 5.5 | On by default. Disable OK at high or below. | **medium** |
| Haiku 4.5 (legacy) | `{"type": "enabled", "budget_tokens": N}` | N/A |

### What NOT to do
- `budget_tokens` → **400 error** on all models after Opus 4.6/Sonnet 4.6
- `temperature` / `top_p` / `top_k` → **400 error** on 4.6+ models
- Assistant prefill → **400 error** on 4.6+ models

---

## Schema Design Best Practices

1. **Descriptions are instructions** — not just metadata. Write: "Use this when ___. It does ___. It returns ___."
2. **Parameter descriptions matter** — `"City name, e.g. 'San Francisco'"` beats a bare `"city"` field
3. **Use enums for fixed choices** — Claude always picks from the list instead of guessing
4. **Mark required vs optional clearly** — only truly mandatory params in `required`
5. **Use strict mode for reliability** — when you need guaranteed valid input
6. **Keep schemas focused** — one tool = one job. Multiple focused tools > one giant tool
7. **Property descriptions as formatting hints** — `"date in ISO 8601 format"`, `"2-letter country code"`
