#!/usr/bin/env python3
"""
Главный файл запуска телеграм-бота для расписания студентов.
Инициализация БД + автогенерация всего учебного года.
"""

import asyncio
import logging

from bot.handlers import dp, bot
from database.db_manager import DatabaseManager
from utils.generate_schedule import ensure_schedule_for_academic_year

# ===== ЛОГИРОВАНИЕ =====
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
    """Основная функция запуска бота."""
    logger.info("🚀 Запуск бота...")

    # ===== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ =====
    db = DatabaseManager()
    db.init_database()
    logger.info("📦 База данных инициализирована.")

    # ===== АВТОГЕНЕРАЦИЯ РАСПИСАНИЯ =====
    logger.info("📘 Проверка расписания учебного года...")
    try:
        ensure_schedule_for_academic_year()
        logger.info("📘 Генерация/проверка расписания учебного года завершена.")
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации расписания: {e}", exc_info=True)

    # ===== ЗАПУСК БОТА =====
    try:
        logger.info("🤖 Запуск long-polling...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("🛑 Бот остановлен.")


if __name__ == '__main__':
    asyncio.run(main())
