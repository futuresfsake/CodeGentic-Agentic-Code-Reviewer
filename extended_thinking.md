---
name: extended-thinking
description: Notes on how extended thinking is configured in the Claude API using JSON objects as parameters
metadata:
  type: user
---

## Extended Thinking Configuration

Extended thinking is configured through **JSON objects** (a set of named fields with values) passed as request parameters to the Messages API.

### Key parameters

- **`thinking`** — a JSON object like `{"type": "adaptive"}` that controls whether and how thinking runs. **Adaptive** means Claude dynamically decides on its own when to think and how deeply to think, based on the complexity of the request — rather than you setting a fixed token budget.
- **`output_config`** — a JSON object like `{"effort": "high"}` that controls thinking depth.

### Example

```python
response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=16000,
    thinking={"type": "adaptive", "display": "summarized"},
    output_config={"effort": "high"},
    messages=[{"role": "user", "content": "Solve this step by step..."}]
)
```

Here, `thinking` and `output_config` are each a JSON object — a set of named fields (`type`, `display`, `effort`) with their corresponding values (`"adaptive"`, `"summarized"`, `"high"`).

### Manual Extended Thinking (from the docs)

For older models like `claude-sonnet-4-6`, you use manual mode with `budget_tokens` instead of adaptive:

```python
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 10000},
    messages=[
        {
            "role": "user",
            "content": "Are there an infinite number of prime numbers such that n mod 4 == 3?",
        }
    ],
)

# The response contains summarized thinking blocks and text blocks
for block in response.content:
    match block.type:
        case "thinking":
            print(f"\nThinking summary: {block.thinking}")
        case "text":
            print(f"\nResponse: {block.text}")
```

- To turn on manual extended thinking, add a `thinking` object with `type` set to `"enabled"` and a `budget_tokens` value.
- The `budget_tokens` parameter sets a target for how many tokens Claude can use for its internal reasoning process.
- Larger budgets can improve response quality by allowing more thorough analysis for complex problems.
