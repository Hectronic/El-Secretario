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


from __future__ import annotations




class SchemaManager:
    def init_db(self) -> None:
        """Initialize the database and create the table if it doesn't exist."""
        import logging
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    filename TEXT,
                    duration REAL,
                    transcription TEXT,
                    recording_notes TEXT,
                    title TEXT,
                    tags TEXT,
                    summary TEXT,
                    cleaned_text TEXT,
                    is_favorite INTEGER DEFAULT 0,
                    is_diarized INTEGER DEFAULT 0,
                    transcription_model TEXT,
                    processing_attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    type TEXT DEFAULT 'recording'
                )
            ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        collection TEXT,
                        messages TEXT,
                        filter_date TEXT,
                        filter_tags TEXT,
                        context_data TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transcription_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        model_name TEXT,
                        audio_duration REAL,
                        audio_size_bytes INTEGER,
                        transcription_time_seconds REAL,
                        record_id INTEGER,
                        FOREIGN KEY(record_id) REFERENCES records(id)
                    )
                ''')

                # Daily summaries table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        tags_filter TEXT,
                        generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(date, tags_filter)
                    )
                ''')

                # Weekly summaries table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS weekly_summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        week_start TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        tags_filter TEXT,
                        generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(week_start, tags_filter)
                    )
                ''')

                # Tasks table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        record_id INTEGER,
                        day_date TEXT,
                        week_start TEXT NOT NULL,
                        content TEXT NOT NULL,
                        task_origin TEXT,
                        is_ai_generated INTEGER DEFAULT 0,
                        notes TEXT,
                        tags TEXT,
                        is_completed INTEGER DEFAULT 0,
                        completed_at DATETIME,
                        custom_order REAL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE,
                        CHECK(record_id IS NULL OR day_date IS NOT NULL),
                        CHECK(day_date IS NULL OR week_start IS NOT NULL)
                    )
                ''')

                # Migration: Add columns if they don't exist
                cursor.execute("PRAGMA table_info(records)")
                columns = [column[1] for column in cursor.fetchall()]

                if 'title' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN title TEXT')
                if 'recording_notes' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN recording_notes TEXT')
                if 'summary' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN summary TEXT')
                if 'cleaned_text' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN cleaned_text TEXT')
                if 'is_favorite' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN is_favorite INTEGER DEFAULT 0')
                if 'is_diarized' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN is_diarized INTEGER DEFAULT 0')
                if 'transcription_model' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN transcription_model TEXT')
                if 'processing_attempts' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN processing_attempts INTEGER DEFAULT 0')
                if 'last_error' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN last_error TEXT')
                if 'type' not in columns:
                    cursor.execute("ALTER TABLE records ADD COLUMN type TEXT DEFAULT 'recording'")

                # Migration for chat_sessions
                cursor.execute("PRAGMA table_info(chat_sessions)")
                chat_columns = [column[1] for column in cursor.fetchall()]
                if 'filter_date' not in chat_columns:
                    cursor.execute('ALTER TABLE chat_sessions ADD COLUMN filter_date TEXT')
                if 'filter_tags' not in chat_columns:
                    cursor.execute('ALTER TABLE chat_sessions ADD COLUMN filter_tags TEXT')
                if 'context_data' not in chat_columns:
                    cursor.execute('ALTER TABLE chat_sessions ADD COLUMN context_data TEXT')

                # Migration for tasks
                cursor.execute("PRAGMA table_info(tasks)")
                task_info = cursor.fetchall()
                task_columns = {col[1]: col for col in task_info}

                # Rebuild old tasks schema where record_id is required.
                # New model: task can belong to week only, day+week, or record+day+week.
                if "record_id" in task_columns and int(task_columns["record_id"][3]) == 1:
                    cursor.execute("DROP TABLE IF EXISTS tasks_new")
                    cursor.execute('''
                        CREATE TABLE tasks_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            record_id INTEGER,
                            day_date TEXT,
                            week_start TEXT NOT NULL,
                            content TEXT NOT NULL,
                            task_origin TEXT,
                            is_ai_generated INTEGER DEFAULT 0,
                            notes TEXT,
                            tags TEXT,
                            is_completed INTEGER DEFAULT 0,
                            completed_at DATETIME,
                            custom_order REAL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE,
                            CHECK(record_id IS NULL OR day_date IS NOT NULL),
                            CHECK(day_date IS NULL OR week_start IS NOT NULL)
                        )
                    ''')
                    cursor.execute('''
                        INSERT INTO tasks_new (
                            id, record_id, day_date, week_start, content, task_origin, is_ai_generated, notes, tags, is_completed, completed_at, custom_order, created_at
                        )
                        SELECT
                            t.id,
                            CASE WHEN r.id IS NULL THEN NULL ELSE t.record_id END,
                            COALESCE(date(r.created_at), date(t.created_at)),
                            COALESCE(date(r.created_at, 'weekday 0'), date(t.created_at, 'weekday 0'), date('now', 'weekday 0')),
                            t.content,
                            NULL,
                            0,
                            NULL,
                            t.tags,
                            t.is_completed,
                            NULL,
                            NULL,
                            t.created_at
                        FROM tasks t
                        LEFT JOIN records r ON r.id = t.record_id
                    ''')
                    cursor.execute('DROP TABLE tasks')
                    cursor.execute('ALTER TABLE tasks_new RENAME TO tasks')
                    cursor.execute("PRAGMA table_info(tasks)")
                    task_info = cursor.fetchall()
                    task_columns = {col[1]: col for col in task_info}

                if "day_date" not in task_columns:
                    cursor.execute('ALTER TABLE tasks ADD COLUMN day_date TEXT')
                if "week_start" not in task_columns:
                    cursor.execute('ALTER TABLE tasks ADD COLUMN week_start TEXT')
                if "notes" not in task_columns:
                    cursor.execute('ALTER TABLE tasks ADD COLUMN notes TEXT')
                if "task_origin" not in task_columns:
                    cursor.execute('ALTER TABLE tasks ADD COLUMN task_origin TEXT')
                if "is_ai_generated" not in task_columns:
                    cursor.execute('ALTER TABLE tasks ADD COLUMN is_ai_generated INTEGER DEFAULT 0')
                if "completed_at" not in task_columns:
                    cursor.execute('ALTER TABLE tasks ADD COLUMN completed_at DATETIME')
                if "custom_order" not in task_columns:
                    cursor.execute('ALTER TABLE tasks ADD COLUMN custom_order REAL')

                # Backfill day/week context from associated recordings.
                cursor.execute('''
                    UPDATE tasks
                    SET
                        day_date = COALESCE(
                            day_date,
                            (SELECT date(r.created_at) FROM records r WHERE r.id = tasks.record_id)
                        ),
                        week_start = COALESCE(
                            week_start,
                            (SELECT date(r.created_at, 'weekday 0') FROM records r WHERE r.id = tasks.record_id)
                        )
                    WHERE record_id IS NOT NULL
                ''')

                # Ensure day tasks have a week value.
                cursor.execute('''
                    UPDATE tasks
                    SET week_start = date(day_date, 'weekday 0')
                    WHERE day_date IS NOT NULL AND (week_start IS NULL OR week_start = '')
                ''')

                # Absolute safety fallback: never leave week_start empty after migration.
                cursor.execute('''
                    UPDATE tasks
                    SET week_start = COALESCE(
                        week_start,
                        CASE
                            WHEN day_date IS NOT NULL THEN date(day_date, 'weekday 0')
                            ELSE date(created_at, 'weekday 0')
                        END
                    )
                    WHERE week_start IS NULL OR week_start = ''
                ''')

                # Migration: Update existing summaries to have 23:59:59 timestamp
                # Ensures they appear after recordings for the day when sorted by time (if applicable)
                # or just meets user requirement.
                cursor.execute("UPDATE daily_summaries SET generated_at = date || ' 23:59:59' WHERE generated_at NOT LIKE '%23:59:59'")

                # Migration: Update existing weekly summaries from Monday to Sunday
                # strftime('%w', week_start) returns '1' for Monday.
                cursor.execute("UPDATE weekly_summaries SET week_start = date(week_start, '+6 days') WHERE strftime('%w', week_start) = '1'")

                cursor.execute("UPDATE weekly_summaries SET generated_at = week_start || ' 23:59:59' WHERE generated_at NOT LIKE '%23:59:59'")

                # Performance indexes for common filters/sorts.
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_created_at ON records(created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_date ON records(date(created_at))")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_is_favorite ON records(is_favorite)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_is_diarized ON records(is_diarized)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_is_completed_created_at ON tasks(is_completed, created_at DESC)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_custom_order ON tasks(custom_order)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_completed_at ON tasks(completed_at)")

                conn.commit()
            logging.info(f"Database initialized: {self.db_name}")
        except Exception as e:
            logging.critical(f"Database initialization failed: {e}", exc_info=True)
            raise
