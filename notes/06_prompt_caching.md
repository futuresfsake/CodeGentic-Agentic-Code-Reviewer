# Module 2: Prompt Caching

## Official Documentation
- [Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md)
- [Pricing](https://platform.claude.com/docs/en/about-claude/pricing.md)

---

## Core Rule

**Prompt caching is a PREFIX MATCH. Any byte change anywhere in the prefix invalidates everything after it.**

That one rule explains everything about caching. The cache key is the exact bytes of the prompt up to each `cache_control` breakpoint. One different byte at position N = everything after N is uncached.

---

## Render Order

The API renders the prompt in this order:

```
tools → system → messages
```

A breakpoint on the last system block caches both tools AND system together.

---

## How It Works

1. **First request**: prompt is processed and cached. You pay a small write premium (~1.25x cost).
2. **Subsequent requests**: if the prefix bytes match, cached portion is read at ~0.1x cost (90% savings).
3. **Cache TTL**: default 5 minutes, configurable up to 1 hour.

### Pricing

| Token type | Cost multiplier |
|---|---|
| `cache_creation_input_tokens` | ~1.25x normal input cost |
| `cache_read_input_tokens` | ~0.1x normal input cost (90% savings) |
| `input_tokens` | 1x (uncached, full cost) |

---

## Two Ways to Cache

### 1. Automatic (Recommended)

Top-level `cache_control` on `messages.create()` — caches the last cacheable block automatically:

```python
response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=16000,
    cache_control={"type": "ephemeral"},  # auto-caches
    system="Large system prompt...",
    messages=[{"role": "user", "content": "Question"}]
)
```

### 2. Manual (Fine-Grained)

Add `cache_control` to specific content blocks:

```python
response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=16000,
    system=[{
        "type": "text",
        "text": "Large system prompt...",
        "cache_control": {"type": "ephemeral"}  # breakpoint here
    }],
    messages=[{"role": "user", "content": "Question"}]
)
```

With explicit TTL:
```python
"cache_control": {"type": "ephemeral", "ttl": "1h"}  # 1 hour
```

---

## Verifying Cache Hits

```python
print(response.usage.cache_creation_input_tokens)  # written to cache
print(response.usage.cache_read_input_tokens)       # read from cache (the savings)
print(response.usage.input_tokens)                  # uncached (full cost)
```

If `cache_read_input_tokens` is zero across repeated identical-prefix requests, a **silent invalidator** is at work.

---

## Placement Patterns

### Large shared system prompt
```json
"system": [
  {"type": "text", "text": "<large prompt>", "cache_control": {"type": "ephemeral"}}
]
```

### Multi-turn conversations
Put breakpoint on the last content block of the most recent turn. Each new turn reuses the cached prefix.

### Shared prefix, varying suffix
Cache the shared part, leave the varying question uncached:
```json
"messages": [{"role": "user", "content": [
  {"type": "text", "text": "<shared context>", "cache_control": {"type": "ephemeral"}},
  {"type": "text", "text": "<varying question>"}
]}]
```

---

## Silent Invalidators (CERTIFICATION IMPORTANT)

These secretly break caching — grep for them in your code:

| Pattern | Why it breaks |
|---|---|
| `datetime.now()` in system prompt | Prefix changes every request |
| `uuid4()` / request IDs early in content | Every request is unique |
| `json.dumps(d)` without `sort_keys=True` | Non-deterministic serialization |
| User/session ID interpolated in system prompt | Per-user prefix, no sharing |
| Conditional system sections (`if flag: ...`) | Each flag combo = different prefix |
| `tools=build_tools(user)` varying per user | Tools render at position 0 |

**Fix**: move dynamic content after the last breakpoint, make it deterministic, or delete it.

---

## Rules & Limits

- Max **4** `cache_control` breakpoints per request
- Minimum cacheable prefix: 512–4096 tokens depending on model
- Caches are **model-scoped** — switching models = cache miss
- Caches are **workspace-scoped** — different workspaces = separate entries
- Don't change tools mid-conversation — tools render at position 0
- Keep system prompt frozen — no interpolated timestamps or IDs

---

## Key Architectural Rules

1. **Keep stable content first** (frozen system prompt, deterministic tool list)
2. **Put volatile content last** (timestamps, per-request IDs, varying questions)
3. **Don't interpolate dynamic values into system prompts** — use mid-conversation system messages instead
4. **Serialize tools deterministically** — sort by name
5. **Fork operations must reuse the parent's exact prefix**
