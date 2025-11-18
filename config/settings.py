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

# Расписание пар
SCHEDULE_TIMES = {
    1: ('09:00', '10:30'),
    2: ('10:40', '12:10'),
    3: ('12:40', '14:10'),
    4: ('14:20', '15:50'),
    5: ('16:20', '17:50'),
    6: ('18:00', '19:30'),
    7: ('19:40', '21:10')
}

# Настройки логирования
LOG_FILE = 'bot.log'
LOG_REPORTS_DIR = 'reports'

# Каталог для хранения файлов
FILES_DIR = 'files'
SCHEDULES_DIR = os.path.join(FILES_DIR, 'schedules')