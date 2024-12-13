import os
import json
import requests
from datetime import datetime, timedelta
import io

# Словарь с ответом
FUNC_RESPONSE = {
    'statusCode': 200,
    'body': ''
}

# Из переменной окружения с именем "TELEGRAM_BOT_TOKEN
# " получаем токен бота.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Базовая часть URL для доступа к Telegram Bot API.
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# URL и API ключ для получения погоды (пример для OpenWeatherMap)
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"
WEATHER_API_KEY = "1842cdd9bab02f8ab0dda32c29ee498c"

# Yandex speechkit
YANDEX_SPEECH_KIT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
YANDEX_API_KEY = "AQVN009FWgxM5dU_xz3MVhJ_LIhd9nFj7XRhtVsG"
YC_TTS_API_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

# Константы 
start_help_command_response = """
Я расскажу о текущей погоде для населенного пункта.

Я могу ответить на:
- Текстовое сообщение с названием населенного пункта.
- Голосовое сообщение с названием населенного пункта.
- Сообщение с геопозицией.
"""

# Основная функция
def handler(event, context):

    # Если токен отсутствует, то возвращаем None, чтобы телеграм не делал повторные запросы.
    if TELEGRAM_BOT_TOKEN is None:
        return FUNC_RESPONSE

    update = json.loads(event['body'])

    # Если message отсутствует, то возвращаем None, чтобы телеграм не делал повторные запросы.
    if 'message' not in update:
        return FUNC_RESPONSE

    message_in = update['message']

    # Обработка текстовых сообщений
    if 'text' in message_in:
        text = message_in['text']
        if text == '/start' or text == '/help':
            send_message(start_help_command_response, message_in)
        else:
            weather_info = get_weather(text)
            print(weather_info)
            if weather_info:
                formatted_weather_info = format_weather_message(weather_info)
                send_message(formatted_weather_info, message_in)
            else:
                send_message("Я не нашел населенный пункт " + text, message_in)

    # Обработка голосовых сообщений
    if 'voice' in message_in:
        voice = message_in['voice']

        if voice["duration"] > 30:
            send_message("Я не могу обработать сообщение длиннее 30", message_in)
            return FUNC_RESPONSE
        
        token = context.token["access_token"]
        
        yc_auth = {"Authorization": f'Bearer {token}'}

        yc_stt_resp = speech_recognize(voice, yc_auth, message_in)

        if not yc_stt_resp:
            return FUNC_RESPONSE

        if 'result' in yc_stt_resp:
            city_name = yc_stt_resp['result']
            weather_info = get_weather(city_name)
            if weather_info:
                formatted_weather_info = format_voice_weather_message(weather_info)
                yc_tts_resp = speech_synthesis(formatted_weather_info, yc_auth, message_in)
                if not yc_tts_resp:
                    return FUNC_RESPONSE
                yc_tts_voice = yc_tts_resp.content
                send_voice(yc_tts_voice, message_in)
            else:
                send_message(f'Я не нашел населенный пункт "{city_name}".', message_in)
        else:
            send_message("Не удалось распознать голосовое сообщение", message_in)
    
    # Обработка геолокации
    if 'location' in message_in:
        location = message_in['location']
        g_params = {
            'lat': location['latitude'], 
            'lon': location['longitude'],
            'appid': WEATHER_API_KEY,
            'units': 'metric',
            'lang': 'ru'
        }
        g_r = requests.get(url=WEATHER_API_URL, params=g_params).json()
        if g_r:
            formatted_weather_info = format_weather_message(g_r)
            send_message(formatted_weather_info, message_in)
        else:
            send_message("Не удалось получить данные о погоде.", message_in)

    return FUNC_RESPONSE

# Отправка погоды текстом
def send_message(text, message):
    message_id = message['message_id']
    chat_id = message['chat']['id']
    reply_message = {'chat_id': chat_id,
                     'text': text,
                     'reply_to_message_id': message_id}
    requests.post(url=f'{TELEGRAM_API_URL}/sendMessage', json=reply_message)

# Отправка погоды голосовым сообщением
def send_voice(voice, message):
    message_id = message['message_id']
    chat_id = message['chat']['id']
    voice_file = {"voice" : io.BytesIO(voice)}
    params = {'chat_id': chat_id,
              'reply_to_message_id': message_id}
    requests.post(url=f'{TELEGRAM_API_URL}/sendVoice', params=params, files=voice_file)

# Распознование речи
def speech_recognize(voice, yc_auth, message_in):
    voice_file_id = voice["file_id"]

    tg_file_response = requests.post(url=f'{TELEGRAM_API_URL}/getFile', params={"file_id": voice_file_id}).json()

    if "result" not in tg_file_response:
        send_message("Не удалось получить голосовое сообщение", message_in)
        return None

    voice_file = tg_file_response["result"]

    voice_file_path = voice_file["file_path"]

    TG_BOT_API_FILE = f'https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{voice_file_path}'

    voice_content = requests.get(url=TG_BOT_API_FILE).content

    yc_stt_resp = requests.post(url=YANDEX_SPEECH_KIT_URL, headers=yc_auth, data=voice_content).json()

    return yc_stt_resp


# Синтез речи
def speech_synthesis(weather_info, yc_auth, message_in):
    yc_tts_params = {
        "text": weather_info,
        "voice": "alena",
        "emotion": "good"
    }
    yc_tts_resp = requests.post(url=YC_TTS_API_URL, data=yc_tts_params, headers=yc_auth)
    if not yc_tts_resp.ok:
        print(yc_tts_resp)
        send_message("Не удалось синтезировать голосовое сообщение", message_in)
        return None
    return yc_tts_resp

# Функция для получения погоды
def get_weather(city_name):
    params = {
        'q': city_name,
        'appid': WEATHER_API_KEY,
        'units': 'metric',
        'lang': 'ru'
    }
    response = requests.get(WEATHER_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None
    
# Форматирование карточки с данными о погоде
def format_weather_message(weather_info):
    city = weather_info['name']
    description = weather_info['weather'][0]['description']
    icon = weather_info['weather'][0]['icon']
    temp = weather_info['main']['temp']
    feels_like = weather_info['main']['feels_like']
    pressure = weather_info['main']['pressure'] * 0.75006
    humidity = weather_info['main']['humidity']
    visibility = weather_info['visibility']
    wind_speed = weather_info['wind']['speed']
    sunrise = (datetime.fromtimestamp(weather_info['sys']['sunrise']) + timedelta(hours = 3)).strftime('%H:%M') # UTC + 3
    sunset = (datetime.fromtimestamp(weather_info['sys']['sunset']) + timedelta(hours = 3)).strftime('%H:%M') # UTC + 3
    wind_direction = get_wind_direction(weather_info['wind']['deg'])
    return (f"Погода в {city}:\n"
            f"{description}\n"
            f"Температура: {temp}°C, ощущается как {feels_like}°C\n"
            f"Атмосферное давление : {pressure:.0f} мм рт. ст.\n"
            f"Влажность: {humidity}%\n"
            f"Видимость {visibility} метров\n"
            f"Скорость ветра: {wind_speed} м/с {wind_direction}\n"
            f"Восход солнца {sunrise} МСК. Закат {sunset} МСК.")

# Функция рассчета направления ветра
def get_wind_direction(deg):
    directions = ['С', 'СВ', 'В', 'ЮВ', 'Ю', 'ЮЗ', 'З', 'СЗ']
    idx = round(deg / 45) % 8
    return directions[idx]

# Форматирование голосового ответа
def format_voice_weather_message(weather_info):
    city = weather_info['name']
    description = weather_info['weather'][0]['description']
    icon = weather_info['weather'][0]['icon']
    temp = weather_info['main']['temp']
    feels_like = weather_info['main']['feels_like']
    pressure = weather_info['main']['pressure'] * 0.75006
    humidity = weather_info['main']['humidity']
    sunrise = (datetime.fromtimestamp(weather_info['sys']['sunrise']) + timedelta(hours = 3)).strftime('%H:%M') # UTC + 3
    sunset = (datetime.fromtimestamp(weather_info['sys']['sunset']) + timedelta(hours = 3)).strftime('%H:%M') # UTC + 3
    return (f"Населенный пункт {city}.\n"
            f"{description}.\n"
            f"Температура {temp:.0f} градусов цельсия.\n"
            f"Ощущается как {feels_like:.0f} градусов цельсия.\n"
            f"Атмосферное давление: {pressure:.0f} миллиметров ртутного столба.\n"
            f"Влажность: {humidity} процентов.\n"
            f"Восход солнца {sunrise} по МСК. Закат {sunset} по МСК.")
