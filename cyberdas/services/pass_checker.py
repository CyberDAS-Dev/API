import re


class PassChecker:

    def __init__(self):
        self.digit_re = re.compile(r"\d")
        self.upper_re = re.compile(r"[A-Z]")
        self.lower_re = re.compile(r"[a-z]")
        self.symbol_re = re.compile(r"\W")

    def check(self, passw):
        '''
        Проверяет сложность пароля и возвращает список с описанием критериев,
        не прошедших проверку.

        Пароль считается сложным, если имеет:
            - 8+ символов
            - 1+ заглавную букву
            - 1+ прописную букву
            - 1+ цифру
            - 1+ специальный символ
        '''
        length = (len(passw) > 8, '8 символов')
        digit = (self.digit_re.search(passw) is not None, '1 цифра')
        upper = (self.upper_re.search(passw) is not None, '1 заглавная буква')
        lower = (self.lower_re.search(passw) is not None, '1 прописная буква')
        symbol = (self.symbol_re.search(passw) is not None, '1 спецсимвол')

        failed = list()
        for criterion in [length, digit, upper, lower, symbol]:
            if criterion[0] is False:
                failed.append(criterion[1])

        return failed
