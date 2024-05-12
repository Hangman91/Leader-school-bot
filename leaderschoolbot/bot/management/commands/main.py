from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import User, Message

from telegram import Bot, Update
from telegram.ext import CallbackContext, Filters, MessageHandler, Updater
from telegram.utils.request import Request


def do_echo(update: Update, contex: CallbackContext):
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

    reply_text = "Ваш ID = {}\n\n{}".format(chat_id, text)
    update.message.reply_text(
        text=reply_text
    )


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

        message_handler = MessageHandler(Filters.text, do_echo)
        updater.dispatcher.add_handler(message_handler)

        updater.start_polling()
        updater.idle()
