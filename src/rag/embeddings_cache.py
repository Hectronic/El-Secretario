"""Persistent, model-scoped cache for RAG embedding vectors."""

import hashlib
import os
import sqlite3
import struct
from contextlib import closing


class EmbeddingsCache:
    def __init__(self, cache_path):
        self.cache_path = os.path.abspath(str(cache_path))
        os.makedirs(os.path.dirname(self.cache_path) or ".", exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS embeddings_cache (
                    text_hash TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    vector_data BLOB NOT NULL,
                    vector_size INTEGER NOT NULL,
                    PRIMARY KEY (text_hash, model_name)
                )"""
            )

    def _connection(self):
        return sqlite3.connect(self.cache_path)

    @staticmethod
    def text_hash(text):
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def serialize(vector):
        values = [float(value) for value in vector]
        if not values:
            raise ValueError("Embedding vectors cannot be empty.")
        return struct.pack(f"!{len(values)}f", *values)

    @staticmethod
    def deserialize(data, vector_size):
        if len(data) != int(vector_size) * 4:
            raise ValueError("Cached embedding blob has an invalid size.")
        return list(struct.unpack(f"!{int(vector_size)}f", data))

    def get(self, text, model_name):
        digest = self.text_hash(text)
        with closing(self._connection()) as connection:
            row = connection.execute(
                "SELECT vector_data, vector_size FROM embeddings_cache WHERE text_hash = ? AND model_name = ?",
                (digest, model_name),
            ).fetchone()
            if row is None:
                return None
            try:
                return self.deserialize(row[0], row[1])
            except ValueError:
                connection.execute(
                    "DELETE FROM embeddings_cache WHERE text_hash = ? AND model_name = ?", (digest, model_name)
                )
                connection.commit()
                return None

    def put(self, text, model_name, vector):
        values = [float(value) for value in vector]
        blob = self.serialize(values)
        with closing(self._connection()) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO embeddings_cache (text_hash, model_name, vector_data, vector_size) VALUES (?, ?, ?, ?)",
                (self.text_hash(text), model_name, blob, len(values)),
            )
            connection.commit()
        return values

    def get_or_create(self, text, model_name, create_vector):
        cached = self.get(text, model_name)
        if cached is not None:
            return cached
        return self.put(text, model_name, create_vector(text))
