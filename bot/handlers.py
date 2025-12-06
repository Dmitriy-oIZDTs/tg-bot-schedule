"""
Основные обработчики команд телеграм-бота
"""

from datetime import datetime, timedelta
import logging

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)

from config.settings import BOT_TOKEN
from database.db_manager import DatabaseManager
from utils.reporting import export_user_actions_to_csv

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
db = DatabaseManager()


# ============== СОСТОЯНИЯ ==============

class UserStates(StatesGroup):
    """Состояния пользователя"""
    waiting_for_group = State()


class SearchStates(StatesGroup):
    """Состояния для поиска"""
    waiting_for_group_search = State()
    waiting_for_teacher_search = State()
    waiting_for_room_search = State()


# ============== РОЛИ И ЛОГИ ==============

def is_admin(user: dict | None) -> bool:
    return bool(user) and user.get("role") in ("admin", "developer")


def is_developer(user: dict | None) -> bool:
    return bool(user) and user.get("role") == "developer"


def log_user_action(telegram_id: int, action: str, details: str = ""):
    """
    Логируем действие:
    - в стандартный лог (logging)
    - в БД (таблица user_actions_log через DatabaseManager.log_user_action)
    """
    logger.info(f"[USER_ACTION] tg_id={telegram_id} action={action} details={details}")
    try:
        db.log_user_action(telegram_id, action, details)
    except Exception as e:
        logger.error(f"Ошибка записи действия пользователя в БД: {e}")


# ============== КЛАВИАТУРЫ ==============

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура"""
    buttons = [
        [KeyboardButton(text="📅 Мое расписание")],
        [KeyboardButton(text="🔍 Поиск по группе")],
        [KeyboardButton(text="👨‍🏫 Поиск по преподавателю")],
        [KeyboardButton(text="🚪 Поиск по аудитории")],
        [KeyboardButton(text="⚙️ Сменить группу")],
        [KeyboardButton(text="❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_days_keyboard(context_type="my", context_id=None) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора дня недели
    context_type: "my" | "group" | "teacher" | "room"
    context_id: идентификатор (номер группы, id преподавателя, id аудитории)
    """
    days = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ']
    buttons: list[list[InlineKeyboardButton]] = []

    # Первая строка - дни недели
    row = []
    for day in days:
        if context_type == "my":
            callback = f"day_{day}"
        else:
            callback = f"{context_type}_day_{day}_{context_id}"
        row.append(InlineKeyboardButton(text=day, callback_data=callback))
    buttons.append(row)

    # Вторая строка - вся неделя и выбор недели
    if context_type == "my":
        week_cb = "week_current"
        select_cb = "select_week"
    else:
        week_cb = f"{context_type}_week_current_{context_id}"
        select_cb = f"{context_type}_select_week_{context_id}"
    
    buttons.append([
        InlineKeyboardButton(text="📅 Вся неделя", callback_data=week_cb),
        InlineKeyboardButton(text="🔢 По номеру недели", callback_data=select_cb),
    ])

    # Третья строка - навигация
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_week_selector_keyboard(context_type="my", context_id=None) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора номера недели
    context_type: "my" | "group" | "teacher" | "room"
    context_id: идентификатор
    """
    # Вычисляем текущую неделю от 1 сентября
    today = datetime.now()
    september_1 = datetime(today.year if today.month >= 9 else today.year - 1, 9, 1)
    current_week = ((today - september_1).days // 7) + 1

    buttons: list[list[InlineKeyboardButton]] = []

    # Показываем недели по 4 в ряд (1..20)
    for i in range(0, 20, 4):
        row = []
        for week_num in range(i + 1, min(i + 5, 21)):
            text = f"✅ {week_num}" if week_num == current_week else str(week_num)
            if context_type == "my":
                callback = f"week_{week_num}"
            else:
                callback = f"{context_type}_week_{week_num}_{context_id}"
            row.append(InlineKeyboardButton(text=text, callback_data=callback))
        buttons.append(row)

    if context_type == "my":
        back_cb = "back_to_days"
    else:
        back_cb = f"{context_type}_back_to_days_{context_id}"

    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_settings_keyboard(user_settings: dict) -> InlineKeyboardMarkup:
    """
    Клавиатура настроек (5 пунктов)
    """
    notif_text = "🔔 Уведомления: Вкл" if user_settings.get("notifications", True) else "🔕 Уведомления: Выкл"
    time_text = "⏰ Формат времени: 24ч" if user_settings.get("time_format", "24") == "24" else "⏰ Формат времени: 12ч"
    view_text = "📅 Вид по умолчанию: День" if user_settings.get("default_view", "day") == "day" else "📆 Вид по умолчанию: Неделя"

    buttons = [
        [InlineKeyboardButton(text="👥 Сменить группу", callback_data="settings_change_group")],
        [InlineKeyboardButton(text=time_text, callback_data="settings_time_format")],
        [InlineKeyboardButton(text=notif_text, callback_data="settings_notifications")],
        [InlineKeyboardButton(text=view_text, callback_data="settings_default_view")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==============

def format_schedule_day(schedule: list[dict], group_number: str, date: datetime) -> str:
    """Форматирование расписания на день"""
    if not schedule:
        return f"📅 Расписание группы {group_number}\nНа этот день занятий нет"

    text = f"📅 <b>Расписание группы {group_number}</b>\n"
    text += f"📆 <b>{date.strftime('%d.%m.%Y (%A)')}</b>\n\n"

    for lesson in schedule:
        text += f"🕐 <b>Пара № {lesson['lesson_number']} ({lesson['start_time']} – {lesson['end_time']})</b>\n"
        text += f"📚 {lesson['subject_name']}"

        if lesson.get('subject_type'):
            text += f" ({lesson['subject_type']})"

        text += "\n"

        if lesson.get('teacher_fio'):
            text += f"👨‍🏫 Преподаватель: {lesson['teacher_fio']}\n"

        if lesson.get('building_name') and lesson.get('room_number'):
            text += f"🏢 Аудитория: {lesson['room_number']} ({lesson['building_name']})\n"

        if lesson.get('notes'):
            text += f"📝 {lesson['notes']}\n"

        text += "\n"

    return text


def format_teacher_schedule(teacher: dict, schedule: list[dict], date: datetime) -> str:
    """Форматирование расписания преподавателя на день"""
    if not schedule:
        return (
            f"👨‍🏫 {teacher['fio']}\n"
            f"📆 {date.strftime('%d.%m.%Y')}\n\n"
            f"На сегодня пар нет."
        )

    text = f"👨‍🏫 <b>Расписание: {teacher['fio']}</b>\n"
    text += f"📆 {date.strftime('%d.%m.%Y (%A)')}\n\n"

    for lesson in schedule:
        text += f"🕐 <b>{lesson['lesson_number']} пара ({lesson['start_time']} - {lesson['end_time']})</b>\n"
        text += f"📚 {lesson['subject_name']}\n"
        text += f"👥 Группа: {lesson['group_number']}\n"
        if lesson.get('room_number'):
            text += f"🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
        text += "\n"

    return text


def format_room_schedule(room: dict, schedule: list[dict], date: datetime) -> str:
    """Форматирование расписания аудитории на день"""
    if not schedule:
        return (
            f"🚪 Аудитория {room['room_number']}\n"
            f"📆 {date.strftime('%d.%m.%Y')}\n\n"
            f"На этот день свободна 🎉"
        )

    text = f"🚪 <b>Аудитория {room['room_number']}</b>\n"
    text += f"📆 {date.strftime('%d.%m.%Y (%A)')}\n\n"

    for lesson in schedule:
        text += f"🕐 <b>{lesson['lesson_number']} пара ({lesson['start_time']} - {lesson['end_time']})</b>\n"
        text += f"📚 {lesson['subject_name']}\n"
        text += f"👥 Группа: {lesson['group_number']}\n"
        if lesson.get('teacher_fio'):
            text += f"👨‍🏫 {lesson['teacher_fio']}\n"
        text += "\n"

    return text


# ============== КОМАНДЫ ОСНОВНЫЕ ==============

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработка команды /start"""
    log_user_action(message.from_user.id, "start", "/start")
    telegram_id = message.from_user.id
    user = db.get_user_by_telegram_id(telegram_id)

    if user and user.get('group_id'):
        await message.answer(
            f"С возвращением!\n"
            f"Ваша группа: {user['group_number']}\n\n"
            f"Выберите действие:",
            reply_markup=get_main_keyboard()
        )
    else:
        groups = db.get_all_groups()
        groups_text = "\n".join([f"{g['group_number']}" for g in groups])

        await message.answer(
            "👋 Добро пожаловать в бот расписания!\n\n"
            f"Выберите вашу группу из списка:\n\n"
            f"<code>{groups_text}</code>\n\n"
            "Введите номер группы:",
            parse_mode='HTML'
        )
        await state.set_state(UserStates.waiting_for_group)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработка команды /help"""
    help_text = """
📖 <b>Справка по боту расписания</b>

<b>Основные команды:</b>
/start - Начать работу с ботом
/help - Показать эту справку
/settings - Настройки бота
/about - Информация о боте и авторе
/group [номер] - Посмотреть расписание группы
/teacher [ФИО] - Найти преподавателя
/room [ауд.] - Посмотреть занятость аудитории
/logs [дней] - (админ) Выгрузка отчета о действиях
/setrole &lt;tg_id&gt; &lt;role&gt; - (dev) Назначить роль пользователю
/cancel - Отмена текущего действия

<b>Как пользоваться:</b>
1️⃣ При первом запуске выберите свою группу через /start
2️⃣ Нажмите "📅 Мое расписание" для просмотра
3️⃣ Выберите день недели или всю неделю
4️⃣ Можно выбрать неделю по номеру (с 1 сентября)
5️⃣ Используйте /settings для изменения личных настроек

<b>Поиск:</b>
🔍 Поиск по группе - расписание любой группы
👨‍🏫 Поиск по преподавателю - где и когда пары
🚪 Поиск по аудитории - занятость кабинета

<b>Автор:</b> Романов Дмитрий Владимирович
<b>Группа:</b> o.ИЗДтс 23.2/Б1-22
"""
    await message.answer(help_text, parse_mode='HTML')


@dp.message(F.text == "❓ Помощь")
async def help_button(message: types.Message):
    # просто используем ту же логику, что и для /help
    await cmd_help(message)



@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer(
        "Действие отменено.",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("about"))
async def cmd_about(message: types.Message):
    """
    Информация о боте и авторе + картинка.
    Файл static/bot_logo.png нужно положить сам.
    """
    log_user_action(message.from_user.id, "about", "/about")

    caption = (
        "🤖 <b>Бот расписания</b>\n\n"
        "Помогает быстро узнать расписание по группе, преподавателю или аудитории.\n\n"
        "Автор: <b>Романов Дмитрий Владимирович</b>\n"
        "Группа: <b>o.ИЗДтс 23.2/Б1-22</b>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 Сайт вуза",
                    url="https://example-university.ru"  # замени на реальный
                )
            ]
        ]
    )

    try:
        photo = FSInputFile("static/bot_logo.png")  # положи файл в папку static
        await message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить картинку: {e}")
        await message.answer(caption, parse_mode="HTML")


# ============== ВЫБОР И СМЕНА ГРУППЫ ==============

@dp.message(UserStates.waiting_for_group)
async def process_group_selection(message: types.Message, state: FSMContext):
    """Обработка выбора группы"""
    group_number = message.text.strip().upper()

    # Игнорируем кнопки меню
    if group_number in [
        '📅 МОЕ РАСПИСАНИЕ',
        '🔍 ПОИСК ПО ГРУППЕ',
        '👨‍🏫 ПОИСК ПО ПРЕПОДАВАТЕЛЮ',
        '🚪 ПОИСК ПО АУДИТОРИИ',
        '⚙️ СМЕНИТЬ ГРУППУ',
        '❓ ПОМОЩЬ'
    ]:
        return

    groups = db.get_all_groups()
    group = next((g for g in groups if g['group_number'].upper() == group_number), None)

    if not group:
        groups_text = "\n".join([f"{g['group_number']}" for g in groups])
        await message.answer(
            f"❌ Группа '{group_number}' не найдена.\n\n"
            f"Доступные группы:\n\n"
            f"<code>{groups_text}</code>\n\n"
            f"Введите точное название группы:",
            parse_mode='HTML'
        )
        return

    # Создаем или обновляем пользователя
    telegram_id = message.from_user.id
    username = message.from_user.username
    user = db.get_user_by_telegram_id(telegram_id)

    if user:
        db.update_user_group(user['id'], group['id'])
    else:
        user = db.create_user(telegram_id, username, None, role='user', group_id=group['id'])

    await state.clear()

    await message.answer(
        f"✅ Группа установлена: {group_number}\n"
        f"🏛 Факультет: {group['faculty_name']}\n\n"
        f"Теперь вы можете просматривать расписание!",
        reply_markup=get_main_keyboard()
    )


@dp.message(F.text == "⚙️ Сменить группу")
async def change_group(message: types.Message, state: FSMContext):
    """Смена группы пользователя"""
    groups = db.get_all_groups()
    groups_text = "\n".join([f"{g['group_number']}" for g in groups])

    await message.answer(
        f"Выберите новую группу из списка:\n\n"
        f"<code>{groups_text}</code>\n\n"
        "Введите номер группы:",
        parse_mode='HTML'
    )
    await state.set_state(UserStates.waiting_for_group)


# ============== МОЕ РАСПИСАНИЕ ==============

@dp.message(F.text == "📅 Мое расписание")
async def show_my_schedule(message: types.Message):
    """Показать расписание пользователя c учетом default_view (day|week)"""
    log_user_action(message.from_user.id, "my_schedule", "button")
    user = db.get_user_by_telegram_id(message.from_user.id)

    if not user or not user.get('group_number'):
        await message.answer(
            "❌ Сначала выберите группу.\n"
            "Используйте /start для выбора группы."
        )
        return

    # --- ТУТ ЧИТАЕМ НАСТРОЙКИ ---
    settings = db.get_user_settings(user["id"]) or {}
    view = settings.get("default_view", "day")  # 'day' или 'week'

    # Если по умолчанию НЕДЕЛЯ — сразу показываем как кнопка "📅 Вся неделя"
    if view == "week":
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())  # Понедельник этой недели

        week_schedule_text = f"📅 <b>Расписание группы {user['group_number']}</b>\n"
        week_schedule_text += f"📆 Неделя с {monday.strftime('%d.%m.%Y')}\n\n"

        day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']

        for i in range(6):  # ПН–СБ
            day = monday + timedelta(days=i)
            day_str = day.strftime('%Y-%m-%d')
            day_name = day_names[i]

            week_schedule_text += f"<b>{day_name} ({day.strftime('%d.%m')})</b>\n"

            schedule = db.get_schedule_by_group(user['group_number'], day_str)

            if schedule:
                for lesson in schedule:
                    week_schedule_text += (
                        f"  🕐 {lesson['lesson_number']} пара "
                        f"({lesson['start_time']}-{lesson['end_time']})\n"
                        f"  📚 {lesson['subject_name']}\n"
                    )
                    if lesson.get('teacher_fio'):
                        week_schedule_text += f"  👨‍🏫 {lesson['teacher_fio']}\n"
                    if lesson.get('room_number'):
                        week_schedule_text += f"  🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
            else:
                week_schedule_text += "  Занятий нет\n"

            week_schedule_text += "\n"

        await message.answer(
            week_schedule_text,
            reply_markup=get_days_keyboard("my"),
            parse_mode='HTML'
        )
        return

    # --- ИНАЧЕ (view == 'day') — как было: только сегодня ---
    today = datetime.now()
    schedule = db.get_schedule_by_group(user['group_number'], today.strftime('%Y-%m-%d'))

    if schedule:
        schedule_text = format_schedule_day(schedule, user['group_number'], today)
    else:
        schedule_text = (
            f"📅 Расписание группы {user['group_number']}\n"
            f"📆 {today.strftime('%d.%m.%Y (%A)')}\n\n"
            f"На сегодня занятий нет 🎉"
        )

    await message.answer(
        schedule_text,
        reply_markup=get_days_keyboard("my"),
        parse_mode='HTML'
    )



# ============== CALLBACK: ДНИ/НЕДЕЛИ (МОЕ РАСПИСАНИЕ) ==============

@dp.callback_query(F.data.startswith("day_"))
async def process_day_selection(callback: types.CallbackQuery):
    """Обработка выбора дня недели"""
    user = db.get_user_by_telegram_id(callback.from_user.id)

    if not user or not user.get('group_number'):
        await callback.answer("❌ Группа не выбрана", show_alert=True)
        return

    day_map = {'ПН': 0, 'ВТ': 1, 'СР': 2, 'ЧТ': 3, 'ПТ': 4, 'СБ': 5}
    day_abbr = callback.data.split('_')[1]
    target_weekday = day_map[day_abbr]

    today = datetime.now()
    days_ahead = target_weekday - today.weekday()
    if days_ahead < 0:
        days_ahead += 7

    target_date = today + timedelta(days=days_ahead)

    schedule = db.get_schedule_by_group(user['group_number'], target_date.strftime('%Y-%m-%d'))

    if schedule:
        schedule_text = format_schedule_day(schedule, user['group_number'], target_date)
    else:
        schedule_text = (
            f"📅 Расписание группы {user['group_number']}\n"
            f"📆 {target_date.strftime('%d.%m.%Y (%A)')}\n\n"
            f"На этот день занятий нет 🎉"
        )

    await callback.message.edit_text(
        schedule_text,
        reply_markup=get_days_keyboard("my"),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data == "week_current")
async def show_week_schedule(callback: types.CallbackQuery):
    """Показать расписание МОЕЙ группы на всю текущую неделю (ПН–СБ)"""
    user = db.get_user_by_telegram_id(callback.from_user.id)

    if not user or not user.get('group_number'):
        await callback.answer("❌ Группа не выбрана", show_alert=True)
        return

    group_number = user['group_number']

    today = datetime.now()
    # Понедельник текущей недели
    monday = today - timedelta(days=today.weekday())  # weekday: ПН=0
    # Собираем текст
    week_schedule_text = f"📅 <b>Расписание группы {group_number}</b>\n"
    week_schedule_text += f"📆 Неделя с {monday.strftime('%d.%m.%Y')}\n\n"

    day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']

    for i in range(6):  # ПН–СБ
        day = monday + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        day_name = day_names[i]

        week_schedule_text += f"<b>{day_name} ({day.strftime('%d.%m')})</b>\n"

        # БЕРЁМ РАСПИСАНИЕ НА КОНКРЕТНЫЙ ДЕНЬ
        schedule = db.get_schedule_by_group(group_number, day_str)

        if schedule:
            for lesson in schedule:
                week_schedule_text += (
                    f"  🕐 {lesson['lesson_number']} пара "
                    f"({lesson['start_time']}-{lesson['end_time']})\n"
                    f"  📚 {lesson['subject_name']}\n"
                )
                if lesson.get('teacher_fio'):
                    week_schedule_text += f"  👨‍🏫 {lesson['teacher_fio']}\n"
                if lesson.get('room_number'):
                    week_schedule_text += f"  🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
        else:
            week_schedule_text += "  Занятий нет\n"

        week_schedule_text += "\n"

    await callback.message.edit_text(
        week_schedule_text,
        reply_markup=get_days_keyboard("my"),
        parse_mode='HTML'
    )
    await callback.answer()



@dp.callback_query(F.data == "select_week")
async def show_week_selector(callback: types.CallbackQuery):
    """Показать выбор недели"""
    await callback.message.edit_text(
        "🔢 <b>Выберите номер недели</b>\n\n"
        "Отсчет идет с 1 сентября.\n"
        "✅ - текущая неделя",
        reply_markup=get_week_selector_keyboard("my"),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("week_"))
async def show_week_by_number(callback: types.CallbackQuery):
    """Показать расписание по номеру недели"""
    user = db.get_user_by_telegram_id(callback.from_user.id)

    if not user or not user.get('group_number'):
        await callback.answer("❌ Группа не выбрана", show_alert=True)
        return

    week_num = int(callback.data.split('_')[1])

    today = datetime.now()
    september_1 = datetime(today.year if today.month >= 9 else today.year - 1, 9, 1)
    days_to_monday = (7 - september_1.weekday()) % 7
    first_monday = september_1 + timedelta(days=days_to_monday)
    target_monday = first_monday + timedelta(weeks=week_num - 1)

    week_schedule_text = f"📅 <b>Расписание группы {user['group_number']}</b>\n"
    week_schedule_text += f"📆 Неделя {week_num} ({target_monday.strftime('%d.%m.%Y')})\n\n"

    for i in range(6):  # ПН–СБ
        day = target_monday + timedelta(days=i)
        schedule = db.get_schedule_by_group(user['group_number'], day.strftime('%Y-%m-%d'))

        day_name = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'][i]
        week_schedule_text += f"<b>{day_name} ({day.strftime('%d.%m')})</b>\n"

        if schedule:
            for lesson in schedule:
                week_schedule_text += (
                    f"  🕐 {lesson['lesson_number']} пара ({lesson['start_time']}-{lesson['end_time']})\n"
                    f"  📚 {lesson['subject_name']}\n"
                )
                if lesson.get('teacher_fio'):
                    week_schedule_text += f"  👨‍🏫 {lesson['teacher_fio']}\n"
                if lesson.get('room_number'):
                    week_schedule_text += f"  🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
        else:
            week_schedule_text += "  Занятий нет\n"

        week_schedule_text += "\n"

    await callback.message.edit_text(
        week_schedule_text,
        reply_markup=get_week_selector_keyboard("my"),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_days")
async def back_to_days(callback: types.CallbackQuery):
    """Вернуться к выбору дня (на сегодня)"""
    user = db.get_user_by_telegram_id(callback.from_user.id)

    if not user or not user.get('group_number'):
        await callback.answer("❌ Группа не выбрана", show_alert=True)
        await callback.message.delete()
        return

    today = datetime.now()
    schedule = db.get_schedule_by_group(user['group_number'], today.strftime('%Y-%m-%d'))

    if schedule:
        schedule_text = format_schedule_day(schedule, user['group_number'], today)
    else:
        schedule_text = (
            f"📅 <b>Расписание группы {user['group_number']}</b>\n"
            f"📆 {today.strftime('%d.%m.%Y (%A)')}\n\n"
            f"На сегодня занятий нет 🎉"
        )

    await callback.message.edit_text(
        schedule_text,
        reply_markup=get_days_keyboard("my"),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    """Вернуться в главное меню"""
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


# ============== ПОИСК ПО ГРУППЕ ==============

@dp.message(Command("group"))
@dp.message(F.text == "🔍 Поиск по группе")
async def search_group(message: types.Message, state: FSMContext):
    """Поиск расписания по группе (через параметр или через ввод)."""
    log_user_action(message.from_user.id, "group_search", message.text)

    parts = message.text.split(maxsplit=1)
    group_param = None
    if len(parts) > 1 and parts[0].startswith("/group"):
        group_param = parts[1].strip().upper()

    groups = db.get_all_groups()
    groups_text = "\n".join([f"{g['group_number']}" for g in groups])

    if group_param:
        group = next((g for g in groups if g["group_number"].upper() == group_param), None)
        if not group:
            await message.answer(f"❌ Группа '{group_param}' не найдена.")
            return

        today = datetime.now()
        schedule = db.get_schedule_by_group(group_param, today.strftime("%Y-%m-%d"))

        if schedule:
            schedule_text = format_schedule_day(schedule, group_param, today)
        else:
            schedule_text = (
                f"📅 Расписание группы {group_param}\n"
                f"📆 {today.strftime('%d.%m.%Y')}\n\n"
                f"На сегодня занятий нет."
            )

        await message.answer(
            schedule_text, 
            reply_markup=get_days_keyboard("group", group_param),
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"🔍 <b>Поиск расписания по группе</b>\n\n"
        f"Доступные группы:\n\n"
        f"<code>{groups_text}</code>\n\n"
        f"Введите номер группы:",
        parse_mode="HTML",
    )
    await state.set_state(SearchStates.waiting_for_group_search)


@dp.message(SearchStates.waiting_for_group_search)
async def process_group_search(message: types.Message, state: FSMContext):
    """Обработка поиска по группе (FSM)"""
    group_number = message.text.strip().upper()

    if group_number in [
        '📅 МОЕ РАСПИСАНИЕ',
        '🔍 ПОИСК ПО ГРУППЕ',
        '👨‍🏫 ПОИСК ПО ПРЕПОДАВАТЕЛЮ',
        '🚪 ПОИСК ПО АУДИТОРИИ',
        '⚙️ СМЕНИТЬ ГРУППУ',
        '❓ ПОМОЩЬ'
    ]:
        return

    groups = db.get_all_groups()
    group = next((g for g in groups if g['group_number'].upper() == group_number), None)

    if not group:
        await message.answer(f"❌ Группа '{group_number}' не найдена.")
        return

    await state.clear()

    today = datetime.now()
    schedule = db.get_schedule_by_group(group_number, today.strftime('%Y-%m-%d'))

    if schedule:
        schedule_text = format_schedule_day(schedule, group_number, today)
    else:
        schedule_text = (
            f"📅 Расписание группы {group_number}\n"
            f"📆 {today.strftime('%d.%m.%Y')}\n\n"
            f"На сегодня занятий нет."
        )

    await message.answer(
        schedule_text,
        reply_markup=get_days_keyboard("group", group_number),
        parse_mode='HTML'
    )


# ============== CALLBACK: ГРУППА (дни/недели) ==============

@dp.callback_query(F.data.regexp(r"^group_day_(.+)_(.+)$"))
async def group_day_selection(callback: types.CallbackQuery):
    """Выбор дня для группы"""
    parts = callback.data.split('_')
    day_abbr = parts[2]
    group_number = '_'.join(parts[3:])

    day_map = {'ПН': 0, 'ВТ': 1, 'СР': 2, 'ЧТ': 3, 'ПТ': 4, 'СБ': 5}
    target_weekday = day_map[day_abbr]

    today = datetime.now()
    days_ahead = target_weekday - today.weekday()
    if days_ahead < 0:
        days_ahead += 7

    target_date = today + timedelta(days=days_ahead)
    schedule = db.get_schedule_by_group(group_number, target_date.strftime('%Y-%m-%d'))

    if schedule:
        schedule_text = format_schedule_day(schedule, group_number, target_date)
    else:
        schedule_text = (
            f"📅 Расписание группы {group_number}\n"
            f"📆 {target_date.strftime('%d.%m.%Y (%A)')}\n\n"
            f"На этот день занятий нет."
        )

    await callback.message.edit_text(
        schedule_text,
        reply_markup=get_days_keyboard("group", group_number),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^group_week_current_(.+)$"))
async def group_week_current(callback: types.CallbackQuery):
    """Показать всю неделю для выбранной группы (ПН–СБ)"""
    group_number = '_'.join(callback.data.split('_')[3:])

    today = datetime.now()
    monday = today - timedelta(days=today.weekday())  # Понедельник

    week_schedule_text = f"📅 <b>Расписание группы {group_number}</b>\n"
    week_schedule_text += f"📆 Неделя с {monday.strftime('%d.%m.%Y')}\n\n"

    day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']

    for i in range(6):
        day = monday + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        day_name = day_names[i]

        week_schedule_text += f"<b>{day_name} ({day.strftime('%d.%m')})</b>\n"

        # Берём расписание на КОНКРЕТНЫЙ день
        schedule = db.get_schedule_by_group(group_number, day_str)

        if schedule:
            for lesson in schedule:
                week_schedule_text += (
                    f"  🕐 {lesson['lesson_number']} пара "
                    f"({lesson['start_time']}-{lesson['end_time']})\n"
                    f"  📚 {lesson['subject_name']}\n"
                )
                if lesson.get('teacher_fio'):
                    week_schedule_text += f"  👨‍🏫 {lesson['teacher_fio']}\n"
                if lesson.get('room_number'):
                    week_schedule_text += f"  🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
        else:
            week_schedule_text += "  Занятий нет\n"

        week_schedule_text += "\n"

    await callback.message.edit_text(
        week_schedule_text,
        reply_markup=get_days_keyboard("group", group_number),
        parse_mode='HTML'
    )
    await callback.answer()



@dp.callback_query(F.data.regexp(r"^group_select_week_(.+)$"))
async def group_select_week(callback: types.CallbackQuery):
    """Показать селектор недель для группы"""
    group_number = '_'.join(callback.data.split('_')[3:])

    await callback.message.edit_text(
        "🔢 <b>Выберите номер недели</b>\n\n"
        "Отсчет идет с 1 сентября.\n"
        "✅ - текущая неделя",
        reply_markup=get_week_selector_keyboard("group", group_number),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^group_week_(\d+)_(.+)$"))
async def group_week_by_number(callback: types.CallbackQuery):
    """Показать расписание группы по номеру недели"""
    parts = callback.data.split('_')
    week_num = int(parts[2])
    group_number = '_'.join(parts[3:])

    today = datetime.now()
    september_1 = datetime(today.year if today.month >= 9 else today.year - 1, 9, 1)
    days_to_monday = (7 - september_1.weekday()) % 7
    first_monday = september_1 + timedelta(days=days_to_monday)
    target_monday = first_monday + timedelta(weeks=week_num - 1)

    week_schedule_text = f"📅 <b>Расписание группы {group_number}</b>\n"
    week_schedule_text += f"📆 Неделя {week_num} ({target_monday.strftime('%d.%m.%Y')})\n\n"

    for i in range(6):
        day = target_monday + timedelta(days=i)
        schedule = db.get_schedule_by_group(group_number, day.strftime('%Y-%m-%d'))

        day_name = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'][i]
        week_schedule_text += f"<b>{day_name} ({day.strftime('%d.%m')})</b>\n"

        if schedule:
            for lesson in schedule:
                week_schedule_text += (
                    f"  🕐 {lesson['lesson_number']} пара ({lesson['start_time']}-{lesson['end_time']})\n"
                    f"  📚 {lesson['subject_name']}\n"
                )
                if lesson.get('teacher_fio'):
                    week_schedule_text += f"  👨‍🏫 {lesson['teacher_fio']}\n"
                if lesson.get('room_number'):
                    week_schedule_text += f"  🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
        else:
            week_schedule_text += "  Занятий нет\n"

        week_schedule_text += "\n"

    await callback.message.edit_text(
        week_schedule_text,
        reply_markup=get_week_selector_keyboard("group", group_number),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^group_back_to_days_(.+)$"))
async def group_back_to_days(callback: types.CallbackQuery):
    """Вернуться к выбору дня для группы"""
    group_number = '_'.join(callback.data.split('_')[4:])

    today = datetime.now()
    schedule = db.get_schedule_by_group(group_number, today.strftime('%Y-%m-%d'))

    if schedule:
        schedule_text = format_schedule_day(schedule, group_number, today)
    else:
        schedule_text = (
            f"📅 Расписание группы {group_number}\n"
            f"📆 {today.strftime('%d.%m.%Y')}\n\n"
            f"На сегодня занятий нет."
        )

    await callback.message.edit_text(
        schedule_text,
        reply_markup=get_days_keyboard("group", group_number),
        parse_mode='HTML'
    )
    await callback.answer()


# ============== ПОИСК ПО ПРЕПОДАВАТЕЛЮ ==============

@dp.message(Command("teacher"))
@dp.message(F.text == "👨‍🏫 Поиск по преподавателю")
async def search_teacher(message: types.Message, state: FSMContext):
    """
    Поиск расписания преподавателя.
    Можно: /teacher Иванов Иван Иванович
    """
    parts = message.text.split(maxsplit=1)
    teacher_param = None
    if len(parts) > 1 and parts[0].startswith("/teacher"):
        teacher_param = parts[1].strip()

    teachers = db.get_all_teachers()
    teachers_text = "\n".join([f"{t['fio']}" for t in teachers[:20]])

    if teacher_param:
        teacher = next((t for t in teachers if teacher_param.lower() in t['fio'].lower()), None)
        if not teacher:
            await message.answer(f"❌ Преподаватель '{teacher_param}' не найден.")
            return

        today = datetime.now()
        schedule = db.get_teacher_schedule(teacher['id'], today.strftime('%Y-%m-%d'))
        text = format_teacher_schedule(teacher, schedule, today)
        await message.answer(
            text,
            reply_markup=get_days_keyboard("teacher", teacher['id']),
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"👨‍🏫 <b>Поиск по преподавателю</b>\n\n"
        f"Преподаватели (первые 20):\n\n"
        f"<code>{teachers_text}</code>\n\n"
        f"Введите ФИО преподавателя:",
        parse_mode='HTML'
    )
    await state.set_state(SearchStates.waiting_for_teacher_search)


@dp.message(SearchStates.waiting_for_teacher_search)
async def process_teacher_search(message: types.Message, state: FSMContext):
    """Обработка поиска по преподавателю (FSM)"""
    teacher_name = message.text.strip()

    if teacher_name.upper() in [
        '📅 МОЕ РАСПИСАНИЕ',
        '🔍 ПОИСК ПО ГРУППЕ',
        '👨‍🏫 ПОИСК ПО ПРЕПОДАВАТЕЛЮ',
        '🚪 ПОИСК ПО АУДИТОРИИ',
        '⚙️ СМЕНИТЬ ГРУППУ',
        '❓ ПОМОЩЬ'
    ]:
        return

    teachers = db.get_all_teachers()
    teacher = next((t for t in teachers if teacher_name.lower() in t['fio'].lower()), None)

    if not teacher:
        await message.answer(f"❌ Преподаватель '{teacher_name}' не найден.")
        return

    await state.clear()

    today = datetime.now()
    schedule = db.get_teacher_schedule(teacher['id'], today.strftime('%Y-%m-%d'))
    text = format_teacher_schedule(teacher, schedule, today)
    await message.answer(
        text,
        reply_markup=get_days_keyboard("teacher", teacher['id']),
        parse_mode='HTML'
    )


# ============== CALLBACK: ПРЕПОДАВАТЕЛЬ (дни/недели) ==============

@dp.callback_query(F.data.regexp(r"^teacher_day_(.+)_(\d+)$"))
async def teacher_day_selection(callback: types.CallbackQuery):
    """Выбор дня для преподавателя"""
    parts = callback.data.split('_')
    day_abbr = parts[2]
    teacher_id = int(parts[3])

    # Получаем данные преподавателя
    teachers = db.get_all_teachers()
    teacher = next((t for t in teachers if t['id'] == teacher_id), None)
    if not teacher:
        await callback.answer("❌ Преподаватель не найден", show_alert=True)
        return

    day_map = {'ПН': 0, 'ВТ': 1, 'СР': 2, 'ЧТ': 3, 'ПТ': 4, 'СБ': 5}
    target_weekday = day_map[day_abbr]

    today = datetime.now()
    days_ahead = target_weekday - today.weekday()
    if days_ahead < 0:
        days_ahead += 7

    target_date = today + timedelta(days=days_ahead)
    schedule = db.get_teacher_schedule(teacher_id, target_date.strftime('%Y-%m-%d'))
    text = format_teacher_schedule(teacher, schedule, target_date)

    await callback.message.edit_text(
        text,
        reply_markup=get_days_keyboard("teacher", teacher_id),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^teacher_week_current_(\d+)$"))
async def teacher_week_current(callback: types.CallbackQuery):
    """Показать всю неделю для преподавателя"""
    teacher_id = int(callback.data.split('_')[3])

    teachers = db.get_all_teachers()
    teacher = next((t for t in teachers if t['id'] == teacher_id), None)
    if not teacher:
        await callback.answer("❌ Преподаватель не найден", show_alert=True)
        return

    today = datetime.now()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)

    # Собираем расписание на неделю
    week_schedule_text = f"👨‍🏫 <b>Расписание: {teacher['fio']}</b>\n"
    week_schedule_text += f"📆 Неделя с {monday.strftime('%d.%m.%Y')}\n\n"

    for i in range(6):
        day = monday + timedelta(days=i)
        schedule = db.get_teacher_schedule(teacher_id, day.strftime('%Y-%m-%d'))

        day_name = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'][i]
        week_schedule_text += f"<b>{day_name} ({day.strftime('%d.%m')})</b>\n"

        if schedule:
            for lesson in schedule:
                week_schedule_text += (
                    f"  🕐 {lesson['lesson_number']} пара ({lesson['start_time']}-{lesson['end_time']})\n"
                    f"  📚 {lesson['subject_name']}\n"
                    f"  👥 Группа: {lesson['group_number']}\n"
                )
                if lesson.get('room_number'):
                    week_schedule_text += f"  🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
        else:
            week_schedule_text += "  Занятий нет\n"

        week_schedule_text += "\n"

    await callback.message.edit_text(
        week_schedule_text,
        reply_markup=get_days_keyboard("teacher", teacher_id),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^teacher_select_week_(\d+)$"))
async def teacher_select_week(callback: types.CallbackQuery):
    """Показать селектор недель для преподавателя"""
    teacher_id = int(callback.data.split('_')[3])

    await callback.message.edit_text(
        "🔢 <b>Выберите номер недели</b>\n\n"
        "Отсчет идет с 1 сентября.\n"
        "✅ - текущая неделя",
        reply_markup=get_week_selector_keyboard("teacher", teacher_id),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^teacher_week_(\d+)_(\d+)$"))
async def teacher_week_by_number(callback: types.CallbackQuery):
    """Показать расписание преподавателя по номеру недели"""
    parts = callback.data.split('_')
    week_num = int(parts[2])
    teacher_id = int(parts[3])

    teachers = db.get_all_teachers()
    teacher = next((t for t in teachers if t['id'] == teacher_id), None)
    if not teacher:
        await callback.answer("❌ Преподаватель не найден", show_alert=True)
        return

    today = datetime.now()
    september_1 = datetime(today.year if today.month >= 9 else today.year - 1, 9, 1)
    days_to_monday = (7 - september_1.weekday()) % 7
    first_monday = september_1 + timedelta(days=days_to_monday)
    target_monday = first_monday + timedelta(weeks=week_num - 1)

    week_schedule_text = f"👨‍🏫 <b>Расписание: {teacher['fio']}</b>\n"
    week_schedule_text += f"📆 Неделя {week_num} ({target_monday.strftime('%d.%m.%Y')})\n\n"

    for i in range(6):
        day = target_monday + timedelta(days=i)
        schedule = db.get_teacher_schedule(teacher_id, day.strftime('%Y-%m-%d'))

        day_name = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'][i]
        week_schedule_text += f"<b>{day_name} ({day.strftime('%d.%m')})</b>\n"

        if schedule:
            for lesson in schedule:
                week_schedule_text += (
                    f"  🕐 {lesson['lesson_number']} пара ({lesson['start_time']}-{lesson['end_time']})\n"
                    f"  📚 {lesson['subject_name']}\n"
                    f"  👥 Группа: {lesson['group_number']}\n"
                )
                if lesson.get('room_number'):
                    week_schedule_text += f"  🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
        else:
            week_schedule_text += "  Занятий нет\n"

        week_schedule_text += "\n"

    await callback.message.edit_text(
        week_schedule_text,
        reply_markup=get_week_selector_keyboard("teacher", teacher_id),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^teacher_back_to_days_(\d+)$"))
async def teacher_back_to_days(callback: types.CallbackQuery):
    """Вернуться к выбору дня для преподавателя"""
    teacher_id = int(callback.data.split('_')[4])

    teachers = db.get_all_teachers()
    teacher = next((t for t in teachers if t['id'] == teacher_id), None)
    if not teacher:
        await callback.answer("❌ Преподаватель не найден", show_alert=True)
        return

    today = datetime.now()
    schedule = db.get_teacher_schedule(teacher_id, today.strftime('%Y-%m-%d'))
    text = format_teacher_schedule(teacher, schedule, today)

    await callback.message.edit_text(
        text,
        reply_markup=get_days_keyboard("teacher", teacher_id),
        parse_mode='HTML'
    )
    await callback.answer()


# ============== ПОИСК ПО АУДИТОРИИ ==============

@dp.message(F.text == "🚪 Поиск по аудитории")
@dp.message(Command("room"))
async def search_room(message: types.Message, state: FSMContext):
    """Поиск по аудитории"""
    await message.answer(
        f"🚪 <b>Поиск по аудитории</b>\n\n"
        f"Введите номер аудитории (например: 101, 201А):",
        parse_mode='HTML'
    )
    await state.set_state(SearchStates.waiting_for_room_search)


@dp.message(SearchStates.waiting_for_room_search)
async def process_room_search(message: types.Message, state: FSMContext):
    """Обработка поиска по аудитории"""
    room_number = message.text.strip()

    if room_number.upper() in [
        '📅 МОЕ РАСПИСАНИЕ',
        '🔍 ПОИСК ПО ГРУППЕ',
        '👨‍🏫 ПОИСК ПО ПРЕПОДАВАТЕЛЮ',
        '🚪 ПОИСК ПО АУДИТОРИИ',
        '⚙️ СМЕНИТЬ ГРУППУ',
        '❓ ПОМОЩЬ'
    ]:
        return

    query = "SELECT id, building_id, room_number FROM rooms WHERE room_number ILIKE %s"
    result = db.execute_query(query, (f"%{room_number}%",), fetch=True)
    room = result[0] if result else None

    if not room:
        await message.answer(f"❌ Аудитория '{room_number}' не найдена.")
        return

    await state.clear()

    today = datetime.now()
    schedule = db.get_room_schedule(room["id"], today.strftime('%Y-%m-%d'))
    text = format_room_schedule(room, schedule, today)

    await message.answer(
        text,
        reply_markup=get_days_keyboard("room", room["id"]),
        parse_mode='HTML'
    )


# ============== CALLBACK: АУДИТОРИЯ (дни/недели) ==============

@dp.callback_query(F.data.regexp(r"^room_day_(.+)_(\d+)$"))
async def room_day_selection(callback: types.CallbackQuery):
    """Выбор дня для аудитории"""
    parts = callback.data.split('_')
    day_abbr = parts[2]
    room_id = int(parts[3])

    query = "SELECT id, building_id, room_number FROM rooms WHERE id = %s"
    result = db.execute_query(query, (room_id,), fetch=True)
    room = result[0] if result else None

    if not room:
        await callback.answer("❌ Аудитория не найдена", show_alert=True)
        return

    day_map = {'ПН': 0, 'ВТ': 1, 'СР': 2, 'ЧТ': 3, 'ПТ': 4, 'СБ': 5}
    target_weekday = day_map[day_abbr]

    today = datetime.now()
    days_ahead = target_weekday - today.weekday()
    if days_ahead < 0:
        days_ahead += 7

    target_date = today + timedelta(days=days_ahead)
    schedule = db.get_room_schedule(room_id, target_date.strftime('%Y-%m-%d'))
    text = format_room_schedule(room, schedule, target_date)

    await callback.message.edit_text(
        text,
        reply_markup=get_days_keyboard("room", room_id),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^room_week_current_(\d+)$"))
async def room_week_current(callback: types.CallbackQuery):
    """Показать всю неделю для аудитории"""
    room_id = int(callback.data.split('_')[3])

    query = "SELECT id, building_id, room_number FROM rooms WHERE id = %s"
    result = db.execute_query(query, (room_id,), fetch=True)
    room = result[0] if result else None

    if not room:
        await callback.answer("❌ Аудитория не найдена", show_alert=True)
        return

    today = datetime.now()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)

    week_schedule_text = f"🚪 <b>Аудитория {room['room_number']}</b>\n"
    week_schedule_text += f"📆 Неделя с {monday.strftime('%d.%m.%Y')}\n\n"

    for i in range(6):
        day = monday + timedelta(days=i)
        schedule = db.get_room_schedule(room_id, day.strftime('%Y-%m-%d'))

        day_name = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'][i]
        week_schedule_text += f"<b>{day_name} ({day.strftime('%d.%m')})</b>\n"

        if schedule:
            for lesson in schedule:
                week_schedule_text += (
                    f"  🕐 {lesson['lesson_number']} пара ({lesson['start_time']}-{lesson['end_time']})\n"
                    f"  📚 {lesson['subject_name']}\n"
                    f"  👥 Группа: {lesson['group_number']}\n"
                )
                if lesson.get('teacher_fio'):
                    week_schedule_text += f"  👨‍🏫 {lesson['teacher_fio']}\n"
        else:
            week_schedule_text += "  Свободна\n"

        week_schedule_text += "\n"

    await callback.message.edit_text(
        week_schedule_text,
        reply_markup=get_days_keyboard("room", room_id),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^room_select_week_(\d+)$"))
async def room_select_week(callback: types.CallbackQuery):
    """Показать селектор недель для аудитории"""
    room_id = int(callback.data.split('_')[3])

    await callback.message.edit_text(
        "🔢 <b>Выберите номер недели</b>\n\n"
        "Отсчет идет с 1 сентября.\n"
        "✅ - текущая неделя",
        reply_markup=get_week_selector_keyboard("room", room_id),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^room_week_(\d+)_(\d+)$"))
async def room_week_by_number(callback: types.CallbackQuery):
    """Показать расписание аудитории по номеру недели"""
    parts = callback.data.split('_')
    week_num = int(parts[2])
    room_id = int(parts[3])

    query = "SELECT id, building_id, room_number FROM rooms WHERE id = %s"
    result = db.execute_query(query, (room_id,), fetch=True)
    room = result[0] if result else None

    if not room:
        await callback.answer("❌ Аудитория не найдена", show_alert=True)
        return

    today = datetime.now()
    september_1 = datetime(today.year if today.month >= 9 else today.year - 1, 9, 1)
    days_to_monday = (7 - september_1.weekday()) % 7
    first_monday = september_1 + timedelta(days=days_to_monday)
    target_monday = first_monday + timedelta(weeks=week_num - 1)

    week_schedule_text = f"🚪 <b>Аудитория {room['room_number']}</b>\n"
    week_schedule_text += f"📆 Неделя {week_num} ({target_monday.strftime('%d.%m.%Y')})\n\n"

    for i in range(6):
        day = target_monday + timedelta(days=i)
        schedule = db.get_room_schedule(room_id, day.strftime('%Y-%m-%d'))

        day_name = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'][i]
        week_schedule_text += f"<b>{day_name} ({day.strftime('%d.%m')})</b>\n"

        if schedule:
            for lesson in schedule:
                week_schedule_text += (
                    f"  🕐 {lesson['lesson_number']} пара ({lesson['start_time']}-{lesson['end_time']})\n"
                    f"  📚 {lesson['subject_name']}\n"
                    f"  👥 Группа: {lesson['group_number']}\n"
                )
                if lesson.get('teacher_fio'):
                    week_schedule_text += f"  👨‍🏫 {lesson['teacher_fio']}\n"
        else:
            week_schedule_text += "  Свободна\n"

        week_schedule_text += "\n"

    await callback.message.edit_text(
        week_schedule_text,
        reply_markup=get_week_selector_keyboard("room", room_id),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^room_back_to_days_(\d+)$"))
async def room_back_to_days(callback: types.CallbackQuery):
    """Вернуться к выбору дня для аудитории"""
    room_id = int(callback.data.split('_')[4])

    query = "SELECT id, building_id, room_number FROM rooms WHERE id = %s"
    result = db.execute_query(query, (room_id,), fetch=True)
    room = result[0] if result else None

    if not room:
        await callback.answer("❌ Аудитория не найдена", show_alert=True)
        return

    today = datetime.now()
    schedule = db.get_room_schedule(room_id, today.strftime('%Y-%m-%d'))
    text = format_room_schedule(room, schedule, today)

    await callback.message.edit_text(
        text,
        reply_markup=get_days_keyboard("room", room_id),
        parse_mode='HTML'
    )
    await callback.answer()


# ============== НАСТРОЙКИ /settings ==============

@dp.message(Command("settings"))
async def cmd_settings(message: types.Message):
    """Настройки бота"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала запустите бот командой /start и выберите группу.")
        return

    try:
        settings = db.get_user_settings(user["id"]) or {}
    except Exception as e:
        logger.error(f"Не удалось получить настройки пользователя: {e}")
        settings = {}

    await message.answer(
        "⚙️ <b>Настройки бота</b>\n\n"
        "Выберите пункт меню для изменения:",
        reply_markup=get_settings_keyboard(settings),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "settings_time_format")
async def settings_time_format(callback: types.CallbackQuery):
    user = db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    settings = db.get_user_settings(user["id"]) or {}
    current = settings.get("time_format", "24")
    new_value = "12" if current == "24" else "24"
    db.update_user_settings(user["id"], {"time_format": new_value})
    new_settings = db.get_user_settings(user["id"]) or {}

    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(new_settings)
    )
    await callback.answer("Формат времени изменён.")


@dp.callback_query(F.data == "settings_notifications")
async def settings_notifications(callback: types.CallbackQuery):
    user = db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    settings = db.get_user_settings(user["id"]) or {}
    current = settings.get("notifications", True)
    db.update_user_settings(user["id"], {"notifications": not current})
    new_settings = db.get_user_settings(user["id"]) or {}

    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(new_settings)
    )
    await callback.answer("Настройка уведомлений изменена.")


@dp.callback_query(F.data == "settings_default_view")
async def settings_default_view(callback: types.CallbackQuery):
    user = db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    settings = db.get_user_settings(user["id"]) or {}
    current = settings.get("default_view", "day")
    new_value = "week" if current == "day" else "day"
    db.update_user_settings(user["id"], {"default_view": new_value})
    new_settings = db.get_user_settings(user["id"]) or {}

    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(new_settings)
    )
    await callback.answer("Вид по умолчанию изменён.")


@dp.callback_query(F.data == "settings_change_group")
async def settings_change_group(callback: types.CallbackQuery, state: FSMContext):
    """Запускаем сценарий смены группы через существующую логику"""
    await callback.answer()
    groups = db.get_all_groups()
    groups_text = "\n".join([f"{g['group_number']}" for g in groups])

    await callback.message.answer(
        f"Выберите новую группу из списка:\n\n"
        f"<code>{groups_text}</code>\n\n"
        "Введите номер группы:",
        parse_mode='HTML'
    )
    await state.set_state(UserStates.waiting_for_group)


# ============== ОТЧЕТЫ /logs и РОЛИ /setrole ==============

@dp.message(Command("logs"))
async def cmd_logs(message: types.Message):
    """
    /logs [days]
    Экспорт действий пользователей за N дней в CSV.
    Только для admin/developer.
    """
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not is_admin(user):
        await message.answer("❌ У вас нет прав для просмотра логов.")
        return

    parts = message.text.split(maxsplit=1)
    days = 1
    if len(parts) > 1:
        try:
            days = int(parts[1])
        except ValueError:
            await message.answer("⚠️ Использование: /logs [количество_дней]\nНапример: /logs 7")
            return

    actions = db.get_user_actions(last_days=days)
    if not actions:
        await message.answer("За указанный период действий не найдено.")
        return

    filename = export_user_actions_to_csv(actions)  # создаёт файл в /reports
    doc = FSInputFile(filename)
    await message.answer_document(
        document=doc,
        caption=f"📊 Отчет по действиям пользователей за последние {days} дн."
    )


@dp.message(Command("setrole"))
async def cmd_setrole(message: types.Message):
    """
    /setrole <telegram_id> <user|admin|developer>
    Только для разработчика.
    """
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not is_developer(user):
        await message.answer("❌ Команда доступна только разработчику.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /setrole <telegram_id> <user|admin|developer>")
        return

    try:
        target_tg_id = int(parts[1])
    except ValueError:
        await message.answer("telegram_id должен быть числом.")
        return

    new_role = parts[2]
    if new_role not in ("user", "admin", "developer"):
        await message.answer("Роль должна быть одной из: user, admin, developer")
        return

    target_user = db.get_user_by_telegram_id(target_tg_id)
    if not target_user:
        await message.answer("Пользователь с таким Telegram ID не найден.")
        return

    db.update_user_role(target_user["id"], new_role)
    await message.answer(f"✅ Роль пользователя {target_tg_id} изменена на: {new_role}")


# ============== ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК ==============

@dp.error()
async def error_handler(event, exception):
    """
    Глобальный обработчик ошибок aiogram 3.x
    """
    logger.error(f"Ошибка при обработке события: {exception}", exc_info=True)
    
    # Игнорируем ошибку "message is not modified"
    if "message is not modified" in str(exception):
        return True
    
    return True