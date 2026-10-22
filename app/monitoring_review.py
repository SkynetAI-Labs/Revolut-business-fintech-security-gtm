"""Administrator review decisions without modifying detection evidence."""

from datetime import datetime, timezone


def review_alert(connection, alert_id, reviewer_id, new_status):
    """Apply one final decision inside the caller's transaction."""
    for name, value in (("alert_id", alert_id), ("reviewer_id", reviewer_id)):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer.")

    if new_status not in ("reviewed", "dismissed"):
        raise ValueError("Review status must be reviewed or dismissed.")

    if not connection.in_transaction:
        raise ValueError("Alert review requires an explicit transaction.")

    reviewer = connection.execute(
        "SELECT role FROM users WHERE id = ?",
        (reviewer_id,),
    ).fetchone()
    if reviewer is None or reviewer["role"] != "admin":
        raise PermissionError("Administrator access required.")

    reviewed_at = datetime.now(timezone.utc).isoformat()
    cursor = connection.execute(
        "UPDATE monitoring_alerts "
        "SET status = ?, reviewed_by = ?, reviewed_at = ? "
        "WHERE id = ? AND status = 'open'",
        (new_status, reviewer_id, reviewed_at, alert_id),
    )

    if cursor.rowcount != 1:
        existing = connection.execute(
            "SELECT status FROM monitoring_alerts WHERE id = ?",
            (alert_id,),
        ).fetchone()
        if existing is None:
            raise LookupError("Alert not found.")
        raise RuntimeError("Alert already has a final review decision.")

    return {
        "id": alert_id,
        "status": new_status,
        "reviewed_by": reviewer_id,
        "reviewed_at": reviewed_at,
    }
