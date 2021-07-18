class SessionError(Exception):
    pass


class NoSessionError(SessionError):
    pass


class BadAuthError(SessionError):
    pass


class SecurityError(Exception):
    pass
