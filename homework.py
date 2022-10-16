import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exception import (APIResponseIsIncorrect, APIResponseIsNotDict,
                       EndPointIsNotAccesed, HomeworkValueIncorrect,
                       NoStatusInResponse, WrongHTTPStatusCode)

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
    stream=sys.stdout
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
    logger.info('Бот начинает отправку сообщения')
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
    logger.info('Бот начинает подключение к API')
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.exceptions.RequestException as error:
        message = f'Сбой при запросе к эндпоинту: {error}'
        raise EndPointIsNotAccesed(message)
    status_code = response.status_code
    if status_code != HTTPStatus.OK:
        message = f'API недоступен, код ошибки: {status_code}'
        raise WrongHTTPStatusCode(message)

    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        message = f'Ответ пришел в некорректном формате: {response}'
        raise APIResponseIsNotDict(message)
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        message = 'В ответе отсутствуют ключи'
        raise APIResponseIsIncorrect(message)
    if 'current_date' not in response:
        message = 'В ответе отсутствуют ключи'
        raise APIResponseIsIncorrect(message)
    if not isinstance(homeworks, list):
        message = 'Неправильное значение домашней работы'
        raise HomeworkValueIncorrect(message)

    return homeworks


def parse_status(homeworks):
    """Проверяет статус проверки домашки."""
    homework_name = homeworks.get('homework_name')
    homework_status = homeworks.get('status')
    if homework_name is None:
        message = 'Отсутствует имя домашней работы'
        raise KeyError(message)
    if homework_status is None:
        message = 'Отсутствует статус'
        raise KeyError(message)
    if homework_status not in HOMEWORK_STATUSES:
        message = ('недокументированный статус домашней работы ,'
                   'обнаруженный в ответе API')
        raise NoStatusInResponse(message)
    verdict = HOMEWORK_STATUSES.get(homework_status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствуют важные переменные!'
        logger.critical(message)
        sys.exit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
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
