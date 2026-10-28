"""
==============================================================================
MODULE 2: ERROR HANDLING & RETRIES
==============================================================================

OFFICIAL DOCUMENTATION:
  - Errors:      https://platform.claude.com/docs/en/api/errors.md
  - Rate Limits: https://platform.claude.com/docs/en/api/rate-limits.md

The SDK auto-retries 408, 409, 429, 500+ with exponential backoff.
Default: 2 retries. Catch specific exceptions, most-specific first.

==============================================================================
"""

import anthropic
import json
import time
import random

client = anthropic.Anthropic()


# =============================================================================
# PROPER ERROR HANDLING — Specific Exception Chain
# =============================================================================
# Catch specific exceptions in order: most-specific → least-specific.
# Never use a single broad except — you lose retryable vs non-retryable.

def proper_error_handling():
    """The correct way to handle Claude API errors."""
    try:
        response = client.messages.create(
            model="claude-opus-5-5",
            max_tokens=4096,
            messages=[{"role": "user", "content": "Hello!"}]
        )
        return response

    except anthropic.BadRequestError as e:
        # 400 — your request is wrong. Fix it, don't retry.
        # Common causes: invalid model, budget_tokens on modern model,
        # disabled thinking on Opus 5.5, temperature on 4.6+
        print(f"Bad request: {e.message}")
        return None

    except anthropic.AuthenticationError:
        # 401 — invalid API key
        print("Invalid API key. Check ANTHROPIC_API_KEY.")
        return None

    except anthropic.PermissionDeniedError:
        # 403 — key doesn't have required permissions
        print("Permission denied. Check API key permissions.")
        return None

    except anthropic.NotFoundError:
        # 404 — wrong model name or endpoint
        print("Not found. Check model name and endpoint.")
        return None

    except anthropic.RateLimitError as e:
        # 429 — rate limited (SDK already retried 2 times)
        retry_after = int(e.response.headers.get("retry-after", "60"))
        print(f"Rate limited even after retries. Retry after {retry_after}s.")
        return None

    except anthropic.APIStatusError as e:
        # Catch-all for other HTTP errors
        if e.status_code >= 500:
            print(f"Server error ({e.status_code}). Anthropic is having issues.")
        else:
            print(f"API error ({e.status_code}): {e.message}")
        return None

    except anthropic.APIConnectionError:
        # Network issues — no HTTP response at all
        print("Connection error. Check internet.")
        return None


# =============================================================================
# CONFIGURING SDK RETRIES
# =============================================================================

def configure_retries():
    """Show different retry configurations."""

    # More retries for unreliable connections
    resilient_client = anthropic.Anthropic(max_retries=5)

    # No retries — handle everything yourself
    no_retry_client = anthropic.Anthropic(max_retries=0)

    # Per-request override
    response = client.with_options(max_retries=5).messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": "Hello"}]
    )
    return response


# =============================================================================
# CUSTOM RETRY WITH EXPONENTIAL BACKOFF
# =============================================================================
# Only needed when SDK's built-in retry isn't enough.
# Example: you want more retries, different delay strategy, or logging.

def call_with_retry(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs
):
    """Call the API with custom exponential backoff retry."""
    last_exception = None

    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)

        except anthropic.RateLimitError as e:
            last_exception = e
            retry_after = int(e.response.headers.get("retry-after", "0"))
            delay = max(retry_after, base_delay * (2 ** attempt)) + random.uniform(0, 1)
            delay = min(delay, max_delay)
            print(f"Rate limited. Retry {attempt + 1}/{max_retries} after {delay:.1f}s")
            time.sleep(delay)

        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                last_exception = e
                delay = min(base_delay * (2 ** attempt), max_delay)
                print(f"Server error {e.status_code}. Retry {attempt + 1}/{max_retries} after {delay:.1f}s")
                time.sleep(delay)
            else:
                raise  # 4xx (except 429) should NOT be retried

        except anthropic.APIConnectionError as e:
            last_exception = e
            delay = min(base_delay * (2 ** attempt), max_delay)
            print(f"Connection error. Retry {attempt + 1}/{max_retries} after {delay:.1f}s")
            time.sleep(delay)

    raise last_exception


# =============================================================================
# TIMEOUT CONFIGURATION
# =============================================================================

def timeout_examples():
    """Different timeout configurations."""

    # Client-level timeout (seconds in Python!)
    client_with_timeout = anthropic.Anthropic(timeout=20.0)

    # Granular timeout control
    client_granular = anthropic.Anthropic(
        timeout=anthropic.Timeout(60.0, read=5.0, write=10.0, connect=2.0)
    )

    # Per-request timeout override
    response = client.with_options(timeout=5.0).messages.create(
        model="claude-opus-5-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Quick question"}]
    )
    return response


# =============================================================================
# LOGGING THE REQUEST ID
# =============================================================================
# Every response has _request_id. Log it for debugging and when
# reporting issues to Anthropic.

def log_request_id():
    """Log the request ID for debugging."""
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello"}]
    )
    print(f"Request ID: {response._request_id}")
    print(f"Model: {response.model}")
    print(f"Stop reason: {response.stop_reason}")
    return response


# =============================================================================
# ERROR HANDLING IN AN AGENT LOOP
# =============================================================================
# In a production agent, wrap the API call with error handling
# and track iterations to prevent infinite loops.

tools = [
    {"name": "search", "description": "Search for info",
     "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}}
]


def robust_agent_loop(user_message: str, max_iterations: int = 10):
    """Agent loop with comprehensive error handling."""
    messages = [{"role": "user", "content": user_message}]
    iterations = 0
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 3

    while iterations < max_iterations:
        iterations += 1

        try:
            response = client.messages.create(
                model="claude-opus-5-5",
                max_tokens=4096,
                tools=tools,
                messages=messages,
            )
            consecutive_errors = 0  # reset on success

        except anthropic.RateLimitError:
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                print("Too many consecutive rate limit errors. Stopping.")
                return None
            time.sleep(30)
            continue

        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print("Too many consecutive server errors. Stopping.")
                    return None
                time.sleep(5)
                continue
            else:
                print(f"Non-retryable error: {e.message}")
                return None

        except anthropic.APIConnectionError:
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                print("Too many consecutive connection errors. Stopping.")
                return None
            time.sleep(5)
            continue

        # Process response
        if response.stop_reason == "end_turn":
            return next((b.text for b in response.content if b.type == "text"), "")

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"result": "mock data"})
                    })
            messages.append({"role": "user", "content": tool_results})

        if response.stop_reason == "max_tokens":
            print("Hit max_tokens. Increase max_tokens or use streaming.")
            return None

        if response.stop_reason == "refusal":
            print("Claude refused the request.")
            return None

    print(f"Hit max iterations ({max_iterations}).")
    return None


if __name__ == "__main__":
    print("=" * 60)
    print("Error Handling & Retries Demo")
    print("=" * 60)
    print("\nRun individual functions:")
    print("  proper_error_handling()   - correct exception chain")
    print("  log_request_id()          - log request ID for debugging")
    print("  robust_agent_loop(msg)    - agent loop with error recovery")
