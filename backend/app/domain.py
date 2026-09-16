import math
import re


def normalize_plate(value: str) -> str:
    value = re.sub(r'[\s-]', '', value.upper())
    if not re.fullmatch(r'[A-Z]{3}[0-9][A-Z0-9][0-9]{2}', value):
        raise ValueError('Informe uma placa brasileira válida, como ABC1D23 ou ABC1234.')
    return value


def price_cents(seconds: int, first_hour: int, extra_hour: int, grace_minutes: int) -> int:
    """Tolerância isenta a estadia inteira; depois dela cobra desde a entrada."""
    if seconds < 0:
        raise ValueError('A saída não pode ser anterior à entrada.')
    if seconds <= grace_minutes * 60:
        return 0
    return first_hour + max(0, math.ceil((seconds - 3600) / 3600)) * extra_hour
