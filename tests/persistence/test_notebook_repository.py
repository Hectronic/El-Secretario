from src.notebook_database import NotebookDBManager
from src.persistence import NotebookRepository


def test_notebook_repository_persists_entries_and_cascades_deletion(tmp_path):
    repository = NotebookRepository(str(tmp_path / "notebooks.sqlite"))
    notebook_id = repository.create_notebook("Research", "Sprint references")
    entry_id = repository.add_text_entry(notebook_id, "Read the requirements", "Plan")

    assert repository.get_notebook(notebook_id)["name"] == "Research"
    entries = repository.get_entries(notebook_id)
    assert len(entries) == 1
    assert entries[0]["id"] == entry_id
    assert entries[0]["content"] == "Read the requirements"
    assert entries[0]["title"] == "Plan"

    repository.delete_notebook(notebook_id)
    assert repository.get_entries(notebook_id) == []


def test_notebook_facade_delegates_to_repository(tmp_path, monkeypatch):
    db = NotebookDBManager(str(tmp_path / "notebooks.sqlite"))
    calls = []
    monkeypatch.setattr(db.notebooks, "get_notebooks", lambda: calls.append(True) or [])

    assert db.get_notebooks() == []
    assert calls == [True]
