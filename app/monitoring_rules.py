"""Explainable rules for fictional transaction monitoring."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MonitoringConfig:
    large_transfer_pence: int = 500000
    frequency_count: int = 5
    frequency_window_seconds: int = 600
    outgoing_value_pence: int = 1000000
    outgoing_window_seconds: int = 3600
    repeated_count: int = 3
    repeated_window_seconds: int = 300

    def __post_init__(self):
        for name, value in vars(self).items():
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")


@dataclass(frozen=True)
class RuleMatch:
    rule_code: str
    severity: str
    evidence: dict


def detect_large_transfer(
    amount_pence: int,
    currency: str,
    config: MonitoringConfig,
) -> RuleMatch | None:
    if type(amount_pence) is not int or amount_pence <= 0:
        raise ValueError("amount_pence must be a positive integer.")

    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("currency must be a non-empty string.")

    if currency != "GBP" or amount_pence <= config.large_transfer_pence:
        return None

    return RuleMatch(
        rule_code="LARGE_TRANSFER",
        severity="medium",
        evidence={
            "rule_version": 1,
            "amount_pence": amount_pence,
            "currency": currency,
            "threshold_pence": config.large_transfer_pence,
        },
    )


def detect_transfer_frequency(
    outgoing_count: int,
    config: MonitoringConfig,
) -> RuleMatch | None:
    if type(outgoing_count) is not int or outgoing_count < 1:
        raise ValueError(
            "outgoing_count must be a positive integer including the trigger."
        )

    if outgoing_count <= config.frequency_count:
        return None

    return RuleMatch(
        rule_code="HIGH_TRANSFER_FREQUENCY",
        severity="medium",
        evidence={
            "rule_version": 1,
            "outgoing_count": outgoing_count,
            "threshold_count": config.frequency_count,
            "window_seconds": config.frequency_window_seconds,
        },
    )


def detect_outgoing_value(
    total_pence: int,
    currency: str,
    config: MonitoringConfig,
) -> RuleMatch | None:
    if type(total_pence) is not int or total_pence <= 0:
        raise ValueError("total_pence must be a positive integer.")

    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("currency must be a non-empty string.")

    if currency != "GBP" or total_pence <= config.outgoing_value_pence:
        return None

    return RuleMatch(
        rule_code="HIGH_OUTGOING_VALUE",
        severity="high",
        evidence={
            "rule_version": 1,
            "total_pence": total_pence,
            "currency": currency,
            "threshold_pence": config.outgoing_value_pence,
            "window_seconds": config.outgoing_window_seconds,
        },
    )


def detect_repeated_transfers(
    repeated_count: int,
    config: MonitoringConfig,
) -> RuleMatch | None:
    if type(repeated_count) is not int or repeated_count < 1:
        raise ValueError(
            "repeated_count must be a positive integer including the trigger."
        )

    if repeated_count <= config.repeated_count:
        return None

    return RuleMatch(
        rule_code="RAPID_REPEATED_TRANSFERS",
        severity="high",
        evidence={
            "rule_version": 1,
            "transfer_count": repeated_count,
            "threshold_count": config.repeated_count,
            "window_seconds": config.repeated_window_seconds,
        },
    )
