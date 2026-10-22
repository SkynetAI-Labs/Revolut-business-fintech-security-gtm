from app.rate_limiting import limiter
"""Authenticated, customer-scoped and administrator alert retrieval."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict

from app.database import get_connection
from app.dependencies import get_current_customer_id, require_admin

router = APIRouter(prefix="/monitoring", tags=["Transaction monitoring"])

AlertStatus = Literal["open", "reviewed", "dismissed"]
AlertSeverity = Literal["medium", "high"]
RuleCode = Literal[
    "LARGE_TRANSFER",
    "HIGH_TRANSFER_FREQUENCY",
    "HIGH_OUTGOING_VALUE",
    "RAPID_REPEATED_TRANSFERS",
]


class MonitoringAlertResponse(BaseModel):
    id: int
    transaction_id: int
    rule_code: RuleCode
    severity: AlertSeverity
    evidence: dict
    transaction_at: str
    detected_at: str
    status: AlertStatus


class AdministratorAlertResponse(MonitoringAlertResponse):
    customer_id: int
    reviewed_by: int | None
    reviewed_at: str | None


def alert_filters(
    status: AlertStatus | None = None,
    severity: AlertSeverity | None = None,
    rule_code: RuleCode | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    before_id: int | None = Query(default=None, gt=0),
):
    return {
        "status": status,
        "severity": severity,
        "rule_code": rule_code,
        "limit": limit,
        "before_id": before_id,
    }


def read_alerts(
    customer_id,
    *,
    status,
    severity,
    rule_code,
    limit,
    before_id,
):
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT id, transaction_id, customer_id, rule_code, severity, "
            "evidence_json, transaction_at, detected_at, status, "
            "reviewed_by, reviewed_at "
            "FROM monitoring_alerts "
            "WHERE (? IS NULL OR customer_id = ?) "
            "AND (? IS NULL OR status = ?) "
            "AND (? IS NULL OR severity = ?) "
            "AND (? IS NULL OR rule_code = ?) "
            "AND (? IS NULL OR id < ?) "
            "ORDER BY id DESC LIMIT ?",
            (
                customer_id, customer_id,
                status, status,
                severity, severity,
                rule_code, rule_code,
                before_id, before_id,
                limit,
            ),
        ).fetchall()

        results = []
        for row in rows:
            record = dict(row)
            record["evidence"] = json.loads(record.pop("evidence_json"))
            results.append(record)
        return results
    finally:
        connection.close()


@router.get("/alerts", response_model=list[MonitoringAlertResponse])
@limiter.limit("30/minute")
def list_customer_alerts(
    request: Request,
    customer_id: int = Depends(get_current_customer_id),
    filters: dict = Depends(alert_filters),
):
    return read_alerts(customer_id, **filters)


@router.get("/admin/alerts", response_model=list[AdministratorAlertResponse])
@limiter.limit("10/minute")
def list_administrator_alerts(
    request: Request,
    administrator_id: int = Depends(require_admin),
    customer_id: int | None = Query(default=None, gt=0),
    filters: dict = Depends(alert_filters),
):
    return read_alerts(customer_id, **filters)


class AlertReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["reviewed", "dismissed"]


class AlertReviewResponse(BaseModel):
    id: int
    status: Literal["reviewed", "dismissed"]
    reviewed_by: int
    reviewed_at: str


@router.patch(
    "/admin/alerts/{alert_id}/review",
    response_model=AlertReviewResponse,
)
@limiter.limit("10/minute")
def review_monitoring_alert(
    request: Request,
    decision: AlertReviewRequest,
    alert_id: int = Path(gt=0),
    administrator_id: int = Depends(require_admin),
):
    from app.monitoring_review import review_alert

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        result = review_alert(
            connection, alert_id, administrator_id, decision.status
        )
        connection.commit()
        return result
    except PermissionError as error:
        connection.rollback()
        raise HTTPException(
            status_code=403, detail="Administrator access required"
        ) from error
    except LookupError as error:
        connection.rollback()
        raise HTTPException(
            status_code=404, detail="Alert not found"
        ) from error
    except RuntimeError as error:
        connection.rollback()
        raise HTTPException(
            status_code=409, detail="Alert already has a final review decision"
        ) from error
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
