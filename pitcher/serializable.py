from datetime import datetime, date, time
from functools import singledispatch
from decimal import Decimal


@singledispatch
def to_serializable(val):
    """Used by default."""
    return str(val)


@to_serializable.register
def serialize_date(val: date) -> str:
    return val.isoformat()


@to_serializable.register
def serialize_time(val: time) -> str:
    representation = val.isoformat(timespec="seconds")
    return representation


@to_serializable.register
def serialize_datetime(val: datetime) -> str:
    representation = val.isoformat(timespec="seconds")
    if representation.endswith("+00:00"):
        representation = representation[:-6] + "Z"
    return representation


@to_serializable.register(float)
@to_serializable.register(Decimal)
def serialize_decimal(val) -> str:
    return str(val)
