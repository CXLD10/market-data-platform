from datetime import datetime, timezone

from app.utils.validators import normalize_timestamp, to_native_float


def test_timestamp_normalization_to_utc():
    ts = normalize_timestamp("2024-01-01T10:00:00+05:30")
    assert ts.tzinfo == timezone.utc
    assert ts.hour == 4


def test_numeric_cleaning_nan():
    assert to_native_float(float('nan')) == 0.0


def test_native_types():
    value = to_native_float(1)
    assert isinstance(value, float)
    assert value == 1.0
