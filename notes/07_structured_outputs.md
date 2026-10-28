# Module 2: Structured Outputs

## Official Documentation
- [Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md)
- [Tool Use Overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md)

---

## What Are Structured Outputs?

Structured outputs force Claude to return data in a **specific JSON shape** you define. Instead of free-form text, you get validated JSON that matches your schema every time.

Two ways to get structured output:
1. **`output_config.format`** — constrains the entire response format (recommended)
2. **`strict: true` on tools** — guarantees tool inputs match the schema

---

## Method 1: output_config.format (Recommended)

Force Claude's entire response into a JSON schema:

```python
response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=4096,
    output_config={
        "format": {
            "type": "json_schema",
            "json_schema": {
                "name": "analysis_result",
                "schema": {
                    "type": "object",
                    "properties": {
                        "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
                        "confidence": {"type": "number"},
                        "key_phrases": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["sentiment", "confidence", "key_phrases"],
                    "additionalProperties": False
                }
            }
        }
    },
    messages=[{"role": "user", "content": "Analyze: 'This product is amazing!'"}]
)
```

The response text is guaranteed valid JSON matching your schema.

**Note**: `output_config.format` replaces the deprecated `output_format` parameter.

---

## Method 2: strict: true on Tools

Guarantees that `tool_use.input` always validates against the schema:

```python
tools = [{
    "name": "classify",
    "description": "Classify the input text",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": ["bug", "feature", "question"]},
            "severity": {"type": "integer", "minimum": 1, "maximum": 5}
        },
        "required": ["category", "severity"],
        "additionalProperties": False
    }
}]
```

Requirements for `strict: true`:
- `additionalProperties: false` in the schema
- All properties listed in `required`

---

## Using messages.parse() (SDK Helper)

The SDK's `parse()` method validates the response against your schema automatically:

```python
response = client.messages.parse(
    model="claude-opus-5-5",
    max_tokens=4096,
    output_config={"format": {"type": "json_schema", "json_schema": {...}}},
    messages=[...]
)
```

---

## When to Use Which

| Need | Use |
|---|---|
| Claude's response must be JSON | `output_config.format` |
| Tool inputs must be valid | `strict: true` on the tool |
| Classification / extraction | `output_config.format` |
| Routing / intent detection | `strict: true` tool |
| Free-form text response | Neither — default behavior |

---

## Incompatibilities

- `output_config.format` is **incompatible with citations** (returns 400)
- On models where forced `tool_choice` is removed (Opus 5.5, Sonnet 5.5, Fable 5.1), use `output_config.format` instead of forcing a tool call just to get JSON back
