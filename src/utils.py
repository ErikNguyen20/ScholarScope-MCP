import re


def sanitize_search_text(s: str) -> str:
    """Remove commas and collapse whitespace for API search terms for OpenAlex to work"""
    if not s:
        return s
    s = s.replace(",", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s
