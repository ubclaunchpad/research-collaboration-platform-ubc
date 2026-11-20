"""Running the merge on the RES-25 sample twice gives identical results."""

from pathlib import Path

from app.merge import sample
from app.merge.store import ResearcherStore

SAMPLE = Path(__file__).parents[3] / "sample_data" / "researchers_sample.json"


def run_once(db_path):
    with ResearcherStore(db_path) as store:
        results = sample.run(store, SAMPLE)
        return results, store.export(), store.counts()


def test_sample_merges_all_ten_researchers(tmp_path):
    results, export, counts = run_once(tmp_path / "db.sqlite")

    assert [r.status for r in results] == ["created"] * 10
    assert counts == {"researchers": 10, "source_records": 20, "review_items": 0}
    names = {r["full_name"] for r in export["researchers"]}
    assert "Mathias Lécuyer" in names
    for researcher in export["researchers"]:
        assert researcher["provenance"]["full_name"] == "dept_listing"
        assert researcher["provenance"]["papers"] == "openalex"
        assert len(researcher["papers"]) == 3


def test_running_twice_on_same_db_is_identical(tmp_path):
    db = tmp_path / "db.sqlite"
    _, first, first_counts = run_once(db)
    results, second, second_counts = run_once(db)

    assert [r.status for r in results] == ["merged"] * 10
    assert second == first
    assert second_counts == first_counts


def test_fresh_databases_give_identical_results(tmp_path):
    _, a, _ = run_once(tmp_path / "a.sqlite")
    _, b, _ = run_once(tmp_path / "b.sqlite")
    assert a == b  # including researcher ids


def test_cli_runs_twice(tmp_path, capsys):
    db, out = tmp_path / "db.sqlite", tmp_path / "out.json"
    assert sample.main([str(SAMPLE), "--db", str(db), "--out", str(out)]) == 0
    first = out.read_text()
    assert sample.main([str(SAMPLE), "--db", str(db), "--out", str(out)]) == 0
    assert out.read_text() == first
    assert "'researchers': 10" in capsys.readouterr().out
