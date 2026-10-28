# Module 2: Error Handling & Retries

## Official Documentation
- [Errors](https://platform.claude.com/docs/en/api/errors.md)
- [Rate Limits](https://platform.claude.com/docs/en/api/rate-limits.md)

---

## SDK Auto-Retry

The Anthropic SDK automatically retries these errors with exponential backoff:

| Error | Status Code | Auto-retried? |
|---|---|---|
| Request Timeout | 408 | Yes |
| Conflict | 409 | Yes |
| Rate Limited | 429 | Yes |
| Server Error | 500+ | Yes |
| Connection Error | N/A | Yes |
| Bad Request | 400 | **No** — fix your request |
| Auth Error | 401 | **No** — fix your API key |
| Permission Denied | 403 | **No** — check permissions |
| Not Found | 404 | **No** — wrong model/endpoint |

Default: **2 retries**. Configure with `max_retries`:
```python
client = anthropic.Anthropic(max_retries=5)  # or 0 to disable
```

---

## Exception Hierarchy

Catch specific exceptions, most-specific first:

```python
try:
    response = client.messages.create(...)
except anthropic.BadRequestError as e:        # 400 - fix the request
    print(f"Bad request: {e.message}")
except anthropic.AuthenticationError:          # 401 - invalid key
    print("Invalid API key")
except anthropic.PermissionDeniedError:        # 403 - lacks permissions
    print("Permission denied")
except anthropic.NotFoundError:                # 404 - wrong model/endpoint
    print("Not found")
except anthropic.RateLimitError as e:          # 429 - rate limited
    retry_after = int(e.response.headers.get("retry-after", "60"))
    print(f"Rate limited. Retry after {retry_after}s")
except anthropic.APIStatusError as e:          # catch-all for other HTTP errors
    if e.status_code >= 500:
        print(f"Server error ({e.status_code})")
    else:
        print(f"API error: {e.message}")
except anthropic.APIConnectionError:           # network/connection issues
    print("Connection error")
```

**Never** use a single broad `except APIStatusError` — you lose the distinction between retryable (429, 500+) and non-retryable (400, 404) errors.

---

## Common 400 Errors (Fix Your Code)

| Error | Cause |
|---|---|
| `budget_tokens` on modern models | Use `{"type": "adaptive"}` instead |
| `thinking: {type: "disabled"}` on Opus 5.5 | Can't disable thinking; use low effort |
| `tool_choice: "any"/"tool"` on Opus 5.5/Sonnet 5.5/Fable 5.1 | Use `"auto"` + prompt instruction |
| `temperature`/`top_p`/`top_k` on 4.6+ | Sampling params removed |
| Assistant prefill on 4.6+ | Use structured outputs instead |
| MCP without `mcp_toolset` in tools | Both `mcp_servers` AND `mcp_toolset` required |

---

## Retry Pattern (Custom)

Only needed when SDK's built-in retry isn't enough:

```python
import time, random

def call_with_retry(client, max_retries=5, base_delay=1.0, **kwargs):
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError:
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), 60)
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                delay = min(base_delay * (2 ** attempt), 60)
                time.sleep(delay)
            else:
                raise  # 4xx (except 429) should not be retried
    raise Exception("Max retries exceeded")
```

---

## Timeouts

- Default: **10 minutes**
- Python timeout unit: **seconds** (not milliseconds!)
- TypeScript timeout unit: **milliseconds**
- Large `max_tokens` without streaming raises `ValueError` (SDK prevents HTTP timeout)

```python
client = anthropic.Anthropic(timeout=20.0)  # 20 seconds

# Per-request override
client.with_options(timeout=5.0).messages.create(...)
```

---

## Key Rules

1. **Catch specific, not broad** — chain from most-specific to least-specific
2. **Don't retry 400s** — fix the request instead
3. **SDK handles most retries** — only add custom retry for special cases
4. **Log `_request_id`** — `response._request_id` helps when reporting issues to Anthropic
5. **Stream for large outputs** — prevents HTTP timeouts better than increasing timeout
