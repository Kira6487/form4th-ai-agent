import re


def normalize_content(content: str) -> str:
    """Normalize whitespace without flattening Markdown structure."""
    content = content.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = [re.sub(r"[ \t]+$", "", line) for line in content.split("\n")]
    normalized = "\n".join(lines)
    normalized = re.sub(r"[ \t]{2,}", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()
