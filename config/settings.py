import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Настройки базы данных PostgreSQL
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'schedule_bot_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

# Уровни доступа пользователей
USER_ROLES = {
    'developer': 1,
    'admin': 2,
    'user': 3
}

# Тестовые учетные данные (указать во Введении ВКР)
TEST_USERS = {
    'developer': {
        'telegram_id': 123456789,  # ID разработчика
        'fio': 'Иванов Иван Иванович',
        'role': 'developer'
    },
    'admin': {
        'telegram_id': 987654321,  # ID администратора
        'fio': 'Петров Петр Петрович',
        'role': 'admin'
    },
    'user': {
        'telegram_id': 111222333,  # ID обычного пользователя
        'fio': 'Сидоров Сидор Сидорович',
        'role': 'user'
    }
}

