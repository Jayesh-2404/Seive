from sieve.index import index_repo
from sieve.summarize import extractive_summary, summarize_file, validate_summary

ROOT = "sample_repo_large"

def test_extractive_fallback_is_unchanged() -> None:
    index = index_repo(ROOT)
    entry = next(item for item in index["files"] if item["file"] == "auth.py")
    summary = extractive_summary(entry, index)
    assert summary.startswith("auth.py: defines")
    assert "check_auth" in summary


def test_backticked_hallucination_is_rejected() -> None:
    source = "def check_auth(token):\n    return token\n"
    assert validate_summary("`check_auth` checks the token.", source, ["check_auth"])
    assert not validate_summary("`missing_symbol` does the work.", source, ["check_auth"])


def test_provider_summary_is_accepted_or_rejected() -> None:
    index = index_repo(ROOT)
    entry = next(item for item in index["files"] if item["file"] == "auth.py")

    def good(prompt: str) -> str:
        return "`check_auth` validates a token for `Session`."

    def bad(prompt: str) -> str:
        return "`not_a_real_symbol` does the work."

    accepted = summarize_file(entry, index, provider=good, use_cache=False)
    rejected = summarize_file(entry, index, provider=bad, use_cache=False)
    assert "check_auth" in accepted
    assert accepted != rejected
    assert rejected.startswith("auth.py: defines")


def test_validation_keeps_the_summary_bounded() -> None:
    index = index_repo(ROOT)
    entry = next(item for item in index["files"] if item["file"] == "auth.py")

    def long(prompt: str) -> str:
        return "`check_auth` " + "word " * 500

    summary = summarize_file(entry, index, provider=long, max_tokens=40,
                             use_cache=False)
    from sieve import tokenizer
    assert tokenizer.count(summary) <= 40
