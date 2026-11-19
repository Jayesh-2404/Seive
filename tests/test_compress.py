import json

import pytest

from sieve.compress import compress_text, detect_kind
from sieve.store import STORE


def test_log_keeps_the_error_and_saves_tokens() -> None:
    lines = [f"2026-01-01 10:00:00 INFO step {i} ok" for i in range(2000)]
    lines.insert(1000, "2026-01-01 10:00:00 ERROR boom in checkout")
    text = "\n".join(lines)
    result = compress_text(text, budget=300)
    assert result["kind"] == "log"
    assert "ERROR boom in checkout" in result["text"]
    assert result["tokens_after"] <= 300
    assert result["tokens_after"] < result["tokens_before"]
    assert result["ref"]
    assert "ERROR boom in checkout" in STORE.get(result["ref"])


def test_json_summary_keeps_count_and_shape() -> None:
    data = json.dumps([{"id": i, "name": f"row {i}"} for i in range(200)])
    result = compress_text(data, budget=200)
    assert result["kind"] == "json"
    assert "count" in result["text"] or "200" in result["text"]
    assert result["tokens_after"] <= 200


def test_csv_summary_keeps_header_and_row_count() -> None:
    rows = ["id,name,value"] + [f"{i},row {i},{i * 2}" for i in range(200)]
    result = compress_text("\n".join(rows), budget=200)
    assert result["kind"] == "csv"
    assert "id | name | value" in result["text"]
    assert "rows omitted" in result["text"]
    assert result["tokens_after"] <= 200


def test_small_text_is_unchanged() -> None:
    result = compress_text("hello", budget=200)
    assert result["changed"] is False
    assert result["ref"] is None
    assert result["text"] == "hello"


def test_ansi_and_repeated_lines_are_removed() -> None:
    text = "\x1b[31mERROR boom\x1b[0m\n" + "same line\n" * 200
    result = compress_text(text, budget=100, kind="text")
    assert "\x1b" not in result["text"]
    assert "ERROR boom" in result["text"]
    assert "(x200)" in result["text"]


def test_original_line_slice() -> None:
    original = "line one\nline two\nline three"
    long_text = original + "\n" + "\n".join(f"noise {i}" for i in range(500))
    result = compress_text(long_text, budget=80)
    assert result["ref"]
    assert STORE.get(result["ref"], 1, 2) == "line one\nline two"


def test_invalid_ref_is_rejected() -> None:
    with pytest.raises(ValueError):
        STORE.get("../../secret")


@pytest.mark.parametrize("kind,text", [
    ("text", "\n".join(f"line {i}" for i in range(2000))),
    ("log", "\n".join(f"INFO line {i}" for i in range(2000))),
    ("test", "\n".join(f"PASS test {i}" for i in range(2000))),
    ("json", json.dumps([{"id": i} for i in range(2000)])),
    ("html", "<html><body>" + "<div>item</div>" * 2000 + "</body></html>"),
])
def test_every_kind_respects_the_budget(kind: str, text: str) -> None:
    result = compress_text(text, budget=150, kind=kind)
    assert result["tokens_after"] <= 150


def test_detection_prefers_json_over_other_kinds() -> None:
    assert detect_kind('{"a": 1}') == "json"
    assert detect_kind("FAIL test_one\nok test_two") == "test"
