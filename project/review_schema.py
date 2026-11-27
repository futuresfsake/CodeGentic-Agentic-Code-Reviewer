"""JSON schema for the final review, passed as output_config.format."""

SEVERITIES = ["critical", "warning", "info"]
CATEGORIES = ["bug", "security", "performance", "style", "maintainability"]
QUALITY_LEVELS = ["excellent", "good", "needs_improvement", "poor"]

FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "severity": {"type": "string", "enum": SEVERITIES},
        "category": {"type": "string", "enum": CATEGORIES},
        "file": {"type": "string"},
        "line": {"type": "integer"},
        "description": {"type": "string"},
        "suggestion": {"type": "string"},
    },
    "required": ["severity", "category", "file", "line", "description", "suggestion"],
    "additionalProperties": False,
}

REVIEW_FORMAT = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "overall_quality": {"type": "string", "enum": QUALITY_LEVELS},
            "findings": {"type": "array", "items": FINDING_SCHEMA},
            "summary": {"type": "string"},
        },
        "required": ["overall_quality", "findings", "summary"],
        "additionalProperties": False,
    },
}
