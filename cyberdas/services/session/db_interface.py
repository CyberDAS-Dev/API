from datetime import datetime, timedelta

import cyberdas.models.session
import cyberdas.models.long_session
from cyberdas.config import get_cfg
from cyberdas.exceptions import NoSessionError, SecurityError

cfg = get_cfg()


class AbstractSession:

    classname = None
    length = 0

    @classmethod
    def filter(cls, **ids):
        raise NotImplementedError

    @classmethod
    def find(cls, db, **ids):
        session = db.query(cls.classname).filter_by(**cls.filter(**ids))
        return session

    @classmethod
    def get(cls, db, **ids):
        ses = cls.find(db, **ids).first()
        if (ses is not None):
            return ses
        else:
            raise NoSessionError

    @classmethod
    def new(cls, db, **kwargs):
        new_object = cls.classname(
            expires = datetime.now() + timedelta(seconds = cls.length),
            **kwargs
        )
        db.add(new_object)

    @classmethod
    def prolong(cls, db, **ids):
        session = cls.find(db, **ids)
        if session is None:
            raise NoSessionError
        session.update({cls.classname.expires: datetime.now() + timedelta(seconds = cls.length)}) # noqa
        return cls.length

    @classmethod
    def terminate(cls, db, **ids):
        session = cls.get(db, **ids)
        db.delete(session)


class Session(AbstractSession):

    classname = cyberdas.models.session.Session
    length = int(cfg['internal']['session.length'])

    @classmethod
    def filter(cls, **ids):
        return {'sid': ids['sid']}


class LongSession(AbstractSession):

    classname = cyberdas.models.long_session.LongSession
    length = int(cfg['internal']['remember.length']) * 3600

    @classmethod
    def filter(cls, **ids):
        if 'validator' in ids:
            return {'selector': ids['selector'], 'validator': ids['validator']}
        else:
            return {'selector': ids['selector']}

    @classmethod
    def get(cls, db, **ids):
        try:
            ses = super().get(db, **ids)
        except NoSessionError:
            validator = ids.pop('validator')
            series = cls.find(db, **ids).first()
            if series is not None:
                raise SecurityError(f'[УКРАДЕННЫЙ ТОКЕН] {ids["selector"]}:{validator}') # noqa

        return ses

    @classmethod
    def change(cls, db, new_validator, new_association, **ids):
        # TODO: некрасивый метод, переписать
        old = cls.find(db, **ids)
        old.update({cls.classname.validator: new_validator,
                    cls.classname.associated_sid: new_association})
