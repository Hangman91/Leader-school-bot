Проект с телеграмм-ботом, который консультирует потенциальных абитуриентов по конкурсу Лидер школы и поступлению.



Боевая версия админки располагается по адресу priembot.spmi.ru/admin

Стэк проекта:
Python, Django, PostgreSQL, Telegram-python-bot, Docker, Docker-compose

Админка реализована на Django. 
База данных PostrgeSQL.

Описаны модели для сохранения данных пользователей и их сообщений.

Возможно три категории пользователей: 
1. Пользователь
2. Оператор
3. Админ

Пользователь -- любой юзер, который написал боту сообщение. 
Оператор -- юзер, который получает запрос на перезвон. 
Функционал бота позволяет запрашивать звонок от оператора. 

![Запрос звонка](https://sun9-16.userapi.com/impg/Rz_zg1bvkCasW-LS4TX4wK2LgV0ouKt9h4IUBw/7lY7eaCWUWg.jpg?size=580x286&quality=96&sign=d77acec6ca61846138dd1e10d7f5476c&type=album)

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


Команды для докера: 
docker build -t astalavista91/leaderbot:latest .

docker push astalavista91/leaderbot:latest