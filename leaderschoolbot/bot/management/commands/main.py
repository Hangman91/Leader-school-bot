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
def leader_of_the_school(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['О конкурсе', 'Условия участия'],
         ['Пороговые баллы', 'Подать заявку'],
         ['Ссылка на ТГ-канал', 'Видеоотзывы студентов'],
         ['В начало']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=("Выберете интересующее Вас меню⁠"),
        reply_markup=buttons
        )


@save_user_and_messages
def about_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Цели и задачи конкурса', 'Бонусы "Гранта"'],
         ['Количество мест по гранту', 'Подать заявку'],
         ['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_photo(
        chat_id=chat.id,
        photo='https://leaderschool.spmi.ru/sites/default/files/2024-03/IMG_1522-1-0.jpg',
        caption=(
            '«Лидер школы России» – это программа, нацеленная на совершенствование ' +
            'системы среднего образования и призванная мотивировать талантливых ' +
            'старшеклассников выбирать при поступлении технические вузы. Ведь наша ' +
            'страна сегодня остро нуждается в молодых компетентных инженерах, способных ' +
            'обеспечить в перспективе безболезненную смену поколений на производстве. Кроме ' +
            'того, данный проект представляет собой один из механизмов интеграции средней и ' +
            'высшей школы, надёжный мост, связующий наше настоящее и будущее, а также повышающий ' +
            'устойчивость социально-экономического развития каждого из нас и всего общества в целом. \n' +
            '*Ректор Санкт-Петербургского горного университета императрицы Екатерины II В.С. Литвиненко*'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def mission_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Конкурс «Лидер школы» проводится с целью организации качественного ' +
            'приёма на обучение по специальностям Санкт-Петербургского горного университета ' +
            'в 2024 году. \n' +
            'Задачи конкурса направлены на: \n' +
            '-минимизацию рисков ошибочного выбора и поступления на образовательную программу, ' +
            'не соответствующую потребностям и ожиданиям поступающего; \n' +
            '-предоставление приоритетного гарантированного зачисления для поступающих; \n' +
            '-создание необходимых условий стимулирования и поддержки талантливой молодежи; \n' +
            '-предоставление особых конкурентных преимуществ для обучения в Университете для  ' +
            'выпускников образовательных организаций из регионов Российской Федерации. \n' +
            '[Сайт конкурса](https://leaderschool.spmi.ru/) \n' +
            '[Видеоролик о конкурсе](https://www.youtube.com/watch?v=kqjqvnK2ZDA) \n'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )

@save_user_and_messages
def places_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Автоматизация технологических процессов и производств – 65\n' +
            'Архитектура – 25\n' +
            'Горное дело – 295\n' +
            'Землеустройство и кадастры – 35\n' +
            'Информатика и вычислительная техника – 35\n' +
            'Информационные системы и технологии – 35\n' +
            'Материаловедение и технологии материалов – 25\n' +
            'Машиностроение – 20\n' +
            'Менеджмент – 35\n' +
            'Металлургия - 25\n' +
            'Наземные транспортно-технологические средства – 25\n' +
            'Нефтегазовые техника и технологии – 290\n' +
            'Приборостроение – 20\n' +
            'Прикладная геодезия – 40\n' +
            'Прикладная геология – 100\n' +
            'Радиоэлектронные системы и комплексы – 25\n' +
            'Системный анализ и управление – 25 \n' +
            'Стандартизация и метрология – 25\n' +
            'Строительство – 25\n' +
            'Строительство уникальных зданий и сооружений – 50\n' +
            'Теплоэнергетика и теплотехника – 25\n' +
            'Технологические машины и оборудование – 40\n' +
            'Технология геологической разведки – 40\n' +
            'Технология транспортных процессов – 15\n' +
            'Технология художественной обработки материалов – 25\n' +
            'Техносферная безопасность – 20\n' +
            'Управление в технических системах - 25\n' +
            'Химическая технология – 60\n' +
            'Экология и природопользование – 35\n' +
            'Экономика – 35\n' +
            'Эксплуатация транспортно-технологических машин и комплексов – 15\n' +
            'Электроника и наноэлектроника – 25\n' +
            'Электроэнергетика и электротехника – 60'
        ),
        reply_markup=buttons
        )


@save_user_and_messages
def bonuses_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            '*Победители конкурса «Лидер школы»* получают право быть зачисленными  ' +
            'на обучение на места за счёт средств «Образовательного гранта» с ' +
            'предоставлением социального пакета: \n' +
            '- предоставление койко-места в общежитии; \n' +
            '- обеспечение форменной одеждой; \n' +
            '- компенсация проезда к месту проживания для иногородних обучающихся   ' +
            'один раз в первом семестре после первой сессии *(до 20 000 рублей)*; \n' +
            '- академическая стипендия в установленном порядке; \n' +
            '- повышенная стипендия (после первого семестра) при сдаче ' +
            'первой сессии на «отлично» – *10 000 рублей*; \n' +
            '- повышенная стипендия (после первого семестра) при сдаче ' +
            'первой сессии на «хорошо» и «отлично» – *5 000 рублей*; \n' +
            '- для победителей и призеров предметных олимпиад на ' +
            'период 5 месяцев – *10 000 рублей*; \n' +
            '- ежедневное бесплатное разовое питание по рабочим дням «Перекус горняка».'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def form_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'После подачи заявки на участие в конкурсе в течение суток ' +
            'Вам придёт письмо с дальнейшей инструкцией \n' +
            '[Подать заявку](https://docs.google.com/forms/d/e'+
            '/1FAIpQLSdZhKA47Elb-iCrvmtnt3FwU2yxFAVDskqg0aZxj7QqCnbUGg/viewform)'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def score_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['От 210 до 219', 'От 220 до 239'],
         ['От 240 до 259', 'От 260'],
         ['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Какая у Вас сумма баллов (включая ИД)?'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def answer_score_leader(update, context):
    chat = update.effective_chat
    text210_219 = (
        'Наземные транспортно-технологические средства – 210  \n' +
        'Стандартизация и метрология – 215 \n' +
        'Техносферная безопасность – 215 \n' +
        'Эксплуатация транспортно-технологических машин и комплексов – 215 \n' +
        'Технологические машины и оборудование – 215 \n' +
        'Приборостроение – 215 \n' +
        'Радиоэлектронные системы и комплексы – 215 \n' +
        'Горное дело – 215 \n'
    )
    text220_239 = (
        'Теплоэнергетика и теплотехника – 220\n' +
        'Металлургия - 220\n' +
        'Технология транспортных процессов – 225\n' +
        'Технология геологической разведки – 225\n' +
        'Прикладная геология – 225\n' +
        'Электроэнергетика и электротехника – 230\n' +
        'Прикладная геодезия – 230\n' +
        'Машиностроение – 235\n' +
        'Автоматизация технологических процессов и производств – 235\n'
    )
    text239_259 = (
        'Электроника и наноэлектроника – 240\n' +
        'Материаловедение и технологии материалов – 240\n' +
        'Землеустройство и кадастры – 240\n' +
        'Управление в технических системах - 240\n' +
        'Экология и природопользование – 245\n' +
        'Нефтегазовые техника и технологии – 250\n' +
        'Системный анализ и управление – 250 \n'
    )
    text260 = (
        'Информационные системы и технологии – 260\n' +
        'Строительство уникальных зданий и сооружений – 260\n' +
        'Строительство – 260\n' +
        'Информатика и вычислительная техника – 265\n' +
        'Менеджмент – 265\n' +
        'Химическая технология – 270\n' +
        'Экономика – 275\n' +
        'Технология художественной обработки материалов – 290\n' +
        'Архитектура – 320 \n'
    )
    if update.message.text == 'От 210 до 219':
        text = (text210_219)
    elif update.message.text == 'От 220 до 239':
        text = (text210_219 + text220_239)
    elif update.message.text == 'От 240 до 259':
        text = text210_219 + text220_239 + text239_259
    elif update.message.text == 'От 260':
        text = text210_219 + text220_239 + text239_259 + text260
    buttons = ReplyKeyboardMarkup(
        [['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=text,
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def tg_channel_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Все актуальные новости Вы сможете получить в Телеграм-канале конкурса: \n' +
            '[Подписаться здесь](https://t.me/mining_leader'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def video_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Отзывы студентов о конкурсе на нашем ютуб-канале: \n' +
            '[Посмотреть здесь](https://www.youtube.com/@user-yp5ch9mh8n/videos)'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def requirement_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Основновные условия', 'Важные даты конкурса'],
         ['Пороговые баллы', 'Подать заявку'],
         ['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Выберите пункт меню.'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def dates_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            '*Заключение соглашений о намерениях:* \n' +
            'с 15 декабря 2023 по 4 июля 2024 года  \n\n' +
            '*Подача заявления:*\n' +
            'с 20 июня 2024 года по 4 июля 2024 года \n\n' +
            '*Подача оригинала:*\n' +
            'не позднее 10 июля 2024 года \n\n' +
            '*Выдача «Гранта»:*\n' +
            'после 11 июля 2024 года \n\n'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


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
    r'Лидер* школы|Вернуться назад к Лидеру школы':
        leader_of_the_school,
    r'О конкурсе':
        about_leader,
    r'Цели и задачи конкурса':
        mission_leader,
    r'Количество мест по гранту':
        places_leader,
    r'Бонусы "Гранта"':
        bonuses_leader,
    r'Подать заявку':
        form_leader,
    r'Пороговые баллы':
        score_leader,
    r'От 210 до 219|От 220 до 239|От 240 до 259|От 260':
        answer_score_leader,
    r'Ссылка на ТГ-канал':
        tg_channel_leader,
    r'Видеоотзывы студентов':
        video_leader,
    r'Условия участия':
        requirement_leader,
    r'Важные даты конкурса':
        dates_leader,
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
