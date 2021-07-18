from .db_interface import Session, LongSession


class CookieDispenser:

    ses_len = Session.length
    remember_len = LongSession.length

    @classmethod
    def safe_cookie(cls, cookie_params):
        safe_params = {'secure': True, 'http_only': True, 'same_site': 'Strict'}
        cookie_params.update(safe_params)
        return cookie_params

    @classmethod
    def session_cookie(cls, sid, max_age = None):
        return cls.safe_cookie({'name': 'SESSIONID', 'value': sid,
                                'max_age': max_age or cls.ses_len})

    @classmethod
    def extract_session(cls, cookies):
        try:
            return cookies['SESSIONID']
        except KeyError:
            return None

    @classmethod
    def l_session_cookie(cls, selector, validator, max_age = None):
        return cls.safe_cookie({'name': 'REMEMBER',
                                'value': f'{selector}:{validator}',
                                'max_age': max_age or cls.remember_len})

    @classmethod
    def extract_l_session(cls, cookies):
        try:
            return cookies['REMEMBER'].split(':')
        except KeyError:
            return None
