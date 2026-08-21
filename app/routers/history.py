# Patient History
from fastapi import APIRouter, Depends
from app.database import query_all, query_one
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/history", tags=["history"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_history(limit: int = 20):
    """history.html 'Recent Events' feed"""
    limit = min(limit, 100)

    rows = query_all(
        """SELECT h.id, h.event_type, h.title, h.description, h.icon_color, h.created_at,
                  p.slug AS patient_slug, p.name AS patient_name
           FROM history_events h
           JOIN patients p ON p.id = h.patient_id
           ORDER BY h.created_at DESC
           LIMIT %s""",
        (limit,),
    )

    return [
        {
            "id": r["id"],
            "eventType": r["event_type"],
            "title": r["title"],
            "description": r["description"],
            "iconColor": r["icon_color"],
            "createdAt": r["created_at"],
            "patient": {"slug": r["patient_slug"], "name": r["patient_name"]},
        }
        for r in rows
    ]


@router.get("/summary")
def get_history_summary():
    """history.html 'Summary' grid (Falls / Resolved / Events)"""
    falls = query_one("SELECT COUNT(*) AS c FROM history_events WHERE event_type = 'fall'")["c"]
    resolved = query_one("SELECT COUNT(*) AS c FROM history_events WHERE event_type = 'resolved'")["c"]
    events = query_one("SELECT COUNT(*) AS c FROM history_events")["c"]

    return {"falls": falls, "resolved": resolved, "events": events}
