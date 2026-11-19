from sieve.memory import Memory


def test_memory_roundtrip(tmp_path) -> None:
    memory = Memory(path=str(tmp_path))
    memory.log("first query", ["a.py"], note="decision one")
    memory.log("second query", ["b.py"], note="decision two")
    recent = memory.recent(2)
    assert len(recent) == 2
    assert recent[-1]["note"] == "decision two"
    assert "Persistent notes" in memory.notes()


def test_compaction_keeps_recent_turns_and_summarizes_old(tmp_path) -> None:
    memory = Memory(path=str(tmp_path))
    for i in range(10):
        memory.log(f"query {i}", [f"file{i}.py"], note=f"note {i}")
    compact = memory.compact(keep=3)
    assert len(compact) == 4
    assert "earlier turns" in compact[0]["q"]
    assert compact[-1]["note"] == "note 9"
    assert compact[1]["note"] == "note 7"
