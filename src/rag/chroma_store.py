# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os
from dataclasses import dataclass
from typing import Any

from chromadb.config import Settings

from src.rag.chroma_compat import (
    get_or_create_collection_compatible,
    suppress_sentencepiece_swig_deprecation_warnings,
)

suppress_sentencepiece_swig_deprecation_warnings()

from chromadb.utils import embedding_functions
from src.rag.fallback_store import InMemoryChromaClient


@dataclass
class ChromaStore:
    client: Any
    collection: Any
    embedding_fn: Any
    is_persistent: bool


def create_embedding_function(embedding_module=embedding_functions):
    try:
        logging.info("Initializing embedding function (SentenceTransformer)...")
        return embedding_module.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
    except Exception as e:
        logging.warning(f"SentenceTransformer init failed, falling back to default: {e}")
        try:
            embedding_fn = embedding_module.DefaultEmbeddingFunction()
            logging.info("Fallback: Using DefaultEmbeddingFunction (ONNX).")
            return embedding_fn
        except Exception as e2:
            logging.error(f"All embedding functions failed to initialize: {e2}")
            return None


def create_chroma_store(
    persist_directory: str,
    *,
    chromadb_module,
    embedding_module=embedding_functions,
    settings_factory=Settings,
) -> ChromaStore:
    os.makedirs(persist_directory, exist_ok=True)
    chroma_settings = settings_factory(anonymized_telemetry=False)

    try:
        client = chromadb_module.PersistentClient(path=persist_directory, settings=chroma_settings)
        is_persistent = True
    except Exception as e:
        logging.warning(f"Persistent Chroma init failed, using in-memory fallback: {e}")
        client = InMemoryChromaClient()
        is_persistent = False

    embedding_fn = create_embedding_function(embedding_module)
    logging.info(
        "RAG Engine embedding function initialized: %s",
        type(embedding_fn).__name__ if embedding_fn else "None",
    )

    collection = get_or_create_collection_compatible(
        client,
        name="transcriptions",
        embedding_fn=embedding_fn,
    )
    return ChromaStore(
        client=client,
        collection=collection,
        embedding_fn=embedding_fn,
        is_persistent=is_persistent,
    )
