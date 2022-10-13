import os
import logging
import time
from http import HTTPStatus
from sys import stdout

from dotenv import load_dotenv
from exception import (
    APIResponseIsNotDict,
    APIResponseIsIncorrect,
    EndPointIsNotAccesed,
    WrongHTTPStatusCode,
    HomeworkValueIncorrect,
    VariableNotExists,
    NoStatusInResponse,
)
import requests
import telegram


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s'
)
handler = logging.StreamHandler(
    stream=stdout
)
handler.setFormatter(formatter)
logger.addHandler(handler)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение с статусом обработки домашки."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.info(f'Сообщение {message} было отправлено')
    except Exception as error:
        logger.error(f'Ошибка при отправке {message} сообщения: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту Практикум.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.exceptions.RequestException as error:
        message = f'Сбой при запросе к эндпоинту: {error}'
        logger.error(message)
        raise EndPointIsNotAccesed(message)
    status_code = homework.status_code
    if status_code != HTTPStatus.OK:
        message = f'API недоступен, код ошибки: {status_code}'
        logger.error(message)
        raise WrongHTTPStatusCode(message)
    homework_json = homework.json()

    return homework_json


def check_response(response):
    """Проверяет ответ API на корректность."""
    if type(response) == list:
        response = response[0]
    if type(response) != dict:
        response_type = type(response)
        message = f'Ответ пришел в некорректном формате: {response_type}'
        logger.error(message)
        raise APIResponseIsNotDict(message)
    homework = response.get('homeworks')
    if type(homework) != list:
        message = 'Неправильное значение домашней работы'
        logger.error(message)
        raise HomeworkValueIncorrect(message)
    if 'current_date' and 'homeworks' not in response:
        message = 'В ответе отсутствуют ключи'
        logger.error(message)
        raise APIResponseIsIncorrect(message)

    return homework


def parse_status(homework):
    """Проверяет статус проверки домашки."""
    if homework.get('homework_name') is None:
        message = 'Отсутствует имя домашней работы'
        logger.error(message)
        raise KeyError(message)
    homework_name = homework.get('homework_name', 'Homework_no_name')
    if homework.get('status') not in HOMEWORK_STATUSES:
        message = ('недокументированный статус домашней работы ,'
                   'обнаруженный в ответе API')
        logger.error(message)
        raise NoStatusInResponse(message)
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens_bool = True
    is_exists = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in is_exists:
        if token is None:
            tokens_bool = False

    return tokens_bool


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствуют важные переменные!'
        logger.critical(message)
        raise VariableNotExists(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    send_message(bot, 'Бот начал работу')
    current_timestamp = int(time.time())
    last_error = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                send_message(bot, message)
            else:
                logger.debug('Отсутствие в ответе новых статусов')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != last_error:
                last_error = message
                send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
