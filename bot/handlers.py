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


# ============== ОБРАБОТКА ОШИБОК ==============

@dp.errors()
async def error_handler(event, exception):
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка: {exception}", exc_info=True)
    return True
