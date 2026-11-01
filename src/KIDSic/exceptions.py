"""Stable errors at the external-source and persistence boundaries."""


class KIDSicError(RuntimeError):
    code = 'error'


class CkanError(KIDSicError):
    code = 'ckan_error'


class CkanTransportError(CkanError):
    """The request failed, including timeouts."""


class CkanHttpError(CkanError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f'CKAN returned HTTP {status_code}.')


class CkanApiError(CkanError):
    """The action returned success=false, possibly with HTTP 200."""


class CkanResponseError(CkanError):
    """The response does not satisfy the expected contract."""


class SourceImportError(KIDSicError):
    code = 'source_import_error'


class PersistenceError(KIDSicError):
    code = 'persistence_error'
