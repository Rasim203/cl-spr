"""Telegram Bot on Yandex Cloud Function."""
import os
import json
import requests

# Этот словарь будем возвращать, как результат функции.
FUNC_RESPONSE = {
    'statusCode': 200,
    'body': ''
}
# Из переменной окружения с именем "TELEGRAM_BOT_TOKEN" получаем токен бота.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# Базовая часть URL для доступа к Telegram Bot API.
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(text, message):
    """Отправка сообщения пользователю Telegram."""

    # Формируем данные для метода sendMessage из Telegram Bot API
    message_id = message['message_id']
    chat_id = message['chat']['id']
    reply_message = {'chat_id': chat_id,
                     'text': text,
                     'reply_to_message_id': message_id}

    # POST запросом отправим данные на сервер Telegram Bot API
    # Объект будет преобразован в JSON и отправиться как тело HTTP запроса.
    requests.post(url=f'{TELEGRAM_API_URL}/sendMessage', json=reply_message)


def handler(event, context):
    """Обработчик облачной функции. Реализует Webhook для Telegram Bot."""

    # Наличие токена Telegram Bot обязательно, поэтому если он не
    # определен среди переменных окружения, то завершим облачную функцию с
    # кодом 200, что бы сервер Telegram Bot API повторно не отправлял на
    # обработку это сообщение.
    if TELEGRAM_BOT_TOKEN is None:
        return FUNC_RESPONSE

    # Среда выполнения в аргументе event передает данные об HTTP запросе
    # преобразованные в словарь. В этом словаре по ключу body содержится тело
    # HTTP запроса. Сервер Telegram Bot API при использовании Webhook передает
    # в теле HTTP запроса объект Update в JSON формате. Мы этот объект
    # преобразуем в словарь.
    update = json.loads(event['body'])

    # В объекте Update должно быть поле message содержащее объект Message
    # (сообщение пользователя). Если его нет, то завершим облачную функцию с
    # кодом 200, что бы сервер Telegram Bot API повторно не отправлял на
    # обработку это сообщение.
    if 'message' not in update:
        return FUNC_RESPONSE

    # Если поле message присутствует, то извлекаем объект Message.
    message_in = update['message']

    # Так как обрабатываем только текстовые сообщения, поэтому проверяем есть ли
    # поле text в полученном сообщении. Если текстового сообщения нет, то
    # отправим пользователю предупреждение и завершим облачную функцию с кодом
    # 200, что бы сервер Telegram Bot API повторно не отправлял на обработку это
    # сообщение.
    if 'text' not in message_in:
        send_message('Могу обработать только текстовое сообщение!', message_in)
        return FUNC_RESPONSE

    # Выделяем текст и преобразуем регистр.
    echo_text = message_in['text'].upper()

    # Отправляем преобразованный текст пользователю.
    send_message(echo_text, message_in)

    # Завершим облачную функцию с кодом 200, чтобы сервер Telegram Bot
    # API повторно не отправлял на обработку это сообщение.
    return FUNC_RESPONSE
