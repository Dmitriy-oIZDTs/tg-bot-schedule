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

def get_main_keyboard(role='user'):
    """Создание основной клавиатуры в зависимости от роли"""
    buttons = [
        [KeyboardButton(text="📅 Мое расписание")],
        [KeyboardButton(text="📋 Расписание на дату")],
        [KeyboardButton(text="🔍 Поиск по группе")],
        [KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="❓ Помощь")]
    ]
    
    if role in ['admin', 'developer']:
        buttons.append([KeyboardButton(text="👨‍💼 Администрирование")])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_admin_keyboard():
    """Клавиатура для администратора"""
    buttons = [
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="👥 Список пользователей")],
        [KeyboardButton(text="📁 Выгрузить логи")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_date_keyboard():
    """Инлайн-клавиатура для выбора даты"""
    today = datetime.now()
    buttons = []
    
    # Сегодня и завтра
    buttons.append([
        InlineKeyboardButton(text="Сегодня", callback_data=f"date_{today.strftime('%Y-%m-%d')}"),
        InlineKeyboardButton(text="Завтра", callback_data=f"date_{(today + timedelta(days=1)).strftime('%Y-%m-%d')}")
    ])
    
    # Неделя вперед
    for i in range(2, 7):
        date = today + timedelta(days=i)
        buttons.append([
            InlineKeyboardButton(
                text=date.strftime('%d.%m (%A)'),
                callback_data=f"date_{date.strftime('%Y-%m-%d')}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_settings_keyboard():
    """Инлайн-клавиатура для настроек"""
    buttons = [
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings_notifications")],
        [InlineKeyboardButton(text="⏰ Время уведомлений", callback_data="settings_time")],
        [InlineKeyboardButton(text="📱 Формат расписания", callback_data="settings_format")],
        [InlineKeyboardButton(text="👨‍🏫 Показывать преподавателей", callback_data="settings_teachers")],
        [InlineKeyboardButton(text="🏢 Показывать кабинеты", callback_data="settings_rooms")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============== КОМАНДЫ ==============

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработка команды /start"""
    telegram_id = message.from_user.id
    user = db.get_user_by_telegram_id(telegram_id)
    
    if user:
        # Пользователь уже зарегистрирован
        await message.answer(
            f"С возвращением, {user['fio']}!\n"
            f"Ваша группа: {user['group_number'] or 'не указана'}\n\n"
            f"Выберите действие:",
            reply_markup=get_main_keyboard(user['role'])
        )
        db.log_user_action(user['id'], 'start_command', 'Пользователь вернулся в бота')
    else:
        # Новый пользователь - начинаем регистрацию
        await message.answer(
            "👋 Добро пожаловать в бот расписания!\n\n"
            "Для начала работы необходимо зарегистрироваться.\n"
            "Пожалуйста, введите ваше ФИО (полностью):"
        )
        await state.set_state(RegistrationStates.waiting_for_fio)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработка команды /help"""
    help_text = """
📖 <b>Справка по боту</b>

<b>Основные команды:</b>
/start - Начать работу с ботом
/help - Показать эту справку
/schedule - Получить расписание
/settings - Открыть настройки
/cancel - Отменить текущее действие

<b>Возможности бота:</b>
• Просмотр расписания по группе
• Поиск расписания на конкретную дату
• Просмотр расписания преподавателя
• Просмотр занятости кабинетов
• Настройка уведомлений
• Экспорт расписания в файл

<b>Автор:</b> [Ваше ФИО]
<b>Группа:</b> [Ваша группа]

По всем вопросам обращайтесь к администратору.
"""
    await message.answer(help_text, parse_mode='HTML')
    
    user = db.get_user_by_telegram_id(message.from_user.id)
    if user:
        db.log_user_action(user['id'], 'help_command', 'Пользователь запросил справку')


@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("Нечего отменять.")
        return
    
    await state.clear()
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if user:
        await message.answer(
            "Действие отменено.",
            reply_markup=get_main_keyboard(user['role'])
        )
    else:
        await message.answer("Действие отменено.")


# ============== РЕГИСТРАЦИЯ ==============

@dp.message(RegistrationStates.waiting_for_fio)
async def process_fio(message: types.Message, state: FSMContext):
    """Обработка ввода ФИО"""
    fio = message.text.strip()
    
    if len(fio.split()) < 2:
        await message.answer("❌ Пожалуйста, введите ФИО полностью (минимум имя и фамилия):")
        return
    
    await state.update_data(fio=fio)
    
    # Получаем список групп
    groups = db.get_all_groups()
    
    groups_text = "\n".join([f"• {g['group_number']} ({g['faculty_name']})" for g in groups])
    
    await message.answer(
        f"Спасибо, {fio}!\n\n"
        f"Теперь выберите вашу группу из списка:\n\n{groups_text}\n\n"
        f"Введите номер группы:"
    )
    await state.set_state(RegistrationStates.waiting_for_group)


@dp.message(RegistrationStates.waiting_for_group)
async def process_group(message: types.Message, state: FSMContext):
    """Обработка выбора группы"""
    group_number = message.text.strip().upper()
    
    # Проверяем существование группы
    groups = db.get_all_groups()
    group = next((g for g in groups if g['group_number'] == group_number), None)
    
    if not group:
        await message.answer(
            "❌ Группа не найдена. Пожалуйста, выберите группу из списка выше или введите корректный номер:"
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    fio = data['fio']
    
    # Создаем пользователя
    telegram_id = message.from_user.id
    username = message.from_user.username
    
    user = db.create_user(telegram_id, username, fio, role='user', group_id=group['id'])
    
    await state.clear()
    
    await message.answer(
        f"✅ Регистрация завершена!\n\n"
        f"👤 ФИО: {fio}\n"
        f"🎓 Группа: {group_number}\n"
        f"🏛 Факультет: {group['faculty_name']}\n\n"
        f"Теперь вы можете пользоваться всеми функциями бота.",
        reply_markup=get_main_keyboard('user')
    )
    
    db.log_user_action(user['id'], 'registration', f'Пользователь зарегистрирован: {fio}, {group_number}')


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


# ============== ОБРАБОТКА ОШИБОК ==============

@dp.errors()
async def error_handler(event, exception):
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка: {exception}", exc_info=True)
    return True
