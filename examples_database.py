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


def example_get_teacher_schedule():
    """Пример получения расписания преподавателя"""
    db = DatabaseManager()
    
    # Получаем всех преподавателей
    teachers = db.get_all_teachers()
    
    if teachers:
        teacher = teachers[0]  # Берем первого
        today = datetime.now().strftime('%Y-%m-%d')
        
        schedule = db.get_teacher_schedule(teacher['id'], today)
        
        print(f"Расписание преподавателя {teacher['fio']}:")
        for lesson in schedule:
            print(f"{lesson['lesson_number']} пара: {lesson['subject_name']}")
            print(f"Группа: {lesson['group_number']}")
            print(f"Аудитория: {lesson['room_number']}")
            print()


def example_get_room_schedule():
    """Пример получения расписания аудитории"""
    db = DatabaseManager()
    
    # Пример для аудитории с ID=1
    today = datetime.now().strftime('%Y-%m-%d')
    schedule = db.get_room_schedule(room_id=1, date=today)
    
    print("Расписание аудитории:")
    for lesson in schedule:
        print(f"{lesson['lesson_number']} пара: {lesson['subject_name']}")
        print(f"Группа: {lesson['group_number']}")
        print(f"Преподаватель: {lesson['teacher_fio']}")
        print()


def example_get_faculty_schedule():
    """Пример получения расписания факультета"""
    db = DatabaseManager()
    
    # Пример для факультета с ID=1
    today = datetime.now().strftime('%Y-%m-%d')
    schedule = db.get_schedule_by_faculty(faculty_id=1, date=today)
    
    print("Расписание факультета:")
    current_group = None
    for lesson in schedule:
        if current_group != lesson['group_number']:
            current_group = lesson['group_number']
            print(f"\n=== Группа {current_group} ===")
        
        print(f"{lesson['lesson_number']} пара: {lesson['subject_name']}")
        print(f"Преподаватель: {lesson['teacher_fio']}")
        print()


def example_update_settings():
    """Пример обновления настроек пользователя"""
    db = DatabaseManager()
    
    user = db.get_user_by_telegram_id(123456789)
    
    if user:
        # Обновляем настройки
        db.update_user_settings(
            user_id=user['id'],
            notifications_enabled=True,
            notification_time='08:00',
            show_teacher_info=True,
            show_room_info=True
        )
        print("Настройки обновлены")
        
        # Получаем обновленные настройки
        settings = db.get_user_settings(user['id'])
        print(f"Уведомления: {settings['notifications_enabled']}")
        print(f"Время уведомлений: {settings['notification_time']}")


def example_custom_query():
    """Пример выполнения произвольного запроса"""
    db = DatabaseManager()
    
    # Получаем статистику по пользователям
    query = """
        SELECT 
            role,
            COUNT(*) as count
        FROM users
        WHERE is_active = TRUE
        GROUP BY role
        ORDER BY count DESC
    """
    
    result = db.execute_query(query, fetch=True)
    
    print("Статистика пользователей:")
    for row in result:
        print(f"{row['role']}: {row['count']} пользователей")


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
    # example_get_teacher_schedule()
    # example_get_room_schedule()
    # example_get_faculty_schedule()
    # example_update_settings()
    # example_custom_query()
    
    print("\nДля запуска примеров раскомментируйте нужную функцию")
