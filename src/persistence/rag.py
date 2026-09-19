"""Persistence operations for RAG indexing status."""

from .base import PersistenceBase

from .base import RepositoryBase

class RAGIndexRepository(RepositoryBase):
    def get_rag_index_status(self, source_id: str) -> dict:
        """Get the indexing status for a given source."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT source_id, content_fingerprint, status, indexed_at FROM rag_index_status WHERE source_id = ?",
                (source_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "source_id": row[0],
                    "content_fingerprint": row[1],
                    "status": row[2],
                    "indexed_at": row[3],
                }
            return None

    def upsert_rag_index_status(self, source_id: str, content_fingerprint: str, status: str) -> None:
        """Upsert the indexing status for a source."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO rag_index_status (source_id, content_fingerprint, status, indexed_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(source_id) DO UPDATE SET
                    content_fingerprint=excluded.content_fingerprint,
                    status=excluded.status,
                    indexed_at=CURRENT_TIMESTAMP
                ''',
                (source_id, content_fingerprint, status)
            )
            conn.commit()
