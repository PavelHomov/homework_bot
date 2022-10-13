class VariableNotExists(Exception):
    """Отсутствует обязательная переменная."""


class WrongHTTPStatusCode(Exception):
    """Ответ не равен 200."""


class APIResponseIsNotDict(Exception):
    """Ответ не является списком."""


class APIResponseIsIncorrect(Exception):
    """Некорректное содержание ответа."""


class HomeworkValueIncorrect(Exception):
    """Неправильное значение домашней работы."""


class NoStatusInResponse(Exception):
    """Некорректный статус проверки задания."""


class EndPointIsNotAccesed(Exception):
    """Неизвестная ошибка при запросе к эндпоинту."""
