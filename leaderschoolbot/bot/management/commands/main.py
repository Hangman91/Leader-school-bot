import re
import datetime

from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import User, Message

from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, Filters, MessageHandler, Updater, CommandHandler
from telegram.utils.request import Request


def save_user_and_messages(func):
    """Декоратор, позволяющий сохранять в базу пользователей и их сообщения"""

    def wrapper(update, context):

        chat_id = update.message.chat_id
        text = update.message.text
        name = update.message.from_user.name
        first_name = update.message.from_user.first_name
        last_name = update.message.from_user.last_name
        p, _ = User.objects.get_or_create(
            external_id=chat_id,
            defaults={
                'name': name,
                'first_last_name': first_name + ' ' + last_name,
                'access_level': 'User',
            }
        )

        m = Message(
            user=p,
            text=text,
        )
        m.save()

        return func(update, context)
    return wrapper


def check_admin(func):
    """Декоратор, отсекающий неадминов"""

    def wrapper(update, context):
        chat = update.effective_chat

        field_name = 'access_level'
        obj = User.objects.filter(external_id=chat.id)[0]
        field_value = getattr(obj, field_name)
        if field_value != 'Admin':
            context.bot.send_message(
                chat_id=chat.id,
                text='У тебя нет прав писать сюда'
                )
            return
        return func(update, context)
    return wrapper

@check_admin
def admin(update, context):
    chat = update.effective_chat

    # field_name = 'access_level'
    # obj = User.objects.filter(external_id=chat.id)[0]
    # field_value = getattr(obj, field_name)

    buttons = ReplyKeyboardMarkup(
        [['/statistic', '/massmail'],],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text='Добро пожаловать в админское меню',
        reply_markup=buttons
        )


@check_admin
def statistic(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['/day', '/week', '/all_time'],],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text='За какой период?',
        reply_markup=buttons
        )


@check_admin
def statistic_day(update, context):
    chat = update.effective_chat
    now = datetime.datetime.now()
    yesterday = now - datetime.timedelta(days=1)
    objs = Message.objects.filter(created_at__range=(yesterday,now)).all()
    count_message = objs.count()
    users = []
    for obj in objs:
        users.append(getattr(obj, 'user_id'))
    count_users = len(set(users))
    context.bot.send_message(
        chat_id=chat.id,
        text=f'За сутки было {count_message} сообщений от {count_users} пользователей',
        )


@check_admin
def statistic_week(update, context):
    chat = update.effective_chat
    now = datetime.datetime.now()
    week_ago = now - datetime.timedelta(days=7)
    objs = Message.objects.filter(created_at__range=(week_ago,now)).all()
    count_message = objs.count()
    users = []
    for obj in objs:
        users.append(getattr(obj, 'user_id'))
    count_users = len(set(users))
    context.bot.send_message(
        chat_id=chat.id,
        text=f'За неделю было {count_message} сообщений от {count_users} пользователей',
        )


@check_admin
def statistic_all_time(update, context):
    chat = update.effective_chat
    now = datetime.datetime.now()
    objs = Message.objects.all()
    count_message = objs.count()
    users = []
    for obj in objs:
        users.append(getattr(obj, 'user_id'))
    count_users = len(set(users))
    context.bot.send_message(
        chat_id=chat.id,
        text=f'За всё время было {count_message} сообщений от {count_users} пользователей',
        )

@save_user_and_messages
def do_echo(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text

    reply_text = "Ваш ID = {}\n\n{}".format(chat_id, text)
    update.message.reply_text(
        text=reply_text
    )


@save_user_and_messages
def call_operator(update, context):
    chat = update.effective_chat
    button = ReplyKeyboardMarkup(
        [['/start']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text='https://t.me/Mining_university_official',
        reply_markup=button
        )


@save_user_and_messages
def wake_up(update, context):
    chat = update.effective_chat
    name = update.message.chat.first_name
    buttons = ReplyKeyboardMarkup(
        [['Хочу узнать про поступление', 'Хочу узнать про общежития'],
         ['Конкурс "Лидер школы"', 'Не нашел ответа. Позвать оператора']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Приёмная комиссия Горного университета ' +
            'приветствует Вас, {}!'.format(name)
            ),
        reply_markup=buttons
        )


dict = {
    r'оператор':
        call_operator,
    r'здравствуйте|сначала|привет|начало':
        wake_up,
    r'админ':
        admin,
    }

dict_admin = {
    r'statistic':
        statistic,
    r'day':
        statistic_day,
    r'week':
        statistic_week,
    r'all_time':
        statistic_all_time, 
    }


class Command(BaseCommand):
    help = 'Телеграм-бот'

    def handle(self, *args, **options):
        request = Request()
        bot = Bot(
            request=request,
            token=settings.TOKEN,
        )
        print(bot.get_me())

        updater = Updater(
            bot=bot,
            use_context=True)

        for a in dict:
            updater.dispatcher.add_handler(
                MessageHandler(
                    Filters.regex(
                        re.compile(a, re.IGNORECASE)),
                        dict[a]
                    )
                )


        for command in dict_admin:
            updater.dispatcher.add_handler(
                CommandHandler(command, dict_admin[command])
                    )

 #       updater.dispatcher.add_handler(CommandHandler("statistic", statistic))

        message_handler = MessageHandler(Filters.text, do_echo)

        updater.dispatcher.add_handler(message_handler)

        updater.start_polling()
        updater.idle()
