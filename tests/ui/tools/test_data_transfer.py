from types import SimpleNamespace

from src.ui.tools.data_transfer import export_all_data, import_all_data


class _Exporter:
    def __init__(self, _db, _notebook_db):
        pass

    def export_all(self, _path):
        return {"records_count": 2, "chat_sessions_count": 1, "notebooks_count": 3}

    def import_all(self, _path):
        counts = SimpleNamespace(imported=1, skipped=2)
        return SimpleNamespace(success=True, records=counts, chat_sessions=counts, notebooks=counts)


def test_data_transfer_helpers_format_successful_export_and_import():
    _stats, export_message = export_all_data(object(), object(), "/tmp/export.json", _Exporter)
    _result, import_message = import_all_data(object(), object(), "/tmp/import.json", _Exporter)

    assert "Records: 2" in export_message
    assert import_message.count("1 imported, 2 skipped") == 3
