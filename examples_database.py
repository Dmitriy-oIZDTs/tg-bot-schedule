"""
Примеры использования API базы данных
Этот файл показывает, как работать с DatabaseManager
"""

from database.db_manager import DatabaseManager
from datetime import datetime, timedelta


def example_get_schedule():
    """Пример получения расписания группы"""
    db = DatabaseManager()
    
    # Получить расписание на сегодня
    today = datetime.now().strftime('%Y-%m-%d')
    schedule = db.get_schedule_by_group('ИВТ-21', today)
    
    print("Расписание на сегодня:")
    for lesson in schedule:
        print(f"{lesson['lesson_number']} пара: {lesson['subject_name']}")
        print(f"Преподаватель: {lesson['teacher_fio']}")
        print(f"Аудитория: {lesson['room_number']}")
        print()


def example_get_user():
    """Пример получения пользователя"""
    db = DatabaseManager()
    
    telegram_id = 123456789
    user = db.get_user_by_telegram_id(telegram_id)
    
    if user:
        print(f"Пользователь найден: {user['fio']}")
        print(f"Группа: {user['group_number']}")
        print(f"Роль: {user['role']}")
    else:
        print("Пользователь не найден")


def example_create_user():
    """Пример создания пользователя"""
    db = DatabaseManager()
    
    # Сначала получаем ID группы
    groups = db.get_all_groups()
    group = next((g for g in groups if g['group_number'] == 'ИВТ-21'), None)
    
    if group:
        user = db.create_user(
            telegram_id=123456789,
            username="test_user",
            fio="Тестовый Пользователь Тестович",
            role='user',
            group_id=group['id']
        )
        print(f"Пользователь создан с ID: {user['id']}")


def example_log_action():
    """Пример логирования действия"""
    db = DatabaseManager()
    
    # Получаем пользователя
    user = db.get_user_by_telegram_id(123456789)
    
    if user:
        db.log_user_action(
            user_id=user['id'],
            action_type='view_schedule',
            action_details='Просмотр расписания на сегодня'
        )
        print("Действие залогировано")


if __name__ == '__main__':
    print("=" * 60)
    print("ПРИМЕРЫ РАБОТЫ С БАЗОЙ ДАННЫХ")
    print("=" * 60)
    print()
    
    # Раскомментируйте нужный пример:
    
    # example_get_schedule()
    # example_get_user()
    # example_create_user()
    # example_log_action()
    
    print("\nДля запуска примеров раскомментируйте нужную функцию")
