"""
==============================================================================
MODULE 2: STRUCTURED OUTPUTS
==============================================================================

OFFICIAL DOCUMENTATION:
  - Structured Outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
  - Tool Use Overview:  https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md

Two ways to get structured JSON from Claude:
  1. output_config.format  — constrain the entire response
  2. strict: true on tools — guarantee tool input validity

==============================================================================
"""

import anthropic
import json

client = anthropic.Anthropic()


# =============================================================================
# METHOD 1: output_config.format — Constrain Entire Response
# =============================================================================
# Force Claude's response to match a JSON schema.
# Use for: classification, extraction, structured analysis.

def structured_sentiment():
    """Force Claude to return sentiment analysis as structured JSON."""
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        output_config={
            "format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "sentiment_analysis",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "sentiment": {
                                "type": "string",
                                "enum": ["positive", "negative", "neutral", "mixed"]
                            },
                            "confidence": {
                                "type": "number",
                                "description": "0.0 to 1.0"
                            },
                            "key_phrases": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "summary": {
                                "type": "string"
                            }
                        },
                        "required": ["sentiment", "confidence", "key_phrases", "summary"],
                        "additionalProperties": False
                    }
                }
            }
        },
        messages=[
            {"role": "user", "content": "Analyze the sentiment: 'The new update is fantastic but the pricing is outrageous.'"}
        ]
    )

    # Response text is guaranteed valid JSON matching the schema
    result = json.loads(response.content[0].text)
    print(json.dumps(result, indent=2))
    return result


# =============================================================================
# EXTRACTION EXAMPLE
# =============================================================================

def extract_entities():
    """Extract structured data from unstructured text."""
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        output_config={
            "format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "contact_info",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                            "phone": {"type": "string"},
                            "company": {"type": "string"},
                            "role": {"type": "string"}
                        },
                        "required": ["name", "email", "phone", "company", "role"],
                        "additionalProperties": False
                    }
                }
            }
        },
        messages=[{
            "role": "user",
            "content": (
                "Extract contact info from this email: "
                "'Hi, I'm Sarah Chen from Acme Corp. I'm the VP of Engineering. "
                "You can reach me at sarah@acme.com or 555-0123.'"
            )
        }]
    )

    result = json.loads(response.content[0].text)
    print(json.dumps(result, indent=2))
    return result


# =============================================================================
# METHOD 2: strict: true on Tools — Guarantee Tool Inputs
# =============================================================================
# Use when you need Claude to call a tool with guaranteed valid arguments.

def strict_tool_classification():
    """Use strict tool for intent classification."""
    tools = [{
        "name": "classify_intent",
        "description": "Classify the user's support request into a category and priority.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["billing", "technical", "account", "general"]
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"]
                },
                "summary": {
                    "type": "string",
                    "description": "One-line summary of the issue"
                }
            },
            "required": ["category", "priority", "summary"],
            "additionalProperties": False  # REQUIRED for strict mode
        }
    }]

    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        tools=tools,
        messages=[{
            "role": "user",
            "content": "I can't log in and I have a demo in 30 minutes!"
        }]
    )

    for block in response.content:
        if block.type == "tool_use":
            print(f"Category: {block.input['category']}")
            print(f"Priority: {block.input['priority']}")
            print(f"Summary:  {block.input['summary']}")
            # With strict: true, these fields are GUARANTEED to be valid
    return response


# =============================================================================
# COMPLEX NESTED SCHEMA
# =============================================================================

def structured_code_review():
    """Structured output for code review findings — used in the real project."""
    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=8000,
        output_config={
            "format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "code_review",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "overall_quality": {
                                "type": "string",
                                "enum": ["excellent", "good", "needs_improvement", "poor"]
                            },
                            "findings": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
                                        "category": {"type": "string", "enum": ["bug", "security", "performance", "style", "maintainability"]},
                                        "line": {"type": "integer"},
                                        "description": {"type": "string"},
                                        "suggestion": {"type": "string"}
                                    },
                                    "required": ["severity", "category", "line", "description", "suggestion"],
                                    "additionalProperties": False
                                }
                            },
                            "summary": {"type": "string"}
                        },
                        "required": ["overall_quality", "findings", "summary"],
                        "additionalProperties": False
                    }
                }
            }
        },
        messages=[{
            "role": "user",
            "content": "Review this code:\n```python\ndef login(user, pw):\n    if pw == 'admin123':\n        return True\n    q = f'SELECT * FROM users WHERE name={user}'\n    return db.execute(q)\n```"
        }]
    )

    result = json.loads(response.content[0].text)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("Structured Outputs Demo")
    print("=" * 60)
    print("\nRun individual functions:")
    print("  structured_sentiment()       - sentiment as JSON")
    print("  extract_entities()           - extract contact info")
    print("  strict_tool_classification() - strict tool for classification")
    print("  structured_code_review()     - nested review findings")
