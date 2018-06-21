def to_bool(v):
    """
    Turn a string into a boolean.
    Cry silently into your pillow.
    """
    if not v:
        return False

    if isinstance(v, bool):
        return v

    if isinstance(v, str):
        v = v.encode('utf-8')

    return v.lower() in (b"yes", b"true", b"t", b"1")