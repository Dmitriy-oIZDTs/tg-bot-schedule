"""
Основные обработчики команд телеграм-бота
"""

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import logging

from config.settings import BOT_TOKEN
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
db = DatabaseManager()


# Состояния для FSM (Finite State Machine)
class RegistrationStates(StatesGroup):
    """Состояния для регистрации пользователя"""
    waiting_for_fio = State()
    waiting_for_group = State()


class ScheduleStates(StatesGroup):
    """Состояния для работы с расписанием"""
    waiting_for_date = State()
    waiting_for_group_number = State()


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

# ============== РАСПИСАНИЕ ==============

@dp.message(F.text == "📅 Мое расписание")
async def show_my_schedule(message: types.Message):
    """Показать расписание пользователя на сегодня"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
        return
    
    if not user['group_number']:
        await message.answer("❌ У вас не указана группа. Обратитесь к администратору.")
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    schedule = db.get_schedule_by_group(user['group_number'], today)
    
    if not schedule:
        await message.answer(
            f"📅 На сегодня ({datetime.now().strftime('%d.%m.%Y')}) расписания нет.\n\n"
            f"Возможно, сегодня выходной день или расписание еще не добавлено."
        )
    else:
        schedule_text = format_schedule(schedule, user['group_number'])
        await message.answer(schedule_text, parse_mode='HTML')
    
    db.log_user_action(user['id'], 'view_schedule', f'Просмотр расписания на {today}')


@dp.message(F.text == "📋 Расписание на дату")
async def schedule_by_date(message: types.Message):
    """Выбор даты для просмотра расписания"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
        return
    
    await message.answer(
        "📅 Выберите дату для просмотра расписания:",
        reply_markup=get_date_keyboard()
    )


@dp.callback_query(F.data.startswith("date_"))
async def process_date_selection(callback: types.CallbackQuery):
    """Обработка выбора даты"""
    date_str = callback.data.split("_")[1]
    user = db.get_user_by_telegram_id(callback.from_user.id)
    
    if not user or not user['group_number']:
        await callback.answer("❌ Ошибка: группа не указана", show_alert=True)
        return
    
    schedule = db.get_schedule_by_group(user['group_number'], date_str)
    
    if not schedule:
        date_formatted = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
        await callback.message.edit_text(
            f"📅 На {date_formatted} расписания нет.\n\n"
            f"Возможно, это выходной день или расписание еще не добавлено."
        )
    else:
        schedule_text = format_schedule(schedule, user['group_number'])
        await callback.message.edit_text(schedule_text, parse_mode='HTML')
    
    db.log_user_action(user['id'], 'view_schedule_date', f'Просмотр расписания на {date_str}')
    await callback.answer()


# ============== НАСТРОЙКИ ==============

@dp.message(F.text == "⚙️ Настройки")
async def show_settings(message: types.Message):
    """Показать настройки"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start для регистрации.")
        return
    
    await message.answer(
        "⚙️ <b>Настройки бота</b>\n\n"
        "Выберите параметр для изменения:",
        reply_markup=get_settings_keyboard(),
        parse_mode='HTML'
    )


@dp.callback_query(F.data.startswith("settings_"))
async def process_settings(callback: types.CallbackQuery):
    """Обработка настроек"""
    setting = callback.data.split("_")[1]
    user = db.get_user_by_telegram_id(callback.from_user.id)
    
    if setting == "back":
        await callback.message.delete()
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_keyboard(user['role'])
        )
    else:
        await callback.answer("⚙️ Функция в разработке", show_alert=True)
    
    await callback.answer()


# ============== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==============

def format_schedule(schedule, group_number):
    """Форматирование расписания для вывода"""
    if not schedule:
        return "Расписания нет"
    
    date = schedule[0]['lesson_date']
    date_formatted = date.strftime('%d.%m.%Y, %A')
    
    text = f"📅 <b>Расписание группы {group_number}</b>\n"
    text += f"📆 <b>{date_formatted}</b>\n\n"
    
    for lesson in schedule:
        text += f"🕐 <b>{lesson['lesson_number']} пара ({lesson['start_time']} - {lesson['end_time']})</b>\n"
        text += f"📚 {lesson['subject_name']}"
        
        if lesson['subject_type']:
            text += f" ({lesson['subject_type']})"
        
        text += "\n"
        
        if lesson['teacher_fio']:
            text += f"👨‍🏫 {lesson['teacher_fio']}\n"
        
        if lesson['building_name'] and lesson['room_number']:
            text += f"🏢 {lesson['building_name']}, ауд. {lesson['room_number']}\n"
        
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