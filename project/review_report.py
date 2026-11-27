"""Terminal output for a structured review."""

from collections import Counter

from review_schema import SEVERITIES

SEVERITY_COLORS = {"critical": "\033[91m", "warning": "\033[93m", "info": "\033[94m"}
RESET = "\033[0m"


def format_review(review: dict, color: bool = True) -> str:
    """Render the review as text, most severe findings first."""
    rule = "=" * 60
    quality = review.get("overall_quality", "unknown")
    lines = [rule, "CODE REVIEW RESULTS", rule, "", f"Overall Quality: {quality.upper()}", ""]

    findings = sorted(review.get("findings", []), key=lambda f: SEVERITIES.index(f["severity"]))
    if not findings:
        lines.append("No findings!")
    for finding in findings:
        label = f"[{finding['severity'].upper()}]"
        if color:
            label = f"{SEVERITY_COLORS[finding['severity']]}{label}{RESET}"
        lines += [
            f"  {label} {finding['category']} — {finding['file']}:{finding['line']}",
            f"    {finding['description']}",
            f"    Fix: {finding['suggestion']}",
            "",
        ]

    lines += [f"Summary: {review.get('summary', 'N/A')}", rule]

    counts = Counter(f["severity"] for f in findings)
    if counts:
        totals = ", ".join(f"{counts[s]} {s}" for s in SEVERITIES if counts[s])
        lines.append(f"Findings: {totals}")

    return "\n".join(lines)
