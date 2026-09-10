"""Data import/export service calls and user-facing status formatting."""

from src.data_export import DataExporter


def export_all_data(db, notebook_db, file_path, exporter_factory=DataExporter):
    stats = exporter_factory(db, notebook_db).export_all(file_path)
    message = (
        f"✓ Export complete! Saved to: {file_path}\n"
        f"Records: {stats['records_count']}, Chat Sessions: {stats['chat_sessions_count']}, "
        f"Notebooks: {stats['notebooks_count']}"
    )
    return stats, message


def import_all_data(db, notebook_db, file_path, exporter_factory=DataExporter):
    result = exporter_factory(db, notebook_db).import_all(file_path)
    if not result.success:
        raise RuntimeError(result.error_message)
    message = (
        "✓ Import complete!\n"
        f"Records: {result.records.imported} imported, {result.records.skipped} skipped\n"
        f"Chat Sessions: {result.chat_sessions.imported} imported, {result.chat_sessions.skipped} skipped\n"
        f"Notebooks: {result.notebooks.imported} imported, {result.notebooks.skipped} skipped"
    )
    return result, message
