from src.ui.notebooks.actions import (
    add_text_entry,
    apply_transcription_error,
    apply_transcription_result,
    delete_entry_and_audio,
    rename_entry,
)


class _NotebookPort:
    def __init__(self):
        self.added = []
        self.content = []
        self.renamed = []
        self.deleted = []

    def add_text_entry(self, notebook_id, content):
        self.added.append((notebook_id, content))
        return 3

    def update_entry_content(self, entry_id, content):
        self.content.append((entry_id, content))

    def rename_entry(self, entry_id, title):
        self.renamed.append((entry_id, title))

    def delete_entry(self, entry_id):
        self.deleted.append(entry_id)
        return None


def test_text_and_transcription_actions_normalize_persisted_content():
    db = _NotebookPort()

    assert add_text_entry(db, 7, "  Project notes  ") == 3
    apply_transcription_result(db, 3, {"text": "Captured audio"})
    apply_transcription_error(db, 4, "Worker stopped")
    rename_entry(db, 3, "  Voice memo  ")

    assert db.added == [(7, "Project notes")]
    assert db.content == [(3, "Captured audio"), (4, "Transcription Failed: Worker stopped")]
    assert db.renamed == [(3, "Voice memo")]


def test_delete_action_deletes_entry_even_when_no_audio_file_is_present():
    db = _NotebookPort()

    assert delete_entry_and_audio(db, 9) is None
    assert db.deleted == [9]
