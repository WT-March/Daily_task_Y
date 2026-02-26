"""Database operations for Pilotage de Survie."""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
from typing import Optional
from config import DATABASE_URL


def get_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ============ TASKS ============

def add_task(title: str, category: str = "Dynamic", justification: str = "", impact: Optional[str] = None) -> dict:
    """Add a new task for today."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tasks (title, category, justification, impact, task_date)
                VALUES (%s, %s, %s, %s, CURRENT_DATE)
                RETURNING id, title, category, completed
            """, (title, category, justification, impact))
            conn.commit()
            return dict(cur.fetchone())


def get_today_tasks() -> list:
    """Get all tasks for today."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, category, completed, justification, impact
                FROM tasks
                WHERE task_date = CURRENT_DATE
                ORDER BY category, id
            """)
            return [dict(row) for row in cur.fetchall()]


def get_incomplete_tasks_today() -> list:
    """Get incomplete tasks for today."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, category
                FROM tasks
                WHERE task_date = CURRENT_DATE AND completed = FALSE
                ORDER BY category, id
            """)
            return [dict(row) for row in cur.fetchall()]


def mark_task_done(task_id: int) -> Optional[dict]:
    """Mark a task as completed."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks
                SET completed = TRUE, completed_at = NOW()
                WHERE id = %s AND task_date = CURRENT_DATE
                RETURNING id, title, completed
            """, (task_id,))
            conn.commit()
            result = cur.fetchone()
            return dict(result) if result else None


def mark_task_undone(task_id: int) -> Optional[dict]:
    """Mark a task as not completed."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks
                SET completed = FALSE, completed_at = NULL
                WHERE id = %s AND task_date = CURRENT_DATE
                RETURNING id, title, completed
            """, (task_id,))
            conn.commit()
            result = cur.fetchone()
            return dict(result) if result else None


def delete_task(task_id: int) -> bool:
    """Delete a task."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM tasks
                WHERE id = %s AND task_date = CURRENT_DATE
                RETURNING id
            """, (task_id,))
            conn.commit()
            return cur.fetchone() is not None


# ============ DAILY NOTES ============

def set_daily_note(note: str) -> dict:
    """Set or update today's note."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO daily_notes (note_date, note)
                VALUES (CURRENT_DATE, %s)
                ON CONFLICT (note_date)
                DO UPDATE SET note = %s, updated_at = NOW()
                RETURNING note_date, note
            """, (note, note))
            conn.commit()
            return dict(cur.fetchone())


def get_daily_note() -> Optional[str]:
    """Get today's note."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT note FROM daily_notes WHERE note_date = CURRENT_DATE
            """)
            result = cur.fetchone()
            return result["note"] if result else None


# ============ STATISTICS ============

def get_today_stats() -> dict:
    """Get statistics for today."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE completed = TRUE) as completed,
                    COUNT(*) FILTER (WHERE completed = FALSE) as pending
                FROM tasks
                WHERE task_date = CURRENT_DATE
            """)
            return dict(cur.fetchone())


def has_tasks_today() -> bool:
    """Check if there are any tasks today."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS(SELECT 1 FROM tasks WHERE task_date = CURRENT_DATE)
            """)
            return cur.fetchone()["exists"]


def has_completed_any_today() -> bool:
    """Check if any task was completed today."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM tasks
                    WHERE task_date = CURRENT_DATE AND completed = TRUE
                )
            """)
            return cur.fetchone()["exists"]


# ============ DEFAULT TASKS ============

def create_default_tasks() -> list:
    """Create default tasks for today if none exist."""
    if has_tasks_today():
        return []

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Get default tasks from config
            cur.execute("SELECT value FROM config WHERE key = 'default_recovery_tasks'")
            recovery = cur.fetchone()
            recovery_tasks = recovery["value"] if recovery else ["Sport", "Anime/Manga", "Sommeil (8h)"]

            cur.execute("SELECT value FROM config WHERE key = 'default_core_tasks'")
            core = cur.fetchone()
            core_tasks = core["value"] if core else ["Apprentissage Rust", "Prospection Cyber"]

            created = []

            # Insert recovery tasks
            for title in recovery_tasks:
                cur.execute("""
                    INSERT INTO tasks (title, category, task_date)
                    VALUES (%s, 'Recovery', CURRENT_DATE)
                    RETURNING id, title, category
                """, (title,))
                created.append(dict(cur.fetchone()))

            # Insert core tasks
            for title in core_tasks:
                cur.execute("""
                    INSERT INTO tasks (title, category, task_date)
                    VALUES (%s, 'Core', CURRENT_DATE)
                    RETURNING id, title, category
                """, (title,))
                created.append(dict(cur.fetchone()))

            conn.commit()
            return created
