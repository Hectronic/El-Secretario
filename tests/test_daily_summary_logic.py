
import pytest
import os
import sqlite3
from datetime import date, timedelta
from src.database import DBManager

@pytest.fixture
def db_manager(tmp_path):
    """Fixture para crear una base de datos temporal limpia."""
    db_file = tmp_path / "test_summary_logic.db"
    manager = DBManager(db_name=str(db_file))
    yield manager

def test_get_latest_recording_day_without_daily_summary(db_manager):
    """
    Valida la lógica de negocio para encontrar el último día pendiente de resumen.
    """
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    day_before_yesterday = (date.today() - timedelta(days=2)).isoformat()

    # 1. Escenario: No hay grabaciones -> No hay días pendientes
    assert db_manager.get_latest_recording_day_without_daily_summary(today) is None

    # 2. Escenario: Grabación ayer, sin resumen -> Debe devolver ayer
    with db_manager.get_connection() as conn:
        conn.execute(
            "INSERT INTO records (created_at, filename, duration, transcription, type) VALUES (?, ?, ?, ?, ?)",
            (f"{yesterday} 10:00:00", "rec1.wav", 10.0, "Texto de ayer", "recording")
        )
        conn.commit()

    assert db_manager.get_latest_recording_day_without_daily_summary(today) == yesterday

    # 3. Escenario: Grabación ayer ya tiene resumen -> No hay días pendientes
    db_manager.save_daily_summary(yesterday, "Resumen de ayer", tags_filter=None)
    assert db_manager.get_latest_recording_day_without_daily_summary(today) is None

    # 4. Escenario: Grabación hoy -> NO debe devolver hoy (la jornada no ha terminado)
    with db_manager.get_connection() as conn:
        conn.execute(
            "INSERT INTO records (created_at, filename, duration, transcription, type) VALUES (?, ?, ?, ?, ?)",
            (f"{today} 10:00:00", "rec_today.wav", 10.0, "Texto de hoy", "recording")
        )
        conn.commit()
    assert db_manager.get_latest_recording_day_without_daily_summary(today) is None

    # 5. Escenario: Múltiples días pendientes -> Debe devolver el más reciente (excluyendo hoy)
    with db_manager.get_connection() as conn:
        conn.execute(
            "INSERT INTO records (created_at, filename, duration, transcription, type) VALUES (?, ?, ?, ?, ?)",
            (f"{day_before_yesterday} 10:00:00", "rec_old.wav", 10.0, "Texto antiguo", "recording")
        )
        conn.commit()
    # Actualmente ayer tiene resumen, anteayer no.
    assert db_manager.get_latest_recording_day_without_daily_summary(today) == day_before_yesterday

def test_daily_summary_with_tags_logic(db_manager):
    """
    Valida que la lógica de pendientes discrimine por etiquetas (tags).
    """
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today = date.today().isoformat()

    # Grabación de ayer con tag "Trabajo"
    with db_manager.get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO records (created_at, filename, duration, transcription, tags, type) VALUES (?, ?, ?, ?, ?, ?)",
            (f"{yesterday} 09:00:00", "work.wav", 10.0, "Contenido trabajo", "Trabajo", "recording")
        )
        conn.commit()
        rec_id = cursor.lastrowid

    # Sin resumen para "Trabajo" -> Pendiente
    assert db_manager.get_latest_recording_day_without_daily_summary(today, tags_filter="Trabajo") == yesterday
    
    # Si creamos un resumen global (sin tag), el de "Trabajo" sigue pendiente
    db_manager.save_daily_summary(yesterday, "Resumen Global", tags_filter=None)
    assert db_manager.get_latest_recording_day_without_daily_summary(today, tags_filter="Trabajo") == yesterday

    # Si creamos el resumen de "Trabajo", ya no hay pendientes
    db_manager.save_daily_summary(yesterday, "Resumen Trabajo", tags_filter="Trabajo")
    assert db_manager.get_latest_recording_day_without_daily_summary(today, tags_filter="Trabajo") is None
