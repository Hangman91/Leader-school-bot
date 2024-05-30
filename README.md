Тут будет проект с телеграмм-ботом, который будет консультировать по конкурсу Лидер школы. 

Планируемый стэк:
Python, Django, PostgreSQL, Telegram-python-bot, Docker, Docker-compose


На моменте [коммита от 29.05.2024](https://github.com/Hangman91/Leader-school-bot/commit/d7dd83f010c31789311fe0d7d8e94ca395a57cdb) настроен докер, докер компоуз. Но в ночь на 30.05 докер покинул нашу страну, так что дальше всё возвращаю к настройкам напрямую не сервере. 


Для локального запуска:

Cоздать и активировать виртуальное окружение:

```
python -m venv venv
```

```
source venv/Scripts/activate
```

```
python -m pip install --upgrade pip
```

Установить зависимости из файла requirements.txt:

```
pip install -r ./requirements.txt
```