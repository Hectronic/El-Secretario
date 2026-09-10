"""Persistence and RAG context operations for the standalone chat window."""

import json


def build_window_context(rag_engine, query, collection):
    """Search the selected collection and return the chat context text."""
    results = rag_engine.search(query, n_results=5, tag_filter=collection)
    context = "\n\n".join(f"Note: {result['text']}" for result in results)
    return context or "No relevant notes found for this query."


def load_window_session(persistence, session_id):
    """Return the selected stored session, if it still exists."""
    return next(
        (session for session in persistence.fetch_chat_sessions() if session["id"] == session_id),
        None,
    )


def save_window_session(persistence, session_id, history, collection):
    """Create or update a standalone chat session and return its identifier."""
    messages = json.dumps(history)
    if session_id:
        persistence.update_chat_session(session_id, messages)
        return session_id
    name = history[0]["content"][:30] + "..."
    return persistence.save_chat_session(name, collection, messages)
