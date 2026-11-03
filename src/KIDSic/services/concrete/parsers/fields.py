"""Shared source-field validation; parsers retain their own schema decisions."""
import math
from KIDSic.exceptions import SourceImportError


def text(row: dict, field: str, *, required: bool = False) -> str | None:
    value = row.get(field)
    if value is not None and not isinstance(value, str):
        raise SourceImportError(f'{field} must be text.')
    value = value.strip() if value else None
    if required and not value:
        raise SourceImportError(f'Missing required field: {field}.')
    return value or None


def coordinate(value, maximum: int) -> float | None:
    if value is None or value == '':
        return None
    try:
        number = float(str(value).strip().replace(',', '.'))
    except ValueError as error:
        raise SourceImportError('Invalid coordinate.') from error
    if not math.isfinite(number) or abs(number) > maximum:
        raise SourceImportError('Coordinate outside its valid range.')
    return number

