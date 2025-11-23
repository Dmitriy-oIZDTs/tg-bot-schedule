"""
Основные обработчики команд телеграм-бота
"""

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import calendar
import logging

from config.settings import BOT_TOKEN
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния для FSM
class UserStates(StatesGroup):
    """Состояния пользователя"""
    waiting_for_group = State()
    viewing_schedule = State()


class SearchStates(StatesGroup):
    """Состояния для поиска"""
    waiting_for_group_search = State()
    waiting_for_teacher_search = State()
    waiting_for_room_search = State()


# Инициализация базы данных (ПОСЛЕ определения состояний!)
db = DatabaseManager()

# ============== КЛАВИАТУРЫ ==============

def get_main_keyboard():
    """Главная клавиатура"""
    buttons = [
        [KeyboardButton(text="📅 Мое расписание")],
        [KeyboardButton(text="🔍 Поиск по группе")],
        [KeyboardButton(text="👨‍🏫 Поиск по преподавателю")],
        [KeyboardButton(text="🚪 Поиск по аудитории")],
        [KeyboardButton(text="⚙️ Сменить группу")],
        [KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_days_keyboard():
    """Клавиатура выбора дня недели"""
    days = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ']
    buttons = []
    
    # Первая строка - дни недели
    row = []
    for day in days:
        row.append(InlineKeyboardButton(text=day, callback_data=f"day_{day}"))
    buttons.append(row)
    
    # Вторая строка - вся неделя и выбор недели
    buttons.append([
        InlineKeyboardButton(text="📅 Вся неделя", callback_data="week_current"),
        InlineKeyboardButton(text="🔢 По номеру недели", callback_data="select_week")
    ])
    
    # Третья строка - навигация
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_week_selector_keyboard():
    """Клавиатура выбора номера недели"""
    # Вычисляем текущую неделю от 1 сентября
    today = datetime.now()
    september_1 = datetime(today.year if today.month >= 9 else today.year - 1, 9, 1)
    current_week = ((today - september_1).days // 7) + 1
    
    buttons = []
    
    # Показываем недели по 4 в ряд
    for i in range(0, 20, 4):
        row = []
        for week_num in range(i + 1, min(i + 5, 21)):
            text = f"✅ {week_num}" if week_num == current_week else str(week_num)
            row.append(InlineKeyboardButton(text=text, callback_data=f"week_{week_num}"))
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_days")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============== КОМАНДЫ ==============

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработка команды /start"""
    telegram_id = message.from_user.id
    user = db.get_user_by_telegram_id(telegram_id)
    
    if user and user['group_id']:
        # Пользователь уже выбрал группу
        await message.answer(
            f"С возвращением!\n"
            f"Ваша группа: {user['group_number']}\n\n"
            f"Выберите действие:",
            reply_markup=get_main_keyboard()
        )
    else:
        # Новый пользователь - выбор группы
        groups = db.get_all_groups()
        groups_text = "\n".join([f"• {g['group_number']}" for g in groups])
        
        await message.answer(
            "👋 Добро пожаловать в бот расписания!\n\n"
            f"Выберите вашу группу из списка:\n\n{groups_text}\n\n"
            "Введите номер группы:"
        )
        await state.set_state(UserStates.waiting_for_group)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработка команды /help"""
    help_text = """
📖 <b>Справка по боту</b>

<b>Основные команды:</b>
/start - Начать работу с ботом
/help - Показать эту справку
/group - Посмотреть расписание группы
/teacher - Найти преподавателя
/room - Посмотреть занятость аудитории

<b>Как пользоваться:</b>
1️⃣ При первом запуске выберите свою группу
2️⃣ Нажмите "Мое расписание" для просмотра
3️⃣ Выберите день недели или всю неделю
4️⃣ Можно выбрать неделю по номеру (с 1 сентября)

<b>Поиск:</b>
🔍 Поиск по группе - расписание любой группы
👨‍🏫 Поиск по преподавателю - где и когда пары
🚪 Поиск по аудитории - занятость кабинета

<b>Автор:</b> [Ваше ФИО]
<b>Группа:</b> [Ваша группа]
"""
    await message.answer(help_text, parse_mode='HTML')


@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer(
        "Действие отменено.",
        reply_markup=get_main_keyboard()
    )

# ============== ВЫБОР ГРУППЫ ==============

@dp.message(UserStates.waiting_for_group)
async def process_group_selection(message: types.Message, state: FSMContext):
    """Обработка выбора группы"""
    group_number = message.text.strip().upper()
    
    # Получаем все группы
    groups = db.get_all_groups()
    group = next((g for g in groups if g['group_number'].upper() == group_number), None)
    
    if not group:
        groups_text = "\n".join([f"• {g['group_number']}" for g in groups])
        await message.answer(
            f"❌ Группа '{group_number}' не найдена.\n\n"
            f"Доступные группы:\n{groups_text}\n\n"
            f"Введите точное название группы:"
        )
        return
    
    # Создаем или обновляем пользователя
    telegram_id = message.from_user.id
    username = message.from_user.username
    user = db.get_user_by_telegram_id(telegram_id)
    
    if user:
        # Обновляем группу
        db.update_user_group(user['id'], group['id'])
    else:
        # Создаем пользователя
        user = db.create_user(telegram_id, username, None, role='user', group_id=group['id'])
    
    await state.clear()
    
    await message.answer(
        f"✅ Группа установлена: {group_number}\n"
        f"🏛 Факультет: {group['faculty_name']}\n\n"
        f"Теперь вы можете просматривать расписание!",
        reply_markup=get_main_keyboard()
    )

# ============== МОЕ РАСПИСАНИЕ ==============

@dp.message(F.text == "📅 Мое расписание")
async def show_my_schedule(message: types.Message):
    """Показать расписание пользователя"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user or not user['group_number']:
        await message.answer(
            "❌ Сначала выберите группу.\n"
            "Используйте /start для выбора группы."
        )
        return
    
    # Получаем расписание на сегодня
    today = datetime.now()
    schedule = db.get_schedule_by_group(user['group_number'], today.strftime('%Y-%m-%d'))
    
    if schedule:
        schedule_text = format_schedule_day(schedule, user['group_number'], today)
        await message.answer(
            schedule_text,
            reply_markup=get_days_keyboard(),
            parse_mode='HTML'
        )
    else:
        await message.answer(
            f"📅 Расписание группы {user['group_number']}\n"
            f"📆 {today.strftime('%d.%m.%Y (%A)')}\n\n"
            f"На сегодня занятий нет 🎉",
            reply_markup=get_days_keyboard(),
            parse_mode='HTML'
        )

# ============== ОБРАБОТКА CALLBACK ==============

@dp.callback_query(F.data.startswith("day_"))
async def process_day_selection(callback: types.CallbackQuery):
    """Обработка выбора дня недели"""
    user = db.get_user_by_telegram_id(callback.from_user.id)
    
    if not user or not user['group_number']:
        await callback.answer("❌ Группа не выбрана", show_alert=True)
        return
    
    # Определяем день недели
    day_map = {'ПН': 0, 'ВТ': 1, 'СР': 2, 'ЧТ': 3, 'ПТ': 4, 'СБ': 5}
    day_abbr = callback.data.split('_')[1]
    target_weekday = day_map[day_abbr]
    
    # Находим ближайший такой день
    today = datetime.now()
    days_ahead = target_weekday - today.weekday()
    if days_ahead < 0:
        days_ahead += 7
    
    target_date = today + timedelta(days=days_ahead)
    
    # Получаем расписание
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
        reply_markup=get_days_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data == "week_current")
async def show_week_schedule(callback: types.CallbackQuery):
    """Показать расписание на всю текущую неделю"""
    user = db.get_user_by_telegram_id(callback.from_user.id)
    
    if not user or not user['group_number']:
        await callback.answer("❌ Группа не выбрана", show_alert=True)
        return
    
    # Получаем понедельник текущей недели
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    
    week_schedule_text = f"📅 <b>Расписание группы {user['group_number']}</b>\n"
    week_schedule_text += f"📆 Неделя с {monday.strftime('%d.%m.%Y')}\n\n"
    
    # Получаем расписание на всю неделю
    for i in range(6):  # ПН-СБ
        day = monday + timedelta(days=i)
        schedule = db.get_schedule_by_group(user['group_number'], day.strftime('%Y-%m-%d'))
        
        day_name = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'][i]
        week_schedule_text += f"<b>{day_name} ({day.strftime('%d.%m')})</b>\n"
        
        if schedule:
            for lesson in schedule:
                week_schedule_text += (
                    f"  🕐 {lesson['lesson_number']} пара ({lesson['start_time']}-{lesson['end_time']})\n"
                    f"  📚 {lesson['subject_name']}\n"
                )
                if lesson['teacher_fio']:
                    week_schedule_text += f"  👨‍🏫 {lesson['teacher_fio']}\n"
                if lesson['room_number']:
                    week_schedule_text += f"  🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
        else:
            week_schedule_text += "  Занятий нет\n"
        
        week_schedule_text += "\n"
    
    await callback.message.edit_text(
        week_schedule_text,
        reply_markup=get_days_keyboard(),
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
        reply_markup=get_week_selector_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("week_"))
async def show_week_by_number(callback: types.CallbackQuery):
    """Показать расписание по номеру недели"""
    user = db.get_user_by_telegram_id(callback.from_user.id)
    
    if not user or not user['group_number']:
        await callback.answer("❌ Группа не выбрана", show_alert=True)
        return
    
    week_num = int(callback.data.split('_')[1])
    
    # Вычисляем дату начала недели
    today = datetime.now()
    september_1 = datetime(today.year if today.month >= 9 else today.year - 1, 9, 1)
    # Находим ближайший понедельник от 1 сентября
    days_to_monday = (7 - september_1.weekday()) % 7
    first_monday = september_1 + timedelta(days=days_to_monday)
    target_monday = first_monday + timedelta(weeks=week_num - 1)
    
    week_schedule_text = f"📅 <b>Расписание группы {user['group_number']}</b>\n"
    week_schedule_text += f"📆 Неделя {week_num} ({target_monday.strftime('%d.%m.%Y')})\n\n"
    
    # Получаем расписание на всю неделю
    for i in range(6):  # ПН-СБ
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
                if lesson['teacher_fio']:
                    week_schedule_text += f"  👨‍🏫 {lesson['teacher_fio']}\n"
                if lesson['room_number']:
                    week_schedule_text += f"  🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
        else:
            week_schedule_text += "  Занятий нет\n"
        
        week_schedule_text += "\n"
    
    await callback.message.edit_text(
        week_schedule_text,
        reply_markup=get_week_selector_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_days")
async def back_to_days(callback: types.CallbackQuery):
    """Вернуться к выбору дня"""
    user = db.get_user_by_telegram_id(callback.from_user.id)
    today = datetime.now()
    schedule = db.get_schedule_by_group(user['group_number'], today.strftime('%Y-%m-%d'))
    
    if schedule:
        schedule_text = format_schedule_day(schedule, user['group_number'], today)
    else:
        schedule_text = f"📅 Расписание группы {user['group_number']}\n\nВыберите день:"
    
    await callback.message.edit_text(
        schedule_text,
        reply_markup=get_days_keyboard(),
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



# ============== СМЕНА ГРУППЫ ==============

@dp.message(F.text == "⚙️ Сменить группу")
async def change_group(message: types.Message, state: FSMContext):
    """Смена группы пользователя"""
    groups = db.get_all_groups()
    groups_text = "\n".join([f"• {g['group_number']}" for g in groups])
    
    await message.answer(
        f"Выберите новую группу из списка:\n\n{groups_text}\n\n"
        "Введите номер группы:"
    )
    await state.set_state(UserStates.waiting_for_group)


# ============== ПОИСК ==============

@dp.message(F.text == "🔍 Поиск по группе")
@dp.message(Command("group"))
async def search_group(message: types.Message, state: FSMContext):
    """Поиск расписания по группе"""
    groups = db.get_all_groups()
    groups_text = "\n".join([f"• {g['group_number']}" for g in groups])
    
    await message.answer(
        f"🔍 <b>Поиск расписания по группе</b>\n\n"
        f"Доступные группы:\n{groups_text}\n\n"
        f"Введите номер группы:",
        parse_mode='HTML'
    )
    await state.set_state(SearchStates.waiting_for_group_search)


@dp.message(SearchStates.waiting_for_group_search)
async def process_group_search(message: types.Message, state: FSMContext):
    """Обработка поиска по группе"""
    group_number = message.text.strip().upper()
    groups = db.get_all_groups()
    group = next((g for g in groups if g['group_number'].upper() == group_number), None)
    
    if not group:
        await message.answer(f"❌ Группа '{group_number}' не найдена.")
        return
    
    await state.clear()
    
    # Показываем расписание на сегодня
    today = datetime.now()
    schedule = db.get_schedule_by_group(group_number, today.strftime('%Y-%m-%d'))
    
    if schedule:
        schedule_text = format_schedule_day(schedule, group_number, today)
    else:
        schedule_text = f"📅 Расписание группы {group_number}\n📆 {today.strftime('%d.%m.%Y')}\n\nНа сегодня занятий нет."
    
    await message.answer(schedule_text, parse_mode='HTML')


@dp.message(F.text == "👨‍🏫 Поиск по преподавателю")
@dp.message(Command("teacher"))
async def search_teacher(message: types.Message, state: FSMContext):
    """Поиск расписания преподавателя"""
    teachers = db.get_all_teachers()
    teachers_text = "\n".join([f"• {t['fio']}" for t in teachers[:20]])  # Первые 20
    
    await message.answer(
        f"👨‍🏫 <b>Поиск по преподавателю</b>\n\n"
        f"Преподаватели (первые 20):\n{teachers_text}\n\n"
        f"Введите ФИО преподавателя:",
        parse_mode='HTML'
    )
    await state.set_state(SearchStates.waiting_for_teacher_search)


@dp.message(SearchStates.waiting_for_teacher_search)
async def process_teacher_search(message: types.Message, state: FSMContext):
    """Обработка поиска по преподавателю"""
    teacher_name = message.text.strip()
    teachers = db.get_all_teachers()
    teacher = next((t for t in teachers if teacher_name.lower() in t['fio'].lower()), None)
    
    if not teacher:
        await message.answer(f"❌ Преподаватель '{teacher_name}' не найден.")
        return
    
    await state.clear()
    
    # Показываем расписание на сегодня
    today = datetime.now()
    schedule = db.get_teacher_schedule(teacher['id'], today.strftime('%Y-%m-%d'))
    
    if schedule:
        text = f"👨‍🏫 <b>Расписание: {teacher['fio']}</b>\n"
        text += f"📆 {today.strftime('%d.%m.%Y (%A)')}\n\n"
        
        for lesson in schedule:
            text += f"🕐 <b>{lesson['lesson_number']} пара ({lesson['start_time']} - {lesson['end_time']})</b>\n"
            text += f"📚 {lesson['subject_name']}\n"
            text += f"👥 Группа: {lesson['group_number']}\n"
            if lesson['room_number']:
                text += f"🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
            text += "\n"
        
        await message.answer(text, parse_mode='HTML')
    else:
        await message.answer(
            f"👨‍🏫 {teacher['fio']}\n"
            f"📆 {today.strftime('%d.%m.%Y')}\n\n"
            f"На сегодня пар нет."
        )


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
    
    # Ищем аудиторию
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, building_id, room_number FROM rooms WHERE room_number ILIKE %s", (f"%{room_number}%",))
    room = cursor.fetchone()
    cursor.close()
    db.disconnect()
    
    if not room:
        await message.answer(f"❌ Аудитория '{room_number}' не найдена.")
        return
    
    await state.clear()
    
    # Показываем занятость на сегодня
    today = datetime.now()
    schedule = db.get_room_schedule(room[0], today.strftime('%Y-%m-%d'))
    
    if schedule:
        text = f"🚪 <b>Аудитория {room[2]}</b>\n"
        text += f"📆 {today.strftime('%d.%m.%Y (%A)')}\n\n"
        
        for lesson in schedule:
            text += f"🕐 <b>{lesson['lesson_number']} пара ({lesson['start_time']} - {lesson['end_time']})</b>\n"
            text += f"📚 {lesson['subject_name']}\n"
            text += f"👥 Группа: {lesson['group_number']}\n"
            if lesson['teacher_fio']:
                text += f"👨‍🏫 {lesson['teacher_fio']}\n"
            text += "\n"
        
        await message.answer(text, parse_mode='HTML')
    else:
        await message.answer(
            f"🚪 Аудитория {room[2]}\n"
            f"📆 {today.strftime('%d.%m.%Y')}\n\n"
            f"На сегодня свободна 🎉"
        )


# ============== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==============

def format_schedule_day(schedule, group_number, date):
    """Форматирование расписания на день"""
    if not schedule:
        return f"📅 Расписание группы {group_number}\nНа этот день занятий нет"
    
    text = f"📅 <b>Расписание группы {group_number}</b>\n"
    text += f"📆 <b>{date.strftime('%d.%m.%Y (%A)')}</b>\n\n"
    
    for lesson in schedule:
        text += f"🕐 <b>Пара № {lesson['lesson_number']} ({lesson['start_time']} – {lesson['end_time']})</b>\n"
        text += f"📚 {lesson['subject_name']}"
        
        if lesson['subject_type']:
            text += f" ({lesson['subject_type']})"
        
        text += "\n"
        
        if lesson['teacher_fio']:
            text += f"👨‍🏫 Преподаватель: {lesson['teacher_fio']}\n"
        
        if lesson['building_name'] and lesson['room_number']:
            text += f"🏢 Аудитория: {lesson['room_number']} ({lesson['building_name']})\n"
        
        if lesson['notes']:
            text += f"📝 {lesson['notes']}\n"
        
        text += "\n"
    
    return text


# ============== ОБРАБОТКА ОШИБОК ==============

@dp.errors()
async def error_handler(update: types.Update, exception: Exception):
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка: {exception}", exc_info=True)
    return True