import re
import time
import datetime
from telegram import (
    Bot,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)

from telegram.ext import (
    Filters,
    MessageHandler,
    Updater,
    CommandHandler,
    ConversationHandler
)

from telegram.utils.request import Request

from django.utils import timezone
from django.core.management.base import BaseCommand
from django.conf import settings

from users.models import User, Message, Call


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
        [['/statistic', '/massmail'], ],
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
    now = timezone.now()
    print(now)
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
        text=(
            f'За {dict_time[text]} было {count_message} ' +
            f'сообщений от {count_users} пользователей'
        ),
        parse_mode="MARKDOWN"
    )


@check_admin
def massmail(update, context):
    buttons = ReplyKeyboardMarkup(
        [['/cancel'], ],
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
            [['Да', 'Нет'], ],
            resize_keyboard=True
            )
        update.message.reply_text(
            'Ты уверен в массовом спаме?',
            reply_markup=buttons
        )
        return ARE_YOU_SHURE
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
        update.message.reply_text((
            'Ты уверен в массовом спаме? Если да,' +
            'то введи первое слово сообщения'
            ),
            reply_markup=buttons
        )
        return ARE_YOU_SHURE2
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
            text=(
                f'Успешно отправлено {successfully_count} ' +
                f'сообщений, ошибок {banned_count}'
            )
        )
        return ConversationHandler.END
    update.message.reply_text(
        'Неверно, попробуй ещё раз',
        reply_markup=ReplyKeyboardRemove()
    )


@check_admin
def cancel(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['/statistic', '/massmail'], ],
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
         ['Количество мест по гранту', 'Необходимые ЕГЭ'],
         ['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_photo(
        chat_id=chat.id,
        photo=(
            'https://leaderschool.spmi.ru/sites/' +
            'default/files/2024-03/IMG_1522-1-0.jpg'
        ),
        caption=(
            '«Лидер школы России» – это программа, нацеленная ' +
            'на совершенствование системы среднего образования ' +
            'и призванная мотивировать талантливых старшеклассников ' +
            'выбирать при поступлении технические вузы. Ведь наша ' +
            'страна сегодня остро нуждается в молодых компетентных ' +
            'инженерах, способных обеспечить в перспективе безболезненную ' +
            'смену поколений на производстве. Кроме того, данный ' +
            'проект представляет собой один из механизмов интеграции ' +
            'средней и высшей школы, надёжный мост, связующий наше ' +
            'настоящее и будущее, а также повышающий устойчивость социально' +
            '-экономического развития каждого из нас и ' +
            'всего общества в целом. \n' +
            '*Ректор Санкт-Петербургского горного университета ' +
            'императрицы Екатерины II В.С. Литвиненко*'
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
            'Конкурс «Лидер школы» проводится с целью организации ' +
            'качественного приёма на обучение по специальностям ' +
            'Санкт-Петербургского горного университета в 2024 году. \n' +
            'Задачи конкурса направлены на: \n' +
            '-минимизацию рисков ошибочного выбора и поступления ' +
            'на образовательную программу, ' +
            'не соответствующую потребностям и ожиданиям поступающего; \n' +
            '-предоставление приоритетного гарантированного ' +
            'зачисления для поступающих; \n' +
            '-создание необходимых условий стимулирования и ' +
            'поддержки талантливой молодежи; \n' +
            '-предоставление особых конкурентных преимуществ ' +
            'для обучения в Университете для  ' +
            'выпускников образовательных организаций из регионов ' +
            'Российской Федерации. \n' +
            '[Сайт конкурса](https://leaderschool.spmi.ru/) \n' +
            '[Видеоролик о конкурсе](https://www.youtube.com/' +
            'watch?v=kqjqvnK2ZDA) \n'
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
            'Эксплуатация транспортно-технологических машин ' +
            'и комплексов – 15\n' +
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
            '*Победители конкурса «Лидер школы»* получают право быть ' +
            'зачисленными на обучение на места за счёт средств ' +
            '«Образовательного гранта» с ' +
            'предоставлением социального пакета: \n' +
            '- предоставление койко-места в общежитии; \n' +
            '- обеспечение форменной одеждой; \n' +
            '- компенсация проезда к месту проживания для иногородних ' +
            'обучающихся один раз в первом семестре после первой ' +
            'сессии *(до 20 000 рублей)*; \n' +
            '- повышенная академическая стипендия предоставляемая в ' +
            'установленном порядке:' +
            'при сдаче первой сессии на «отлично» – до 10 000 рублей*; \n' +
            '- при сдаче ' +
            'первой сессии на «хорошо» и «отлично» – до 5 000 рублей*; \n' +
            '- для победителей и призеров предметных олимпиад на ' +
            'период 5 месяцев – *10 000 рублей*; \n' +
            '- «Перекус горняка».'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def need_ege_leader(update, context):
    chat = update.effective_chat
    context.bot.send_photo(
        chat_id=chat.id,
        photo=(
            'https://priem.spmi.ru/sites/default/files/' +
            'manager/10ac7080-967e-48c3-985e-ad8af81ffa2a.jpg'
        ),
        caption=(
            'С перечнем ЕГЭ можете ознакомиться здесь.'
        ),
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
            '[Подать заявку](https://docs.google.com/forms/d/e' +
            '/1FAIpQLSdZhKA47Elb-iCrvmtnt3FwU2yxFAVDskqg0' +
            'aZxj7QqCnbUGg/viewform)'
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
        'Эксплуатация транспортно-технологических ' +
        'машин и комплексов – 215 \n' +
        'Технологические машины и оборудование – 215 \n' +
        'Приборостроение – 215 \n' +
        'Радиоэлектронные системы и комплексы – 215 \n' +
        'Горное дело – 215 \n'
    )
    text220_239 = (
        'Теплоэнергетика и теплотехника – 220\n' +
        'Металлургия - 220\n' +
        'Технология художественной обработки материалов – 220\n' +
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
            'Все актуальные новости Вы сможете получить в ' +
            'Телеграм-канале конкурса: \n' +
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
            '[Посмотреть здесь](https://www.youtube.com/' +
            '@user-yp5ch9mh8n/videos)'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def requirement_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Основные условия', 'Важные даты конкурса'],
         ['Пороговые баллы', 'Подать заявку'],
         ['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Выберите интересующий Вас пункт меню.'
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
            '*Подведение итогов конкурса:*\n' +
            '5 июля 2024 года \n\n' +
            '*Подача оригинала:*\n' +
            'не позднее 10 июля 2024 года \n\n' +
            '*Выдача «Гранта»:*\n' +
            'после 11 июля 2024 года \n\n'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def basic_conditions_leader(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Вернуться назад к Лидеру школы']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Участие в конкурсе «Лидер школы» могут принимать: \n' +
            '- граждане Российской Федерации, закончившие обучение по ' +
            'образовательным программам среднего общего образования ' +
            '(учащиеся 11 классов школ, выпускники школ предыдущих лет); \n' +
            '- иностранные граждане и лица без гражданства, ' +
            'закончившие обучение по образовательным программам среднего ' +
            'общего образования (в том числе обучающиеся за рубежом) ' +
            '(учащиеся выпускных классов школ). \n\n' +

            'Для участия в конкурсе необходимо: \n' +
            '- [Подать заявку](https://docs.google.com/forms/d/e/' +
            '1FAIpQLSdZhKA47Elb-iCrvmtnt3FwU2yxFAVDskqg0aZxj7QqCnbUGg/' +
            'viewform) \n' +
            '- Заключить соглашение о намерениях участия в конкурсе. \n' +
            '- Предоставить в Приёмную комиссию необходимые документы в ' +
            'установленные сроки. \n' +
            '- Набрать по результатам сдачи ЕГЭ суммарный конкурсный балл ' +
            'не ниже установленных пороговых значений.'
        ),
        reply_markup=buttons,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def do_i_dont_know(update, context):
    buttons = ReplyKeyboardMarkup(
        [['Вернуться в начало'],
         ['Позвать оператора']],
        resize_keyboard=True
        )
    reply_text = (
        'Я советую пользоваться кнопками навигации. \n' +
        'Предлагаю вернуться к началу или обратиться к оператору.'
    )
    update.message.reply_text(
        text=reply_text,
        reply_markup=buttons,
        parse_mode="MARKDOWN"
    )


@save_user_and_messages
def call_operator(update, context):
    chat = update.effective_chat
    button = ReplyKeyboardMarkup(
        [['Вернуться в начало'],
         ['Запросить звонок']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Можете написать нашему оператору. ' +
            'https://t.me/Mining_university_official ' +
            '. Также можете запросить звонок оператора, ' +
            'мы свяжемся с Вами в ближайшее время'
        ),
        reply_markup=button
        )


@save_user_and_messages
def start_entrance(update, context):
    chat = update.effective_chat
    button = ReplyKeyboardMarkup(
        [['Подать документы',
          'Порядок приема на обучение'],
         ['План приема и перечень ЕГЭ3',
          'Сроки приема на обучение'],
         ['Сведения об образовательных программах',
          'Вернуться в начало']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text='Выберите интересующий Вас пункт меню.',
        reply_markup=button
        )


@save_user_and_messages
def apply_documents(update, context):
    chat = update.effective_chat
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Для подачи документов переходите ' +
            '[по ссылке](https://priem.spmi.ru/podat-dokumenty-1/) \n' +
            'Там и ссылка на личный кабинет и инструкция ' +
            ' по заполнению заявления.'
        ),
        parse_mode="MARKDOWN"
    )


@save_user_and_messages
def order_entrance(update, context):
    chat = update.effective_chat
    button = ReplyKeyboardMarkup(
        [['Вернуться в начало']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            '[Здесь](http://priem.spmi.ru/sites/default/files/' +
            'manager/01.Postupaushim/Pravila_priema.pdf) ' +
            'Вы можете получить информацию о Порядке приема на обучение по  ' +
            'программам базового высшего образования в 2024 году.'),
        reply_markup=button,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def kcp_entrance(update, context):
    chat = update.effective_chat
    button = ReplyKeyboardMarkup(
        [['Вернуться в начало']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text='[Здесь](http://priem.spmi.ru/sites/default/' +
        'files/manager/03.PlanPriema/kcp_bak_spec.pdf) ' +
        'Вы найдете информацию о количестве бюджетных мест и ' +
        'предметах ЕГЭ, необходимых для поступления',
        reply_markup=button,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def deadlines_entrance(update, context):
    chat = update.effective_chat
    button = ReplyKeyboardMarkup(
        [['Вернуться в начало']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text='[Здесь](https://priem.spmi.ru/sites/default/files/' +
        'manager/01.Postupaushim/' +
        'Informaciya_o_srokah_provedeniya_priema.pdf)' +
        'Вы можете найти информацию о сроках приема на обучение по ' +
        'программам базового высшего образования в 2024 году',
        reply_markup=button,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def landing_entrance(update, context):
    chat = update.effective_chat
    button = ReplyKeyboardMarkup(
        [['Вернуться в начало']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text='[Здесь](https://landing.spmi.ru/) ' +
        'Вы найдете характеристику образовательных программ ' +
        '(сроки обучения, изучаемые дисциплины, карьерные перспективы и др.)',
        reply_markup=button,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def dormitory_main(update, context):
    chat = update.effective_chat
    button = ReplyKeyboardMarkup(
        [['Cтоимость проживания', 'Количество мест для заселения'],
         ['Вернуться в начало']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Санкт-Петербургский горный университет имеет ' +
            '9 своих комфортабельных общежитий, расположенных ' +
            'на Васильевском острове вблизи учебных центов.'
        ),
        reply_markup=button,
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def coast_dormitory(update, context):
    chat = update.effective_chat
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Ознакомиться со стоимостью проживания и категориями ' +
            'комфортности Вы можете по ссылке - ' +
            'https://spmi.ru/stoimost-prozivania-s-ucetom-komfortnosti'
        ),
        parse_mode="MARKDOWN"
        )


@save_user_and_messages
def rooms_dormitory(update, context):
    chat = update.effective_chat
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Количество мест для заселения студентов ' +
            'первого курса в 2024 году Вы можете узнать здесь ' +
            '- https://priem.spmi.ru/sites/default/files/' +
            'manager/obzhezhitia/2024/svodnaya.pdf'
        ),
        parse_mode="MARKDOWN"
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

    list_operator_massmail = User.objects.filter(
        access_level__in=['Admin', 'Operator']
    )
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
def aspirant(update, context):
    chat = update.effective_chat
    buttons = ReplyKeyboardMarkup(
        [['Сроки подачи документов АСП', 'Документы для поступления АСП'],
         ['Перечень вступительных испытаний АСП', 'Списки поступающих АСП'],
         ['Конкурсные группы и количество мест АСП', 'Способы подачи документов АСП'],
         ['Учет дополнительных компетенций АСП', 'Контакты АСП'],
         ['Вернуться в начало']],
        resize_keyboard=True
        )
    context.bot.send_message(
        chat_id=chat.id,
        text=('Выберете интересующее Вас меню'),
        reply_markup=buttons
        )


@save_user_and_messages
def time_asp(update, context):
    chat = update.effective_chat
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            'Прием заявлений на обучение на места за счет ' +
            'бюджетных ассигнований федерального бюджета и по ' +
            'договорам об оказании платных образовательных услуг: \n' +
            '1 период: **с 01.07.2024 по 22.07.2024**  \n' +
            '2 период: **с 19.08.2024 по 27.08.2024** \n\n' +
            'Защита Научного задела по теме и объекту научных исследований \n' +
            '**с 28.08.2024 по 04.09.2024** \n\n' +
            'Проведение консультаций по Собеседованию \n' +
            '**05.09.2024** \n\n' +
            'Собеседование \n' +
            '**06.09.2024** \n\n' +
            'Резервный день для сдачи вступительных испытаний  \n' +
            '**09.09.2024** \n\n' +
            'Завершение приема оригиналов документов установленного ' +
            'образца для поступающих в рамках КЦП \n' +
            '**10.09.2024** \n\n' +
            'Завершение приема оригиналов документов установленного  ' +
            'образца, либо заявлений о согласии на зачисление по договорам ' +
            'об оказании платных образовательных услуг\n' +
            '**11.09.2024** \n'
        ),
        parse_mode="MARKDOWN"
    )


@save_user_and_messages
def wake_up(update, context):
    chat = update.effective_chat
    name = update.message.chat.first_name
    buttons = ReplyKeyboardMarkup(
        [['Хочу узнать про поступление', 'Конкурс "Лидер школы"'],
         ['Общежития', 'Аспирантура'],
         ['Не нашел ответа. Позвать оператора']],
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
    r'Необходимые ЕГЭ':
        need_ege_leader,
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
    r'Основные условия':
        basic_conditions_leader,
    r'Хочу узнать про поступление':
        start_entrance,
    r'Подать документы':
        apply_documents,
    r'Порядок приема на обучение':
        order_entrance,
    r'План приема и перечень ЕГЭ':
        kcp_entrance,
    r'Сроки приема на обучение':
        deadlines_entrance,
    r'Сведения об образовательных программах':
        landing_entrance,
    r'Общежития':
        dormitory_main,
    r'Cтоимость проживания':
        coast_dormitory,
    r'Количество мест для заселения':
        rooms_dormitory,
    r'Аспирантура':
        aspirant,
    r'Сроки подачи документов АСП':
        time_asp,
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

        for a in dict:
            updater.dispatcher.add_handler(
                MessageHandler(
                    Filters.regex(
                        re.compile(a, re.IGNORECASE)),
                    dict[a]
                )
            )

        conv_handler_call = ConversationHandler(
            entry_points=[
                MessageHandler(
                    Filters.regex(
                        re.compile(
                            r'Запросить звонок',
                            re.IGNORECASE
                        )),
                    call_request
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

        message_handler = MessageHandler(Filters.text, do_i_dont_know)

        updater.dispatcher.add_handler(message_handler)

        updater.start_polling()
        updater.idle()
