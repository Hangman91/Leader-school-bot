import re

from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import User, Message

from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, Filters, MessageHandler, Updater
from telegram.utils.request import Request


def save_user_and_messages(func):
    """Декоратор, позволяющий сохранять в базу пользователей и их сообщения"""

    def wrapper(update, contex):

        chat_id = update.message.chat_id
        text = update.message.text

        p, _ = User.objects.get_or_create(
            external_id=chat_id,
            defaults={
                'name': update.message.from_user.name,
                'first_last_name': update.message.from_user.first_name + ' ' + update.message.from_user.last_name
            }
        )

        m = Message(
            user=p,
            text=text,
        )

        m.save()   

        return func(update, contex)
    return wrapper


@save_user_and_messages
def do_echo(update: Update, contex: CallbackContext):
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

        message_handler = MessageHandler(Filters.text, do_echo)

        updater.dispatcher.add_handler(message_handler)

        updater.start_polling()
        updater.idle()
