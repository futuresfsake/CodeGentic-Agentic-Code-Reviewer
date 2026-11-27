from review_report import format_review


def finding(severity, line):
    return {
        "severity": severity,
        "category": "bug",
        "file": "main.py",
        "line": line,
        "description": "d",
        "suggestion": "s",
    }


def test_orders_findings_by_severity():
    review = {
        "overall_quality": "poor",
        "findings": [finding("info", 1), finding("critical", 2)],
        "summary": "Two issues.",
    }
    text = format_review(review, color=False)
    assert text.index("[CRITICAL]") < text.index("[INFO]")
    assert text.endswith("Findings: 1 critical, 1 info")


def test_plain_output_has_no_escape_codes():
    review = {"overall_quality": "good", "findings": [finding("warning", 3)], "summary": "ok"}
    assert "\033[" not in format_review(review, color=False)


def test_handles_a_clean_review():
    review = {"overall_quality": "excellent", "findings": [], "summary": "Clean."}
    assert "No findings!" in format_review(review)
