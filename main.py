"""
Главный файл запуска телеграм-бота для расписания студентов
Автор: 
"""

import asyncio
import logging
from bot.handlers import dp, bot
from database.db_manager import DatabaseManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    logger.info("Запуск бота...")
    
    # Инициализация базы данных
    db = DatabaseManager()
    db.init_database()
    logger.info("База данных инициализирована")
    
    try:
        # Запуск бота
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == '__main__':
    asyncio.run(main())
