"""Simple fact extraction from conversation turns."""

from __future__ import annotations

import re


def extract_facts_simple(user_message: str, assistant_response: str) -> list[str]:
    """
    Extract key facts using simple heuristics (no LLM).

    Returns list of fact strings (max 5 per turn).
    """
    facts: list[str] = []
    combined = f"{user_message}\n{assistant_response}"

    # Pattern 1: Names (e.g., "John Smith", "Alice Johnson")
    name_pattern = r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b"
    seen_names: set[str] = set()
    for match in re.finditer(name_pattern, combined):
        name = match.group(1)
        if name not in seen_names:
            seen_names.add(name)
            facts.append(f"Person mentioned: {name}")

    # Pattern 2: Dates (ISO format or slash format)
    date_pattern = r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b"
    seen_dates: set[str] = set()
    for match in re.finditer(date_pattern, combined):
        date = match.group(1)
        if date not in seen_dates:
            seen_dates.add(date)
            facts.append(f"Date mentioned: {date}")

    # Pattern 3: IDs/References (e.g., "LR-123", "REQ-456", "ticket #789")
    id_pattern = r"\b([A-Z]{2,}-\d+|#\d+)\b"
    for match in re.finditer(id_pattern, combined):
        facts.append(f"Reference: {match.group(1)}")

    # Pattern 4: Actions completed (from assistant response)
    completion_keywords = ["completed", "done", "submitted", "approved", "created", "sent"]
    for keyword in completion_keywords:
        if keyword in assistant_response.lower():
            # Extract first sentence containing the keyword
            sentences = assistant_response.split(".")
            for sentence in sentences:
                if keyword in sentence.lower():
                    clean = sentence.strip()[:100]
                    if clean:
                        facts.append(f"Action: {clean}")
                    break
            break  # Only capture one action per turn

    return facts[:5]  # Limit to 5 facts per turn
