class JsonValidationError(ValueError):
    pass


def require_json_object(payload, error_message='Payload JSON non valido.'):
    if not isinstance(payload, dict):
        raise JsonValidationError(error_message)
    return payload


def parse_positive_int(value, field_name):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise JsonValidationError(f'{field_name} non valido.')

    if parsed <= 0:
        raise JsonValidationError(f'{field_name} non valido.')

    return parsed


def parse_non_negative_int(value, field_name, default=0):
    if value is None:
        return default

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise JsonValidationError(f'{field_name} non valido.')

    if parsed < 0:
        raise JsonValidationError(f'{field_name} non valido.')

    return parsed


def parse_optional_text(value, field_name, max_length=None, strip=True):
    if value is None:
        return None

    if not isinstance(value, str):
        raise JsonValidationError(f'{field_name} non valido.')

    text = value.strip() if strip else value
    if max_length is not None and len(text) > max_length:
        raise JsonValidationError(f'{field_name} troppo lungo.')
    return text


def parse_required_text(value, field_name, max_length=None):
    text = parse_optional_text(value, field_name, max_length=max_length)
    if not text:
        raise JsonValidationError(f'{field_name} obbligatorio.')
    return text


def parse_bool(value, field_name):
    if isinstance(value, bool):
        return value
    raise JsonValidationError(f'{field_name} non valido.')