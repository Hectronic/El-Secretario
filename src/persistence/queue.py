"""Persistence operations for the durable summary queue."""

import json
from .base import PersistenceBase

class QueueJobsRepository(PersistenceBase):
    def save_queue_jobs(self, jobs: list) -> None:
        """Persist the entire queue, replacing existing jobs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM summary_queue_jobs")
            for i, job in enumerate(jobs):
                # Ensure we handle record_id safely
                record_id = job.get('record_id')
                task_type = job.get('type', 'unknown')
                status = job.get('status', 'pending')
                payload = json.dumps(job)
                cursor.execute(
                    '''
                    INSERT INTO summary_queue_jobs (record_id, task_type, payload, status)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (record_id, task_type, payload, status)
                )
            conn.commit()

    def load_queue_jobs(self) -> list:
        """Load pending jobs from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload FROM summary_queue_jobs ORDER BY id ASC"
            )
            rows = cursor.fetchall()
            jobs = []
            for row in rows:
                try:
                    jobs.append(json.loads(row[0]))
                except json.JSONDecodeError:
                    pass
            return jobs
