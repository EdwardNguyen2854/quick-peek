from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import require_permission
from ..db import get_conn, rows_to_dicts

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(user=Depends(require_permission("view_dashboard"))):
    with get_conn() as conn:
        totals = conn.execute(
            """
            SELECT
              COUNT(CASE WHEN action='search' THEN 1 END) AS searches,
              COUNT(CASE WHEN action='open_preview' THEN 1 END) AS opened_previews,
              COALESCE(SUM(files_found),0) AS files_found,
              COALESCE(SUM(seconds_saved),0) AS seconds_saved
            FROM usage_logs
            """
        ).fetchone()
        by_format = conn.execute(
            """
            SELECT format, COUNT(*) as events, COALESCE(SUM(files_found),0) as files_found,
                   COALESCE(SUM(seconds_saved),0) as seconds_saved
            FROM usage_logs
            WHERE format IS NOT NULL
            GROUP BY format
            ORDER BY events DESC
            """
        ).fetchall()
        top_users = conn.execute(
            """
            SELECT u.username, COUNT(l.id) as events, COALESCE(SUM(l.files_found),0) as files_found,
                   COALESCE(SUM(l.seconds_saved),0) as seconds_saved
            FROM usage_logs l
            LEFT JOIN users u ON u.id = l.user_id
            GROUP BY u.username
            ORDER BY events DESC
            LIMIT 10
            """
        ).fetchall()
        recent = conn.execute(
            """
            SELECT l.created_at, u.username, l.action, l.format, l.codes_count, l.files_found, l.seconds_saved
            FROM usage_logs l
            LEFT JOIN users u ON u.id = l.user_id
            ORDER BY l.id DESC
            LIMIT 30
            """
        ).fetchall()
    return {
        "totals": dict(totals),
        "hours_saved": round((totals["seconds_saved"] or 0) / 3600, 2),
        "by_format": rows_to_dicts(by_format),
        "top_users": rows_to_dicts(top_users),
        "recent": rows_to_dicts(recent),
    }
