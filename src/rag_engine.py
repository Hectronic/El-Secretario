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

import chromadb
from chromadb.utils import embedding_functions
import os
from typing import List, Dict, Any, Optional

class RAGEngine:
    def __init__(self, persist_directory: str = "chroma_db"):
        import logging
        self.persist_directory = persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        # Initialize ChromaDB client. Fall back to in-memory client when
        # persistence is unavailable in the current environment.
        try:
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.is_persistent = True
        except Exception as e:
            logging.warning(f"Persistent Chroma init failed, using in-memory fallback: {e}")
            self.client = chromadb.Client()
            self.is_persistent = False
        
        # Use default embedding function (all-MiniLM-L6-v2)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="transcriptions",
            embedding_function=self.embedding_fn
        )

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add or update a document in the vector store.
        doc_id: Unique ID (string)
        text: The transcription text
        metadata: Dict with extra info (e.g., title, date)
        """
        if not text:
            return

        # Ensure ID is in metadata for filtering
        if metadata is None:
            metadata = {}
        metadata['id'] = str(doc_id)

        # ChromaDB upsert handles both add and update
        self.collection.upsert(
            ids=[str(doc_id)],
            documents=[text],
            metadatas=[metadata]
        )

    def search(self, query: str, n_results: int = 5, tag_filter: Optional[str] = None, where_clause: Optional[Dict[str, Any]] = None, ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search for documents relevant to the query.
        Returns a list of results (id, text, metadata, distance).
        ids: Optional list of document IDs to restrict search to.
        """
        final_where = {}
        
        # If explicit where_clause is provided, use it
        if where_clause:
            final_where = where_clause.copy()
        
        # Tag filter - REMOVED because $contains is not supported by ChromaDB
        # Caller should resolve tags to IDs and pass them in 'ids' argument
        # if tag_filter and tag_filter != "All":
        #     final_where["tags"] = {"$contains": tag_filter}
            
        # ID filter (if provided)
        if ids:
            if len(ids) == 1:
                final_where["id"] = ids[0]
            else:
                final_where["id"] = {"$in": ids}
                
        # If no filters, set to None
        if not final_where:
            final_where = None

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=final_where
        )
        
        # Parse results into a cleaner format
        parsed_results = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                parsed_results.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0.0
                })
                
        return parsed_results


    def delete_document(self, doc_id: str) -> None:
        """Delete a document by ID."""
        try:
            self.collection.delete(ids=[str(doc_id)])
        except Exception as e:
            print(f"Error deleting document {doc_id}: {e}")
