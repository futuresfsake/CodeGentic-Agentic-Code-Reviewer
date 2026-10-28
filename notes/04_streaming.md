# Module 2: Streaming Responses

## Official Documentation
- [Streaming](https://platform.claude.com/docs/en/build-with-claude/streaming.md)
- [Models Overview](https://platform.claude.com/docs/en/about-claude/models/overview.md)
- [Errors](https://platform.claude.com/docs/en/api/errors.md)

---

## What Is Streaming?

Streaming sends tokens to your app **as Claude generates them** instead of waiting for the full response. It uses **Server-Sent Events (SSE)** — a standard protocol where the server pushes data to the client over a single HTTP connection.

Without streaming: you wait for the entire response (could be minutes with thinking), then get it all at once.

With streaming: tokens appear in real time, users see text forming live.

---

## When Streaming Is Required

Streaming isn't always optional:

| Situation | Streaming required? |
|---|---|
| Normal short response | No, but still recommended |
| Extended thinking enabled | Strongly recommended (long wait otherwise) |
| `max_tokens` > ~16K | Recommended to avoid HTTP timeouts |
| `max_tokens` at 128K | **Yes** — SDK raises `ValueError` without it |
| User-facing chat UI | Yes — users need to see live output |
| Background/batch processing | No — use Batch API instead |

**Rule of thumb**: default to streaming for anything non-trivial. Use `get_final_message()` if you just need the complete response — you get timeout protection for free.

---

## Two Ways to Stream

### 1. `client.messages.stream()` — Recommended

The SDK helper. Manages the connection, accumulates state, gives you `text_stream` and `get_final_message()`.

```python
with client.messages.stream(...) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
    final = stream.get_final_message()
```

### 2. `stream=True` on `messages.create()` — Low-level

Raw event iterator. No accumulation, no final message helper. Use only when you need minimal memory or custom event handling.

```python
for event in client.messages.create(..., stream=True):
    print(event.type)
```

**Always prefer option 1** unless you have a specific reason not to.

---

## Stream Event Types

Events arrive in this order:

```
message_start          → once, contains message metadata
  content_block_start  → new block beginning (thinking, text, or tool_use)
    content_block_delta  → incremental content (repeated, one per token/chunk)
    content_block_delta  → ...
  content_block_stop   → block complete
  content_block_start  → next block...
    content_block_delta  → ...
  content_block_stop   → ...
message_delta          → message-level update (stop_reason, usage)
message_stop           → done
```

### Delta Types Inside `content_block_delta`

| `event.delta.type` | What it is | When it appears |
|---|---|---|
| `thinking_delta` | Thinking token | During a thinking block |
| `text_delta` | Response text token | During a text block |
| `input_json_delta` | Tool input fragment | During a tool_use block |

---

## When Streaming Breaks

### What the SDK handles automatically
- **Retries** on connection errors, 408, 409, 429, and 5xx (default: 2 retries with exponential backoff)
- **Timeout management** — configurable via `timeout` parameter

### What you handle
- **Partial content on disconnect** — if the stream drops, you have whatever tokens arrived so far. There's no resume-from-where-it-left-off. You retry the full request.
- **Rate limiting** — SDK retries, but you may want custom handling for long waits.

### Fixes and Patterns

1. **Wrap streams in try/except** — catch `APIConnectionError` and `RateLimitError`
2. **Use `get_final_message()`** — always call it after streaming to get the complete response with usage stats
3. **Always `flush=True`** — when printing tokens, `flush=True` makes them appear immediately instead of buffering
4. **Set appropriate timeouts** — default is 10 minutes, increase for long-thinking requests
5. **Increase `max_retries`** — for unreliable connections, set higher than the default 2

---

## Streaming + Extended Thinking

When thinking is enabled, the stream produces **thinking blocks first, then text blocks**:

```
content_block_start  → type: "thinking"
  thinking_delta     → thinking tokens (empty if display: "omitted")
content_block_stop
content_block_start  → type: "text"
  text_delta         → response tokens
content_block_stop
```

If `display` is `"omitted"` (the default), thinking deltas are empty — the stream looks like a long pause. Set `display: "summarized"` to stream visible reasoning.

---

## Streaming + Tool Use

When Claude calls a tool during streaming:

```
content_block_start  → type: "text" (optional, Claude might say something first)
  text_delta         → "Let me check that..."
content_block_stop
content_block_start  → type: "tool_use" (name, id)
  input_json_delta   → tool input fragments
content_block_stop
message_delta        → stop_reason: "tool_use"
```

With `eager_input_streaming: true` on the tool, input fragments arrive immediately as Claude generates them instead of buffering until complete.

---

## Key Gotchas

1. **`max_tokens` > ~64K without streaming** — SDK raises `ValueError` to prevent HTTP timeout
2. **`flush=True`** — without it, printed tokens buffer and appear in chunks, not real-time
3. **`get_final_message()` must be called inside the `with` block** — the stream is closed after exiting
4. **Thinking with default display looks like a hang** — long pause with no output. Set `"summarized"` for UIs.
5. **`output_tokens` in usage includes thinking tokens** — same as non-streaming
