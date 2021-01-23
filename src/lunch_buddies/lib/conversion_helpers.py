from typing import Union

from datetime import datetime
from decimal import Decimal


def convert_datetime_to_decimal(var: datetime) -> Decimal:
    return Decimal(var.timestamp())


def convert_datetime_from_dynamo(var: Union[str, int, Decimal, None]) -> datetime:
    if not var:
        raise Exception("valid datetime not provided")

    return datetime.fromtimestamp(float(var))
