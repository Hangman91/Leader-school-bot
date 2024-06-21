# Описание
Проект с телеграмм-ботом, который консультирует потенциальных абитуриентов по конкурсу Лидер школы и поступлению.

# Где посмотреть?
К боту можно обратиться по ссылке: https://t.me/priem_leader_school_2024_bot  
Боевая версия админки располагается по адресу priembot.spmi.ru/admin

# Стэк проекта
Python
Django
PostgreSQL
Telegram-python-bot
Docker
Docker-compose

# Описание проекта и возможности
Описаны модели для сохранения данных пользователей и их сообщений.

Возможно три категории пользователей: 
1. Пользователь
2. Оператор
3. Админ

**Пользователь** -- любой юзер, который написал боту сообщение. 
**Оператор** -- юзер, который получает запрос на перезвон. 
Функционал бота позволяет запрашивать звонок от оператора. 

![Запрос звонка](https://sun9-16.userapi.com/impg/Rz_zg1bvkCasW-LS4TX4wK2LgV0ouKt9h4IUBw/7lY7eaCWUWg.jpg?size=580x286&quality=96&sign=d77acec6ca61846138dd1e10d7f5476c&type=album)

**Админ** - пользователь, которому доступны команды админки */admin*.  
Они включат в себя статистику */statistic* за разные периоды и средства для массированной рассылки.  
*/massmail* позволяет отправлять сообщения всем пользователям, кто когда-либо писал боту. 

На моменте [коммита от 29.05.2024](https://github.com/Hangman91/Leader-school-bot/commit/d7dd83f010c31789311fe0d7d8e94ca395a57cdb) настроен докер, докер компоуз. Но в ночь на 30.05 докер покинул нашу страну, так что дальше всё возвращаю к настройкам напрямую не сервере. 

# Запуск на сервере

При запуске создаются три контейнера. 

1. База данных
2. Админка
3. Непосредственно сам бот

В файле .env должны быть прописаны следующие переменные:
**TOKEN** - Токен для работы с ботом
**SECRET_KEY** - Ключ для работы с Джанго
Параметры для работы с базой данных:
**DB_ENGINE**
**DB_NAME**
**POSTGRES_USER**
**POSTGRES_PASSWORD**
**DB_HOST**
**DB_PORT**

Команды для докера: 
docker build -t astalavista91/leaderbot:latest .

docker push astalavista91/leaderbot:latest