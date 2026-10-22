"""Transaction assessment using the caller's database connection."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.monitoring_rules import (
    MonitoringConfig,
    RuleMatch,
    detect_large_transfer,
    detect_outgoing_value,
    detect_repeated_transfers,
    detect_transfer_frequency,
)


@dataclass(frozen=True)
class TransactionAssessment:
    transaction_id: int
    customer_id: int
    transaction_at: str
    matches: tuple[RuleMatch, ...]


def parse_transaction_time(value: str) -> datetime:
    """Treat SQLite's naive CURRENT_TIMESTAMP values as UTC."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def assess_transaction(
    connection,
    transaction_id: int,
    config: MonitoringConfig | None = None,
) -> TransactionAssessment:
    if type(transaction_id) is not int or transaction_id <= 0:
        raise ValueError("transaction_id must be a positive integer.")

    config = config if config is not None else MonitoringConfig()
    trigger = connection.execute(
        "SELECT t.id, t.from_account_id, t.to_account_id, "
        "t.amount_pence, t.created_at, a.customer_id, a.currency "
        "FROM transactions AS t "
        "JOIN accounts AS a ON a.id = t.from_account_id "
        "WHERE t.id = ?",
        (transaction_id,),
    ).fetchone()

    if trigger is None:
        raise ValueError("Transaction or sender account not found.")

    trigger_time = parse_transaction_time(trigger["created_at"])
    windows = {
        "frequency": config.frequency_window_seconds,
        "outgoing": config.outgoing_window_seconds,
        "repeated": config.repeated_window_seconds,
    }
    lower_bounds = {
        name: trigger_time - timedelta(seconds=seconds)
        for name, seconds in windows.items()
    }

    # Read only this sender's history. Timestamp filtering is performed
    # explicitly in UTC so boundary and equal-time ordering are consistent.
    history = connection.execute(
        "SELECT id, to_account_id, amount_pence, created_at "
        "FROM transactions WHERE from_account_id = ?",
        (trigger["from_account_id"],),
    ).fetchall()

    frequency_count = 0
    outgoing_total = 0
    repeated_count = 0

    for row in history:
        occurred = parse_transaction_time(row["created_at"])
        if (occurred, row["id"]) > (trigger_time, trigger["id"]):
            continue
        if occurred >= lower_bounds["frequency"]:
            frequency_count += 1
        if occurred >= lower_bounds["outgoing"]:
            outgoing_total += row["amount_pence"]
        if (
            occurred >= lower_bounds["repeated"]
            and row["to_account_id"] == trigger["to_account_id"]
        ):
            repeated_count += 1

    candidates = (
        detect_large_transfer(
            trigger["amount_pence"], trigger["currency"], config
        ),
        detect_transfer_frequency(frequency_count, config),
        detect_outgoing_value(outgoing_total, trigger["currency"], config),
        detect_repeated_transfers(repeated_count, config),
    )

    matches = []
    for match in candidates:
        if match is None:
            continue
        evidence = dict(match.evidence)
        if "window_seconds" in evidence:
            evidence["window_start"] = (
                trigger_time - timedelta(seconds=evidence["window_seconds"])
            ).isoformat()
            evidence["window_end"] = trigger_time.isoformat()
            evidence["upper_transaction_id"] = transaction_id
        matches.append(RuleMatch(
            rule_code=match.rule_code,
            severity=match.severity,
            evidence=evidence,
        ))

    return TransactionAssessment(
        transaction_id=transaction_id,
        customer_id=trigger["customer_id"],
        transaction_at=trigger_time.isoformat(),
        matches=tuple(matches),
    )


def monitor_transaction(connection, transaction_id, config=None):
    """Store alerts without committing; the caller owns the transaction."""
    import json

    assessment = assess_transaction(connection, transaction_id, config)
    for match in assessment.matches:
        connection.execute(
            "INSERT INTO monitoring_alerts "
            "(transaction_id, customer_id, rule_code, severity, "
            "evidence_json, transaction_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(transaction_id, rule_code) DO NOTHING",
            (
                assessment.transaction_id,
                assessment.customer_id,
                match.rule_code,
                match.severity,
                json.dumps(match.evidence, sort_keys=True, allow_nan=False),
                assessment.transaction_at,
            ),
        )
    return assessment


def analyse_historical_transactions(
    connection,
    *,
    after_id=0,
    limit=100,
    up_to_id=None,
    config=None,
):
    """Analyse a bounded batch within an explicit caller-owned transaction.

    Keep the returned up_to_id for subsequent batches in the same replay.
    This function never commits or changes financial transaction records.
    """
    if type(after_id) is not int or after_id < 0:
        raise ValueError("after_id must be a non-negative integer.")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("limit must be an integer between 1 and 1000.")
    if up_to_id is not None and (
        type(up_to_id) is not int or up_to_id < 0
    ):
        raise ValueError("up_to_id must be a non-negative integer.")
    if not connection.in_transaction:
        raise ValueError("Historical analysis requires an explicit transaction.")

    if up_to_id is None:
        up_to_id = connection.execute(
            "SELECT COALESCE(MAX(id), 0) FROM transactions"
        ).fetchone()[0]

    rows = connection.execute(
        "SELECT id FROM transactions "
        "WHERE id > ? AND id <= ? ORDER BY id LIMIT ?",
        (after_id, up_to_id, limit),
    ).fetchall()

    config = config if config is not None else MonitoringConfig()
    changes_before = connection.total_changes

    for row in rows:
        monitor_transaction(connection, row["id"], config)

    next_after_id = rows[-1]["id"] if rows else after_id
    has_more = connection.execute(
        "SELECT 1 FROM transactions WHERE id > ? AND id <= ? LIMIT 1",
        (next_after_id, up_to_id),
    ).fetchone() is not None

    return {
        "processed_count": len(rows),
        "alerts_created": connection.total_changes - changes_before,
        "next_after_id": next_after_id,
        "up_to_id": up_to_id,
        "has_more": has_more,
    }
