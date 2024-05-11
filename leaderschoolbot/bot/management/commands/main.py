from django.core.management.base import BaseCommand
from django.conf import settings

from telegram import Bot, Update
#from telegram.ext import CallbackContext, Filters, MessageHandler, Updater
from telegram.utils.request import Request


class Command(BaseCommand):
    help = 'Телеграм-бот'

    def handle(self, *args, **options):
        request = Request()
        bot = Bot(
            request=request,
            token=settings.TOKEN,
        )
        print(bot.get_me())
