import datetime


class Serializable:

    def as_dict(self):
        output = dict()
        for c in self.__table__.columns:
            data = getattr(self, c.name)
            if isinstance(data, datetime.datetime):
                data = data.isoformat('T')
            if isinstance(data, (datetime.date, datetime.time)):
                data = data.isoformat()
            output[c.name] = data
        return output
