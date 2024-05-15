import re
import datetime

from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import User, Message

from telegram import Bot, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, Filters, MessageHandler, Updater, CommandHandler, ConversationHandler
from telegram.utils.request import Request

MAIL, CHECK_MAIL = range(2)

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
        [['/day', '/week', '/all_time'],
         ['/admin']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text='За какой период?',
        reply_markup=buttons
        )


@check_admin
def statistic_time(update, context):
    chat = update.effective_chat
    text = update.message.text
    dict_time = {
        "/day": "день",
        "/week": "неделю",
        "/all_time": "всё время",
    }
    now = datetime.datetime.now()
    yesterday = now - datetime.timedelta(days=1)
    week_ago = now - datetime.timedelta(days=7)
    if text == "/day":
        objs = Message.objects.filter(created_at__range=(yesterday, now)).all()
    elif text == "/week":
        objs = Message.objects.filter(created_at__range=(week_ago, now)).all()
    else:
        objs = Message.objects.all()
    count_message = objs.count()
    users = []
    for obj in objs:
        users.append(getattr(obj, 'user_id'))
    count_users = len(set(users))
    context.bot.send_message(
        chat_id=chat.id,
        text=f'За {dict_time[text]} было {count_message} сообщений от {count_users} пользователей',
        )


def massmail(update, context):
    update.message.reply_text(
        'Введите сообщение',
        reply_markup=ReplyKeyboardRemove()
    )
    return MAIL


def mail_handler(update, context):
    mail_data = update.message.text
    chat = update.effective_chat
    context.bot.send_message(
        chat_id=chat.id,
        text=mail_data,
        )
    update.message.reply_text(
        'Сообщение действительно таково?',
        reply_markup=ReplyKeyboardRemove()
    )
    return CHECK_MAIL


def check_mail_handler(update, context):
    pass

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
    }

dict_admin = {
    r'admin':
        admin,
    r'statistic':
        statistic,
    r'day':
        statistic_time,
    r'week':
        statistic_time,
    r'all_time':
        statistic_time,
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


        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('massmail', massmail),
            ],
            states={
                MAIL: [
                    MessageHandler(Filters.all, mail_handler, pass_user_data=True),
                ],
                CHECK_MAIL: [
                    MessageHandler(Filters.all, check_mail_handler, pass_user_data=True),
                ],
                # ARE_YOU_SHURE:
                # ARE_YOU_SHURE2:
            },
            fallbacks=[
                CommandHandler('cancel', admin),
            ]
        )
        updater.dispatcher.add_handler(conv_handler)
        message_handler = MessageHandler(Filters.text, do_echo)

        updater.dispatcher.add_handler(message_handler)

        updater.start_polling()
        updater.idle()
