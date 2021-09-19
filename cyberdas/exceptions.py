from falcon.http_error import HTTPError


class SessionError(Exception):
    pass


class NoSessionError(SessionError):
    pass


class BadAuthError(SessionError):
    pass


class HTTPNotEnoughPersonalData(HTTPError):
    def __init__(self, fields: list = [], headers=None, **kwargs):
        super().__init__(
            '442 Not Enough Personal Data',
            description=','.join(fields),
            headers=headers,
            **kwargs
        )
