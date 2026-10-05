"""Token counting with tiktoken (cl100k_base). Single source of truth."""
try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    BACKEND = "tiktoken/cl100k_base"
except Exception:
    _enc = None
    BACKEND = "fallback/char4"

def count(text: str) -> int:
    if _enc is not None:
        return len(_enc.encode(text))
    return max(1, len(text) // 4)

def truncate(text: str, max_tokens: int) -> str:
    if count(text) <= max_tokens:
        return text
    if _enc is not None:
        toks = _enc.encode(text)[:max_tokens]
        return _enc.decode(toks)
    return text[:max_tokens * 4]
