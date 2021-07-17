from zxcvbn import zxcvbn


class PassChecker:

    def check(self, passw, user_inputs):
        '''
        Проверяет сложность пароля и возвращает список рекомендаций, если пароль
        слабый.
        '''
        results = zxcvbn(passw, user_inputs)
        if results['score'] < 3:
            return results['feedback']['suggestions']
        else:
            return []
