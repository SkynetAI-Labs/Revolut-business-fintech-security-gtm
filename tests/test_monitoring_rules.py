import pytest

from app.monitoring_rules import (
    MonitoringConfig,
    detect_large_transfer,
    detect_outgoing_value,
    detect_repeated_transfers,
    detect_transfer_frequency,
)


@pytest.mark.parametrize("amount,expected", [
    (499999, False), (500000, False), (500001, True),
])
def test_large_transfer_boundary(amount, expected):
    result = detect_large_transfer(amount, "GBP", MonitoringConfig())
    assert (result is not None) is expected


@pytest.mark.parametrize("count,expected", [
    (4, False), (5, False), (6, True),
])
def test_frequency_boundary(count, expected):
    result = detect_transfer_frequency(count, MonitoringConfig())
    assert (result is not None) is expected


@pytest.mark.parametrize("total,expected", [
    (999999, False), (1000000, False), (1000001, True),
])
def test_outgoing_value_boundary(total, expected):
    result = detect_outgoing_value(total, "GBP", MonitoringConfig())
    assert (result is not None) is expected


@pytest.mark.parametrize("count,expected", [
    (2, False), (3, False), (4, True),
])
def test_repeated_transfer_boundary(count, expected):
    result = detect_repeated_transfers(count, MonitoringConfig())
    assert (result is not None) is expected


@pytest.mark.parametrize("currency", ["USD", "EUR"])
def test_amount_rules_do_not_treat_other_currencies_as_gbp(currency):
    config = MonitoringConfig()
    assert detect_large_transfer(2000000, currency, config) is None
    assert detect_outgoing_value(2000000, currency, config) is None


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "6", None])
def test_rules_reject_invalid_numeric_inputs(value):
    config = MonitoringConfig()
    for rule in (detect_large_transfer, detect_outgoing_value):
        with pytest.raises(ValueError):
            rule(value, "GBP", config)
    for rule in (detect_transfer_frequency, detect_repeated_transfers):
        with pytest.raises(ValueError):
            rule(value, config)


@pytest.mark.parametrize("currency", ["", " ", None, 123])
def test_amount_rules_reject_invalid_currency(currency):
    config = MonitoringConfig()
    for rule in (detect_large_transfer, detect_outgoing_value):
        with pytest.raises(ValueError):
            rule(2000000, currency, config)


@pytest.mark.parametrize("field", list(MonitoringConfig.__dataclass_fields__))
@pytest.mark.parametrize("value", [0, -1, True, 1.5, "5", None])
def test_config_rejects_invalid_thresholds(field, value):
    with pytest.raises(ValueError):
        MonitoringConfig(**{field: value})


def test_custom_thresholds_are_used():
    config = MonitoringConfig(
        large_transfer_pence=100,
        frequency_count=1,
        outgoing_value_pence=200,
        repeated_count=1,
    )
    assert detect_large_transfer(101, "GBP", config) is not None
    assert detect_transfer_frequency(2, config) is not None
    assert detect_outgoing_value(201, "GBP", config) is not None
    assert detect_repeated_transfers(2, config) is not None


def test_matches_record_reason_severity_and_evidence():
    config = MonitoringConfig()
    matches = [
        (detect_large_transfer(500001, "GBP", config),
         "LARGE_TRANSFER", "medium", "threshold_pence", 500000),
        (detect_transfer_frequency(6, config),
         "HIGH_TRANSFER_FREQUENCY", "medium", "window_seconds", 600),
        (detect_outgoing_value(1000001, "GBP", config),
         "HIGH_OUTGOING_VALUE", "high", "window_seconds", 3600),
        (detect_repeated_transfers(4, config),
         "RAPID_REPEATED_TRANSFERS", "high", "window_seconds", 300),
    ]
    for match, code, severity, key, expected in matches:
        assert match.rule_code == code
        assert match.severity == severity
        assert match.evidence["rule_version"] == 1
        assert match.evidence[key] == expected
