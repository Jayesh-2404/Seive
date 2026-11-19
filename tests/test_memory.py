from sieve.memory import Memory


def test_memory_roundtrip(tmp_path) -> None:
    memory = Memory(path=str(tmp_path))
    memory.log("first query", ["a.py"], note="decision one")
    memory.log("second query", ["b.py"], note="decision two")
    recent = memory.recent(2)
    assert len(recent) == 2
    assert recent[-1]["note"] == "decision two"
    assert "Persistent notes" in memory.notes()
