class ParserFindTagException(Exception):
    """Вызывается, когда парсер не может найти тег."""
    pass


class NoVersionsFoundError(Exception):
    """Вызывается, когда не удается найти список всех версий."""
    pass
