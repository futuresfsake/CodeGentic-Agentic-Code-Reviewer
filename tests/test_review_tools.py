import json

import pytest

from review_tools import MAX_LINES, ReviewTarget, execute_tool


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "app"
    (root / "pkg").mkdir(parents=True)
    (root / "main.py").write_text("import os\npassword = 'x'\n", encoding="utf-8")
    (root / "pkg" / "util.py").write_text("def f():\n    pass\n", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("password = 'outside'\n", encoding="utf-8")
    return root


def run(name, args, target):
    return json.loads(execute_tool(name, args, target))


def test_lists_files_relative_to_the_target(project):
    result = run("list_files", {"path": ".", "pattern": "**/*.py"}, ReviewTarget(str(project)))
    assert result["files"] == ["main.py", "pkg/util.py"]


def test_reads_a_file_with_line_numbers(project):
    result = run("read_file", {"path": "main.py"}, ReviewTarget(str(project)))
    assert result["content"].startswith("1\timport os\n2\t")


def test_truncates_long_files(project):
    (project / "long.py").write_text("x\n" * (MAX_LINES + 5), encoding="utf-8")
    result = run("read_file", {"path": "long.py"}, ReviewTarget(str(project)))
    assert "5 more lines truncated" in result["content"]


@pytest.mark.parametrize("path", ["../secret.txt", "pkg/../../secret.txt"])
def test_refuses_to_read_outside_the_target(project, path):
    result = run("read_file", {"path": path}, ReviewTarget(str(project)))
    assert "outside the review target" in result["error"]


def test_refuses_an_absolute_path(project):
    outside = str(project.parent / "secret.txt")
    result = run("read_file", {"path": outside}, ReviewTarget(str(project)))
    assert "outside the review target" in result["error"]


def test_refuses_to_list_the_parent(project):
    result = run("list_files", {"path": ".."}, ReviewTarget(str(project)))
    assert "outside the review target" in result["error"]


def test_search_glob_cannot_escape(project):
    args = {"pattern": "password", "file_pattern": "../*"}
    result = run("search_pattern", args, ReviewTarget(str(project)))
    assert result["matches"] == []


def test_search_finds_matches(project):
    result = run("search_pattern", {"pattern": "password"}, ReviewTarget(str(project)))
    assert result["matches"] == [{"file": "main.py", "line": 2, "text": "password = 'x'"}]


def test_single_file_target_exposes_only_that_file(project):
    target = ReviewTarget(str(project / "main.py"))
    assert run("list_files", {"path": "."}, target)["files"] == ["main.py"]
    assert "content" in run("read_file", {"path": "main.py"}, target)
    assert "error" in run("read_file", {"path": "pkg/util.py"}, target)


@pytest.mark.parametrize(
    ("name", "args"),
    [("read_file", {}), ("search_pattern", {"pattern": "("}), ("delete_file", {})],
)
def test_bad_calls_return_an_error(project, name, args):
    assert "error" in run(name, args, ReviewTarget(str(project)))
