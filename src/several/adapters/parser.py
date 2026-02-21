from __future__ import annotations

import re
from dataclasses import dataclass, field

TOOL_PATTERN = re.compile(
    r"\b(read_file|write_file|edit_file|apply_patch|bash|run_command|create_file|delete_file)\b",
    re.IGNORECASE,
)
TOKEN_PATTERN = re.compile(r"(?i)\btokens?\b[^0-9]{0,12}([0-9][0-9,]*)")
PERCENT_PATTERN = re.compile(r"(?<!\d)(100|[1-9]?\d)%")


@dataclass
class ParsedOutput:
    tokens_used: int | None = None
    progress_percent: int | None = None
    tool_calls: list[str] = field(default_factory=list)


def parse_output(profile: str | None, output: str) -> ParsedOutput:
    _ = profile  # profile-specific behavior can be extended incrementally.

    tokens_used: int | None = None
    for match in TOKEN_PATTERN.findall(output):
        value = int(match.replace(",", ""))
        tokens_used = max(tokens_used or 0, value)

    progress_values = [int(item) for item in PERCENT_PATTERN.findall(output)]
    progress_percent = max(progress_values) if progress_values else None

    seen: set[str] = set()
    tool_calls: list[str] = []
    for match in TOOL_PATTERN.findall(output):
        normalized = match.lower()
        if normalized not in seen:
            seen.add(normalized)
            tool_calls.append(normalized)

    return ParsedOutput(
        tokens_used=tokens_used,
        progress_percent=progress_percent,
        tool_calls=tool_calls,
    )
