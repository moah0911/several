from __future__ import annotations

from several.adapters.parser import parse_output


def test_parse_output_extracts_tokens_progress_and_tools() -> None:
    text = """
    Progress: 34%
    Tokens used: 1,234
    calling tool read_file
    done 89%
    write_file completed
    """
    parsed = parse_output("generic", text)
    assert parsed.tokens_used == 1234
    assert parsed.progress_percent == 89
    assert "read_file" in parsed.tool_calls
    assert "write_file" in parsed.tool_calls
