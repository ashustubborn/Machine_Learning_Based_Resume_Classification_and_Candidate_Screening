"""
SQLite-backed history of past screenings.
Uses Python's built-in sqlite3, so no extra install is needed.
The database file (history.db) is created automatically in the project folder.
"""

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "history.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(_connect()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS screenings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                job_description TEXT,
                ranked_by TEXT,
                total_uploaded INTEGER,
                results_json TEXT,
                failed_json TEXT
            )
            """
        )
        conn.commit()


def save_screening(job_description, ranked_by, results, failed, total_uploaded):
    created_at = datetime.now(timezone.utc).isoformat()
    with closing(_connect()) as conn:
        cur = conn.execute(
            "INSERT INTO screenings (created_at, job_description, ranked_by, total_uploaded, results_json, failed_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (created_at, job_description, ranked_by, total_uploaded,
             json.dumps(results), json.dumps(failed)),
        )
        conn.commit()
        return cur.lastrowid, created_at


def list_screenings(limit=100):
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM screenings ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    summaries = []
    for row in rows:
        results = json.loads(row["results_json"] or "[]")
        top = results[0] if results else None
        top_score = None
        if top:
            if top.get("match") and top["match"].get("match_percent") is not None:
                top_score = f"{top['match']['match_percent']}% fit"
            else:
                top_score = f"{top['confidence']}% conf."
        jd = (row["job_description"] or "").strip()
        summaries.append({
            "id": row["id"],
            "created_at": row["created_at"],
            "total_uploaded": row["total_uploaded"],
            "screened": len(results),
            "ranked_by": row["ranked_by"],
            "jd_preview": (jd[:90] + "…") if len(jd) > 90 else jd,
            "top_name": top["filename"] if top else None,
            "top_category": top["predicted_category"] if top else None,
            "top_score": top_score,
        })
    return summaries


def get_screening(screening_id):
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM screenings WHERE id = ?", (screening_id,)).fetchone()
    if row is None:
        return None
    results = json.loads(row["results_json"] or "[]")
    return {
        "screening_id": row["id"],
        "created_at": row["created_at"],
        "job_description": row["job_description"] or "",
        "batch_mode": (row["total_uploaded"] or 0) > 1,
        "ranked_by": row["ranked_by"],
        "results": results,
        "failed": json.loads(row["failed_json"] or "[]"),
        "total_uploaded": row["total_uploaded"],
    }


def delete_screening(screening_id):
    with closing(_connect()) as conn:
        cur = conn.execute("DELETE FROM screenings WHERE id = ?", (screening_id,))
        conn.commit()
        return cur.rowcount > 0


def clear_all():
    with closing(_connect()) as conn:
        conn.execute("DELETE FROM screenings")
        conn.commit()
