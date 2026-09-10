from src.rag.documents import add_document, delete_document


class _Collection:
    def __init__(self):
        self.upserts = []
        self.deletes = []

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)

    def delete(self, **kwargs):
        self.deletes.append(kwargs)


def test_add_document_normalizes_metadata_and_uses_collection_in_process():
    collection = _Collection()

    add_document(
        collection,
        persist_directory="db",
        doc_id=4,
        text="planning notes",
        metadata={"title": "Plan"},
        use_subprocess=False,
        upsert_in_subprocess=lambda **_kwargs: False,
    )

    assert collection.upserts == [{
        "ids": ["4"],
        "documents": ["planning notes"],
        "metadatas": [{"title": "Plan", "id": "4", "deleted": "0"}],
    }]


def test_add_document_uses_windows_subprocess_without_in_process_retry():
    collection = _Collection()
    calls = []

    add_document(
        collection,
        persist_directory="db",
        doc_id="4",
        text="planning notes",
        metadata=None,
        use_subprocess=True,
        upsert_in_subprocess=lambda **kwargs: calls.append(kwargs) or False,
    )

    assert collection.upserts == []
    assert calls == [{
        "persist_directory": "db",
        "doc_id": "4",
        "text": "planning notes",
        "metadata": {"id": "4", "deleted": "0"},
        "timeout_seconds": 30,
    }]


def test_empty_document_is_ignored_and_safe_delete_uses_marker():
    collection = _Collection()
    add_document(
        collection,
        persist_directory="db",
        doc_id="ignored",
        text="",
        metadata=None,
        use_subprocess=False,
        upsert_in_subprocess=lambda **_kwargs: True,
    )
    delete_document(
        collection,
        persist_directory="db",
        doc_id="4",
        safe_delete_mode=True,
        use_subprocess=False,
        upsert_in_subprocess=lambda **_kwargs: True,
    )

    assert collection.upserts == [{
        "ids": ["4"],
        "documents": [""],
        "metadatas": [{"id": "4", "deleted": "1"}],
    }]
    assert collection.deletes == []


def test_hard_delete_delegates_to_collection():
    collection = _Collection()

    delete_document(
        collection,
        persist_directory="db",
        doc_id=4,
        safe_delete_mode=False,
        use_subprocess=False,
        upsert_in_subprocess=lambda **_kwargs: True,
    )

    assert collection.deletes == [{"ids": ["4"]}]
