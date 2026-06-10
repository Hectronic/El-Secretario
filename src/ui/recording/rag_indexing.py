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
# along with this program.  See <https://www.gnu.org/licenses/>.

import logging

SKIPPED_STATUS = "RAG auto-index skipped (auto_index_rag=false)."


def should_auto_index_rag(settings):
    return settings.value("auto_index_rag", True, type=bool)


def index_transcription_result_after_refresh(
    *,
    rag,
    db,
    settings,
    record_id,
    title,
    date_label,
    emit_status,
):
    if not rag:
        return False
    if not should_auto_index_rag(settings):
        emit_status(SKIPPED_STATUS)
        logging.info("Post-transcription checkpoint P10b: RAG auto-index skipped by settings")
        return False

    logging.info("Post-transcription checkpoint P10: RAG auto-index enabled")
    ai_text = db.get_record_ai_text(record_id)
    logging.info("Post-transcription checkpoint P11: fetched ai_text (len=%s)", len(ai_text or ""))
    rag.add_document(record_id, ai_text, {"title": title, "date": date_label})
    logging.info("Post-transcription checkpoint P12: rag.add_document completed")
    return True


def index_saved_record_changes(
    *,
    rag,
    db,
    settings,
    record_id,
    transcription,
    notes,
    title,
    date_label,
    tags,
):
    if not rag or not should_auto_index_rag(settings):
        return False

    ai_text = db.compose_ai_text(transcription, notes)
    rag.add_document(
        record_id,
        ai_text,
        {"title": title, "date": date_label, "tags": tags},
    )
    return True
