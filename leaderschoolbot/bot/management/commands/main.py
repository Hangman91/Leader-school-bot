import re
import time
import datetime

from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import User, Message, Call

from telegram import Bot, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, ParseMode
from telegram.ext import CallbackContext, Filters, MessageHandler, Updater, CommandHandler, ConversationHandler
from telegram.utils.request import Request

PHOTO, MAIL, CHECK_MAIL, ARE_YOU_SHURE, ARE_YOU_SHURE2 = range(5)
SAVE_REQUEST, CANCEL = range(2)


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
                'first_last_name': str(first_name) + ' ' + str(last_name),
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


@check_admin
def massmail(update, context):
    buttons = ReplyKeyboardMarkup(
        [['/cancel'],],
        resize_keyboard=True
        )
    update.message.reply_text(
        'Введите сообщение',
        reply_markup=buttons
    )
    context.user_data["SKIP"] = False
    return MAIL


@check_admin
def mail_handler(update, context):
    text_mail = update.message.text_markdown
    context.user_data["MAIL"] = text_mail
    buttons = ReplyKeyboardMarkup(
        [['/skip'], ['/cancel']],
        resize_keyboard=True
        )
    update.message.reply_text(
        'Прикрепите картинку',
        reply_markup=buttons
    )
    return PHOTO


@check_admin
def photo_handler(update, context):
    chat = update.effective_chat
    text_mail = context.user_data["MAIL"]
    file_id = update.message.photo[-1].file_id
    newFile = context.bot.get_file(file_id)
    context.user_data["PHOTO"] = newFile['file_id']
    context.bot.send_photo(
            chat_id=chat.id,
            photo=context.user_data["PHOTO"],
            caption=text_mail,
            parse_mode="MARKDOWN"
            )
    buttons = ReplyKeyboardMarkup(
        [['Да, я проверил', 'Нет, нашел ошибку'],
         ['/cancel']],
        resize_keyboard=True
        )
    update.message.reply_text(
        'Сообщение действительно таково?',
        reply_markup=buttons
    )
    return CHECK_MAIL


@check_admin
def skip_photo(update, context):
    chat = update.effective_chat
    text_mail = context.user_data["MAIL"]
    context.bot.send_message(
            chat_id=chat.id,
            text=text_mail,
            parse_mode="MARKDOWN"
            )
    buttons = ReplyKeyboardMarkup(
        [['Да, я проверил', 'Нет, нашел ошибку'],
         ['/cancel']],
        resize_keyboard=True
        )
    update.message.reply_text(
        'Сообщение действительно таково?',
        reply_markup=buttons
    )
    context.user_data["SKIP"] = True
    return CHECK_MAIL


@check_admin
def check_mail_handler(update, context):
    if update.message.text == 'Да, я проверил':
        buttons = ReplyKeyboardMarkup(
            [['Да', 'Нет'],],
            resize_keyboard=True
            )
        update.message.reply_text(
            'Ты уверен в массовом спаме?',
            reply_markup=buttons
        )
        return ARE_YOU_SHURE
    else:
        update.message.reply_text(
            'Давай заново',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


@check_admin
def are_you_shure_handler(update, context):
    if update.message.text == 'Да':
        buttons = ReplyKeyboardMarkup(
            [['/cancel']],
            resize_keyboard=True
            )
        update.message.reply_text(
            'Ты уверен в массовом спаме? Если да, то введи первое слово сообщения',
            reply_markup=buttons
        )
        return ARE_YOU_SHURE2
    else:
        update.message.reply_text(
            'Ок',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


@check_admin
def are_you_shure2_handler(update, context):
    text_mail = context.user_data["MAIL"]

    first_word = text_mail.split()[0]
    chat = update.effective_chat
    if update.message.text == first_word:
        update.message.reply_text(
            'Отправка пошла',
            reply_markup=ReplyKeyboardRemove()
        )
        list_of_massmail = User.objects.all()
        successfully_count = 0
        banned_count = 0

        for victim in list_of_massmail:
            victim_id = getattr(victim, 'external_id')
            try:
                if not context.user_data["SKIP"]:
                    photo = context.user_data["PHOTO"]
                    context.bot.send_photo(
                        chat_id=victim_id,
                        photo=photo,
                        caption=text_mail,
                        parse_mode="MARKDOWN"
                        )
                else:
                    context.bot.send_message(
                        chat_id=victim_id,
                        text=text_mail,
                        parse_mode="MARKDOWN"
                        )
                successfully_count += 1
                time.sleep(1)
            except BaseException:
                banned_count += 1
        context.bot.send_message(
            chat_id=chat.id,
            text=f'Успешно отправлено {successfully_count} сообщений, ошибок {banned_count}',
            )
        return ConversationHandler.END
    else:
        update.message.reply_text(
            'Неверно, попробуй ещё раз',
            reply_markup=ReplyKeyboardRemove()
        )


@check_admin
def cancel(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['/statistic', '/massmail'],],
        resize_keyboard=True
        )
    context.bot.send_message(
            chat_id=chat.id,
            text='Отмена массмейла',
            reply_markup=buttons
            )
    return ConversationHandler.END


def cancel1(update, context):
    print(2)
    return ConversationHandler.END


@save_user_and_messages
def do_echo(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text_markdown

    reply_text = "Ваш ID = {}\n\n{}".format(chat_id, text)
    update.message.reply_text(
        text=reply_text,
        parse_mode="MARKDOWN"
    )


@save_user_and_messages
def call_operator(update, context):
    chat = update.effective_chat
    button = ReplyKeyboardMarkup(
        [['/start'],
         ['Запросить звонок']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text='Можете написать нашему оператору. https://t.me/Mining_university_official . Также можете запросить звонок оператора, мы свяжемся с Вами в ближайшее время',
        reply_markup=button
        )



@save_user_and_messages
def call_request(update, context):
    update.message.reply_text(
        'Пришлите одним сообщение номер телефона и как к Вам можно обращаться',
    )
    return SAVE_REQUEST

@save_user_and_messages
def save_call_request(update, context):
    chat_id = update.message.chat_id
    user = User.objects.get(external_id=chat_id)
    message = update.message.text
    call = Call(
       user=user,
       message=message,
    )
    call.save()

    list_operator_massmail = User.objects.filter(access_level__in=['Admin', 'Operator'])
    for operator_mail in list_operator_massmail:
        operator_massmail_id = getattr(operator_mail, 'external_id')
        text_mail = 'Новый запрос звонка! ' + message
        context.bot.send_message(
                        chat_id=operator_massmail_id,
                        text=text_mail,
                        parse_mode="MARKDOWN"
                        )
    update.message.reply_text(
        'Мы свяжемся с Вами в ближайшее время',
    )
    return ConversationHandler.END


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
    # r'запросить звонок':
    #     call_request,
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
                    CommandHandler('cancel', cancel),
                    MessageHandler(Filters.text, mail_handler),
                ],
                PHOTO: [
                    CommandHandler('skip', skip_photo),
                    MessageHandler(Filters.photo, photo_handler),
                ],
                CHECK_MAIL: [
                    CommandHandler('cancel', cancel),
                    MessageHandler(Filters.all, check_mail_handler),
                ],
                ARE_YOU_SHURE: [
                    MessageHandler(Filters.all, are_you_shure_handler),
                ],
                ARE_YOU_SHURE2: [
                    CommandHandler('cancel', cancel),
                    MessageHandler(Filters.all, are_you_shure2_handler),
                ],
            },
            fallbacks=[
                MessageHandler(Filters.all, cancel),
                CommandHandler('cancel', cancel),
            ]
        )

        conv_handler_call = ConversationHandler(
            entry_points=[
                MessageHandler(
                    Filters.regex(re.compile(r'Запросить звонок', re.IGNORECASE)), call_request
                ),
            ],
            states={
                SAVE_REQUEST: [
                    MessageHandler(Filters.text, save_call_request),
                    CommandHandler('cancel', cancel1),
                ],
            },
            fallbacks=[
                MessageHandler(Filters.all, cancel1),
                CommandHandler('cancel', cancel1),
            ]
        )
        
        updater.dispatcher.add_handler(conv_handler)
        updater.dispatcher.add_handler(conv_handler_call)

        message_handler = MessageHandler(Filters.text, do_echo)

        updater.dispatcher.add_handler(message_handler)

        updater.start_polling()
        updater.idle()
