from PyQt6.QtCore import Qt

from src.database import DBManager
from src.notebook_database import NotebookDBManager
from src.ui.context_manager_panel import ContextManagerPanel


def test_context_panel_restores_real_sqlite_context_between_panels(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "context.sqlite"))
    record_id = db.save("context.wav", "Transcript", 2.0, "Context recording")
    notebook_db = NotebookDBManager(str(tmp_path / "notebooks.sqlite"))
    notebook_id = notebook_db.create_notebook("Project")
    notebook_db.add_text_entry(notebook_id, "Decision", title="Notebook decision")
    source = ContextManagerPanel(db, notebook_db)
    mirror = ContextManagerPanel(db, notebook_db, show_header=False, interactive=False)
    qtbot.addWidget(source)
    qtbot.addWidget(mirror)
    changes = []
    source.context_changed.connect(lambda: changes.append(True))

    source.nb_list.item(0).setCheckState(Qt.CheckState.Checked)
    source.set_forced_records([{"id": record_id, "title": "Context recording", "created_at": "2026-09-08"}])
    source.sync_with_global(None, None, "work, ops")
    mirror.restore_from_panel(source)

    assert mirror.serialize_state() == source.serialize_state()
    assert mirror.entries_list.count() == 2
    assert "Context recording" in mirror.entries_list.item(0).text()
    assert "Notebook decision" in mirror.entries_list.item(1).text()
    assert changes
