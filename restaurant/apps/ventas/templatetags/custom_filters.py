from django import template
from decimal import Decimal, ROUND_DOWN, InvalidOperation

register = template.Library()


@register.filter
def mil(value):
    try:
        if value is None:
            return '0'
        value = Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_DOWN)
        parts = []
        s = str(int(value))
        while s:
            parts.append(s[-3:])
            s = s[:-3]
        return '.'.join(reversed(parts))
    except (ValueError, TypeError, InvalidOperation):
        return str(value) if value is not None else '0'
